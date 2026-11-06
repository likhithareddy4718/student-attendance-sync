
import os
from typing import List, Dict, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# --------------------------------------------------
# CUSTOM SAVE ERROR
# --------------------------------------------------

class MatchSaveError(Exception):
    """Raised when saving matches to the database fails."""
    pass


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():
    """Open a connection to PostgreSQL."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise MatchSaveError(
            "DATABASE_URL is missing in the .env file."
        )

    return psycopg2.connect(database_url)


# --------------------------------------------------
# SAVE CONFIRMED STUDENT-PARENT MATCHES
# --------------------------------------------------

def save_matched_pairs(
    matched_pairs: List[Dict],
    school_id: int
) -> Tuple[bool, str, int]:
    """
    Save administrator-reviewed student-parent matches.

    Each pair should contain:
        student_id
        parent_id

    Student ownership and parent-school association are checked
    before inserting a relationship.

    Returns:
        (success, message, count_saved)
    """

    if not matched_pairs:
        return True, "No matches to save.", 0

    try:
        school_id = int(school_id)

        if school_id <= 0:
            raise ValueError("Invalid school ID")

    except (ValueError, TypeError) as exc:
        raise MatchSaveError("Invalid administrator school ID.") from exc

    conn = None
    cur = None
    count_saved = 0
    errors = []

    try:
        conn = get_db_connection()

        cur = conn.cursor(cursor_factory=RealDictCursor)

        for index, pair in enumerate(matched_pairs):

            student_id = pair.get("student_id")
            parent_id = pair.get("parent_id")

            student_name = pair.get("student_name", "Unknown")
            parent_name = pair.get("parent_name", "Unknown")

            # Do not save rows without a selected parent
            if parent_id is None or parent_id == "":
                errors.append(
                    f"Student '{student_name}' has no parent selected."
                )
                continue

            try:
                student_id = int(student_id)
                parent_id = int(parent_id)

                if student_id <= 0 or parent_id <= 0:
                    raise ValueError()

            except (ValueError, TypeError):
                errors.append(
                    f"Invalid student or parent ID for "
                    f"'{student_name}'."
                )
                continue

            savepoint = f"match_save_{index}"

            cur.execute(f"SAVEPOINT {savepoint}")

            try:
                # 1. Verify student belongs to this school
                cur.execute(
                    """
                    SELECT id, name
                    FROM students
                    WHERE id = %s
                      AND school_id = %s
                    """,
                    (student_id, school_id)
                )

                student = cur.fetchone()

                if not student:
                    errors.append(
                        f"Student '{student_name}' "
                        f"(ID {student_id}) not found in this school."
                    )

                    cur.execute(
                        f"ROLLBACK TO SAVEPOINT {savepoint}"
                    )
                    cur.execute(
                        f"RELEASE SAVEPOINT {savepoint}"
                    )
                    continue

                # 2. Verify parent exists and is associated
                #    with this administrator's school
                cur.execute(
                    """
                    SELECT p.id, p.name
                    FROM parents p
                    WHERE p.id = %s
                      AND EXISTS (
                          SELECT 1
                          FROM student_parents sp
                          JOIN students s
                            ON s.id = sp.student_id
                          WHERE sp.parent_id = p.id
                            AND s.school_id = %s
                      )
                    """,
                    (parent_id, school_id)
                )

                parent = cur.fetchone()

                if not parent:
                    errors.append(
                        f"Parent '{parent_name}' "
                        f"(ID {parent_id}) does not belong to this school."
                    )

                    cur.execute(
                        f"ROLLBACK TO SAVEPOINT {savepoint}"
                    )
                    cur.execute(
                        f"RELEASE SAVEPOINT {savepoint}"
                    )
                    continue

                # 3. Check whether relationship already exists
                cur.execute(
                    """
                    SELECT id
                    FROM student_parents
                    WHERE student_id = %s
                      AND parent_id = %s
                    LIMIT 1
                    """,
                    (student_id, parent_id)
                )

                existing = cur.fetchone()

                if existing:
                    # Avoid duplicate relationship
                    count_saved += 1

                else:
                    # 4. Insert new relationship
                    cur.execute(
                        """
                        INSERT INTO student_parents
                            (student_id, parent_id)
                        VALUES (%s, %s)
                        """,
                        (student_id, parent_id)
                    )

                    count_saved += 1

                cur.execute(
                    f"RELEASE SAVEPOINT {savepoint}"
                )

            except Exception as exc:
                # Roll back only this pair and continue processing
                cur.execute(
                    f"ROLLBACK TO SAVEPOINT {savepoint}"
                )
                cur.execute(
                    f"RELEASE SAVEPOINT {savepoint}"
                )

                errors.append(
                    f"Error saving student ID {student_id}: {str(exc)}"
                )

        # Commit successfully processed pairs
        conn.commit()

        if errors:
            error_summary = " | ".join(errors[:3])

            if len(errors) > 3:
                error_summary += (
                    f" (and {len(errors) - 3} more errors)"
                )

            message = (
                f"Processed {count_saved} matches, "
                f"but {len(errors)} had issues: {error_summary}"
            )

            return False, message, count_saved

        message = (
            f"Successfully saved {count_saved} "
            "student-parent matches."
        )

        return True, message, count_saved

    except psycopg2.Error as exc:

        if conn:
            conn.rollback()

        raise MatchSaveError(
            f"Database error while saving matches: {str(exc)}"
        ) from exc

    except Exception as exc:

        if conn:
            conn.rollback()

        if isinstance(exc, MatchSaveError):
            raise

        raise MatchSaveError(
            f"Unexpected error while saving matches: {str(exc)}"
        ) from exc

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()
