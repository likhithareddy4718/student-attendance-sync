
import os
import csv
import io
import re

import psycopg2
from psycopg2.extras import RealDictCursor

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


# Load environment variables
load_dotenv()


# Create Flask Blueprint
student_parent_bp = Blueprint(
    "student_parent",
    __name__,
    url_prefix="/student-parent"
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing in the .env file"
        )

    return psycopg2.connect(database_url)


# --------------------------------------------------
# STUDENT-PARENT MATCHING PAGE
# --------------------------------------------------

@student_parent_bp.route("/matching", methods=["GET"])
def matching_page():

    # Check administrator login
    if "admin_id" not in session:
        return redirect("/login")

    admin_school_id = session.get("school_id")

    if not admin_school_id:
        return "Administrator school ID is missing", 400

    conn = None

    try:

        conn = get_db_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                """
                SELECT
                    s.id,
                    s.name AS student_name,
                    p.id AS parent_id,
                    p.name AS parent_name,
                    p.email,
                    p.phone

                FROM students s

                LEFT JOIN student_parents sp
                    ON s.id = sp.student_id

                LEFT JOIN parents p
                    ON sp.parent_id = p.id

                WHERE s.school_id = %s

                ORDER BY s.name
                """,
                (admin_school_id,)
            )

            student_parent_data = cur.fetchall()

        return render_template(
            "student_parent_matching.html",
            student_parent_data=student_parent_data,
            school_id=admin_school_id
        )

    except Exception:

        current_app.logger.exception(
            "Error loading student-parent matching page"
        )

        return "Unable to load student-parent records", 500

    finally:

        if conn:
            conn.close()


# --------------------------------------------------
# CSV UPLOAD AND AUTOMATIC STUDENT MATCHING
# --------------------------------------------------

@student_parent_bp.route("/upload-csv", methods=["POST"])
def upload_csv():

    # 1. Check administrator authentication

    if "admin_id" not in session or not session.get("school_id"):

        return jsonify({
            "error": "Not authorized. Please log in again."
        }), 401

    # 2. Check uploaded file

    if "file" not in request.files:

        return jsonify({
            "error": "No file provided"
        }), 400

    file = request.files["file"]

    if not file.filename:

        return jsonify({
            "error": "Please select a CSV file"
        }), 400

    if not file.filename.lower().endswith(".csv"):

        return jsonify({
            "error": "Only CSV files are allowed"
        }), 400

    try:

        # 3. Read CSV file

        content = file.stream.read(1024 * 1024 + 1)

        if len(content) > 1024 * 1024:

            return jsonify({
                "error": "CSV file must be smaller than 1 MB"
            }), 400

        if not content:

            return jsonify({
                "error": "CSV file is empty"
            }), 400

        text_content = content.decode("utf-8-sig")

        reader = csv.DictReader(
            io.StringIO(text_content)
        )

        # 4. Validate CSV headers

        if not reader.fieldnames:

            return jsonify({
                "error": "CSV headers are missing"
            }), 400

        reader.fieldnames = [
            (column or "").strip().lower()
            for column in reader.fieldnames
        ]

        required_columns = {
            "student_id",
            "student_name",
            "parent_name",
            "parent_phone",
            "parent_email"
        }

        if not required_columns.issubset(set(reader.fieldnames)):

            return jsonify({
                "error": (
                    "CSV must contain these columns: "
                    "student_id, student_name, parent_name, "
                    "parent_phone, parent_email"
                )
            }), 400

        # 5. Fetch students belonging to logged-in school

        conn = get_db_connection()

        try:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    """
                    SELECT id, name
                    FROM students
                    WHERE school_id = %s
                    ORDER BY id
                    """,
                    (session["school_id"],)
                )

                student_records = cur.fetchall()

                students = {
                    str(student["id"]): student["name"]
                    for student in student_records
                }

        finally:

            conn.close()

        # 6. Process CSV records

        preview = []
        errors = []
        seen_ids = set()

        for line_number, row in enumerate(reader, start=2):

            student_id = (
                row.get("student_id") or ""
            ).strip()

            student_name = (
                row.get("student_name") or ""
            ).strip()

            parent_name = (
                row.get("parent_name") or ""
            ).strip()

            parent_phone = (
                row.get("parent_phone") or ""
            ).strip()

            parent_email = (
                row.get("parent_email") or ""
            ).strip()

            # Check student ID

            if not student_id:

                errors.append(
                    f"Row {line_number}: Student ID is missing"
                )

                continue

            if not student_id.isdigit():

                errors.append(
                    f"Row {line_number}: Student ID must be numeric"
                )

                continue

            if student_id in seen_ids:

                errors.append(
                    f"Row {line_number}: Duplicate student ID {student_id}"
                )

                continue

            seen_ids.add(student_id)

            # Check student belongs to this school

            if student_id not in students:

                errors.append(
                    f"Row {line_number}: Student ID {student_id} "
                    "does not belong to your school"
                )

                continue

            # Check parent name

            if not parent_name:

                errors.append(
                    f"Row {line_number}: Parent name is missing"
                )

                continue

            # Check parent email

            if parent_email and not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                parent_email
            ):

                errors.append(
                    f"Row {line_number}: Invalid parent email"
                )

                continue

            # Get actual student name from database

            actual_student_name = students[student_id]

            # Compare CSV name with database name

            name_matches = (
                student_name.casefold()
                == actual_student_name.casefold()
            )

            # Add record to preview

            preview.append({

                "student_id": int(student_id),

                "student_name": actual_student_name,

                "uploaded_student_name": student_name,

                "parent_name": parent_name,

                "parent_phone": parent_phone,

                "parent_email": parent_email,

                "name_matches": name_matches,

                "review_status": (
                    "Ready for review"
                    if name_matches
                    else "Student name mismatch - review required"
                )

            })

        # 7. Check valid records

        if not preview and errors:

            return jsonify({

                "error": "No valid records found in CSV",

                "preview": [],

                "errors": errors,

                "total_valid": 0

            }), 400

        # 8. Send preview data to HTML

        return jsonify({

            "message": (
                "CSV processed successfully. "
                "Please review the student-parent matches."
            ),

            "preview": preview,

            "errors": errors,

            "total_valid": len(preview)

        }), 200

    except UnicodeDecodeError:

        return jsonify({

            "error": "CSV must use UTF-8 encoding",

            "preview": [],

            "errors": [],

            "total_valid": 0

        }), 400

    except Exception:

        current_app.logger.exception(
            "CSV upload processing failed"
        )

        return jsonify({

            "error": (
                "Server error while processing CSV. "
                "Check the Flask terminal."
            ),

            "preview": [],

            "errors": [],

            "total_valid": 0

        }), 500


# --------------------------------------------------
# SAVE MATCHES - NEXT IMPLEMENTATION STEP
# --------------------------------------------------

@student_parent_bp.route("/save-matches", methods=["POST"])
def save_matches():

    if "admin_id" not in session:

        return jsonify({
            "error": "Not authorized"
        }), 401

    return jsonify({

        "error": (
            "Save functionality is not implemented yet. "
            "Complete the review and approval feature next."
        )

    }), 501
