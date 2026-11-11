
import os

import psycopg2
from psycopg2.extras import RealDictCursor
from services.match_saver import (
    save_matched_pairs,
    MatchSaveError
)
from dotenv import load_dotenv

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    current_app
)

from services.student_parent_matcher import (
    find_best_parent_match,
    calculate_name_similarity
)

load_dotenv()

review_matches_bp = Blueprint(
    "review_matches",
    __name__,
    url_prefix="/review-matches"
)


# -----------------------------------------
# DATABASE CONNECTION
# -----------------------------------------

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing in .env")

    return psycopg2.connect(database_url)


# -----------------------------------------
# VIEW MATCHES
# -----------------------------------------

@review_matches_bp.route("/view", methods=["POST"])
def view_matches():

    if "admin_id" not in session:
        return redirect("/login")

    school_id = session.get("school_id")

    if not school_id:
        return jsonify({
            "error": "Administrator school ID is missing"
        }), 400

    data = request.get_json(silent=True) or {}
    csv_rows = data.get("csv_rows", [])

    if not isinstance(csv_rows, list) or not csv_rows:
        return jsonify({
            "error": "No CSV records provided"
        }), 400

    if len(csv_rows) > 1000:
        return jsonify({
            "error": "Maximum 1000 records are allowed"
        }), 400

    conn = None

    try:
        conn = get_db_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            # Fetch students belonging to this school
            cur.execute(
                """
                SELECT id, name
                FROM students
                WHERE school_id = %s
                ORDER BY name
                """,
                (school_id,)
            )

            existing_students = cur.fetchall()

            # Fetch parents already linked to this school
            cur.execute(
                """
                SELECT DISTINCT
                    p.id,
                    p.name,
                    p.email,
                    p.phone
                FROM parents p
                INNER JOIN student_parents sp
                    ON p.id = sp.parent_id
                INNER JOIN students s
                    ON sp.student_id = s.id
                WHERE s.school_id = %s
                ORDER BY p.name
                """,
                (school_id,)
            )

            existing_parents = cur.fetchall()

        # Build lookup for school students
        students_by_id = {
            int(student["id"]): student
            for student in existing_students
        }

        matches = []

        for row in csv_rows:

            if not isinstance(row, dict):
                continue

            student_name = (
                row.get("student_name")
                or row.get("uploaded_student_name")
                or ""
            ).strip()

            parent_name = (
                row.get("parent_name") or ""
            ).strip()

            parent_email = (
                row.get("parent_email") or ""
            ).strip()

            parent_phone = (
                row.get("parent_phone") or ""
            ).strip()

            # Identify the database student
            student_match = None
            csv_student_id = row.get("student_id")

            if csv_student_id is not None:
                try:
                    student_match = students_by_id.get(
                        int(csv_student_id)
                    )
                except (ValueError, TypeError):
                    student_match = None

            else:
                # If no ID is supplied, use a unique name match
                possible_students = [
                    student for student in existing_students
                    if calculate_name_similarity(
                        student_name,
                        student["name"]
                    ) > 0.8
                ]

                if len(possible_students) == 1:
                    student_match = possible_students[0]

            if not student_match:
                matches.append({
                    "student_id": None,
                    "student_name": student_name,
                    "parent_name_from_csv": parent_name,
                    "parent_email_from_csv": parent_email,
                    "parent_phone_from_csv": parent_phone,
                    "matched_parent_id": None,
                    "matched_parent_name": "Student not found",
                    "matched_parent_email": "",
                    "matched_parent_phone": "",
                    "confidence_score": 0,
                    "status": "no_student_found"
                })
                continue

            # Find best parent match
            best_match, score = find_best_parent_match(
                student_name,
                parent_name,
                parent_email,
                parent_phone,
                existing_parents
            )

            matches.append({
                "student_id": student_match["id"],
                "student_name": student_match["name"],
                "parent_name_from_csv": parent_name,
                "parent_email_from_csv": parent_email,
                "parent_phone_from_csv": parent_phone,
                "matched_parent_id": (
                    best_match["id"] if best_match else None
                ),
                "matched_parent_name": (
                    best_match["name"]
                    if best_match else "No match found"
                ),
                "matched_parent_email": (
                    (best_match["email"] or "")
                    if best_match else ""
                ),
                "matched_parent_phone": (
                    (best_match["phone"] or "")
                    if best_match else ""
                ),
                "confidence_score": round(score * 100, 1),
                "status": (
                    "matched" if best_match
                    else "no_parent_found"
                )
            })

        return render_template(
            "review_matches.html",
            matches=matches,
            all_parents=existing_parents,
            school_id=school_id
        )

    except Exception:
        current_app.logger.exception(
            "Review matches page failed"
        )

        return jsonify({
            "error": "Unable to generate review matches"
        }), 500

    finally:
        if conn:
            conn.close()


# -----------------------------------------
# CORRECT AND VALIDATE MATCHES
# -----------------------------------------


@review_matches_bp.route("/correct", methods=["POST"])
def correct_matches():
    """
    Validate and save administrator-confirmed matches.
    """

    if "admin_id" not in session:
        return jsonify({
            "error": "Not logged in"
        }), 401

    school_id = session.get("school_id")

    if not school_id:
        return jsonify({
            "error": "Administrator school ID is missing"
        }), 400

    data = request.get_json(silent=True) or {}

    corrected_matches = data.get("corrected_matches", [])

    if not isinstance(corrected_matches, list) or not corrected_matches:
        return jsonify({
            "error": "No matches provided"
        }), 400

    if len(corrected_matches) > 1000:
        return jsonify({
            "error": "Maximum 1000 matches are allowed"
        }), 400

    try:
        # Prepare confirmed pairs for database saving
        confirmed_pairs = []

        for match in corrected_matches:

            if not isinstance(match, dict):
                return jsonify({
                    "error": "Invalid match format"
                }), 400

            confirmed_pairs.append({
                "student_id": match.get("student_id"),
                "parent_id": match.get("parent_id"),
                "student_name": match.get("student_name", "Unknown"),
                "parent_name": match.get("parent_name", "Unknown")
            })

        # Save the confirmed pairs
        success, message, count = save_matched_pairs(
            confirmed_pairs,
            school_id
        )

        if not success:
            return jsonify({
                "success": False,
                "message": message,
                "count_saved": count
            }), 400

        return jsonify({
            "success": True,
            "message": message,
            "count_saved": count
        }), 200

    except MatchSaveError as exc:

        current_app.logger.exception(
            "Unable to save student-parent matches"
        )

        return jsonify({
            "error": str(exc)
        }), 500

    except Exception:

        current_app.logger.exception(
            "Unexpected error while saving matches"
        )

        return jsonify({
            "error": "Unexpected error while saving matches"
        }), 500
