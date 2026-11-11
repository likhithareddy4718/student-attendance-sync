
import os
from typing import Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# --------------------------------------------------
# CUSTOM VALIDATION ERROR
# --------------------------------------------------

class NotificationValidationError(Exception):
    """Raised when a notification cannot be safely sent."""
    pass


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():
    """Open a connection to the PostgreSQL database."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise NotificationValidationError(
            "DATABASE_URL is missing in the .env file."
        )

    return psycopg2.connect(database_url)


# --------------------------------------------------
# CHECK STUDENT-PARENT RELATIONSHIP
# --------------------------------------------------

def validate_student_parent_pair(
    student_id: int,
    parent_id: int
) -> Tuple[bool, str]:
    """
    Check whether the student-parent pair exists
    in the student_parents table.

    Returns:
        Tuple of (is_valid, reason)
    """

    conn = None

    try:

        conn = get_db_connection()

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

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

            result = cur.fetchone()

        if result:

            return (
                True,
                f"Student {student_id} is linked to parent "
                f"{parent_id}. Safe to notify."
            )

        return (
            False,
            f"No confirmed link between student {student_id} "
            f"and parent {parent_id}. Notification blocked."
        )

    except psycopg2.Error as e:

        raise NotificationValidationError(
            f"Database error during validation: {str(e)}"
        ) from e

    finally:

        if conn:
            conn.close()


# --------------------------------------------------
# CHECK PARENT CONTACT DETAILS
# --------------------------------------------------

def validate_parent_contact_exists(
    parent_id: int,
    delivery_method: str
) -> Tuple[bool, str]:
    """
    Check whether the parent has the requested
    email or phone contact information.

    delivery_method must be 'email' or 'phone'.
    """

    delivery_method = (
        delivery_method or ""
    ).strip().lower()

    # Validate delivery method
    if delivery_method not in ["email", "phone"]:

        raise NotificationValidationError(
            f"Invalid delivery method: {delivery_method}. "
            "Must be 'email' or 'phone'."
        )

    conn = None

    try:

        conn = get_db_connection()

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            # Fetch parent contact information
            cur.execute(
                """
                SELECT email, phone
                FROM parents
                WHERE id = %s
                """,
                (parent_id,)
            )

            parent = cur.fetchone()

        # Check parent existence
        if not parent:

            return (
                False,
                f"Parent {parent_id} does not exist in database."
            )

        # Get requested contact information
        contact_value = parent.get(delivery_method)

        # Check contact availability
        if contact_value and str(contact_value).strip():

            return (
                True,
                f"Parent {parent_id} has a valid "
                f"{delivery_method} contact on file."
            )

        return (
            False,
            f"Parent {parent_id} has no {delivery_method} "
            "on file. Cannot send notification."
        )

    except psycopg2.Error as e:

        raise NotificationValidationError(
            f"Database error during contact validation: {str(e)}"
        ) from e

    finally:

        if conn:
            conn.close()


# --------------------------------------------------
# MAIN NOTIFICATION VALIDATION FUNCTION
# --------------------------------------------------

def validate_notification_safe_to_send(
    student_id: int,
    parent_id: int,
    delivery_method: str
) -> Tuple[bool, str]:
    """
    Run all safety checks before sending a notification.

    Checks:
        1. Student-parent relationship exists.
        2. Parent has the requested contact method.

    Returns:
        Tuple of (is_safe, reason)
    """

    # Check 1: Validate student-parent relationship

    pair_valid, pair_reason = validate_student_parent_pair(
        student_id,
        parent_id
    )

    if not pair_valid:

        return False, pair_reason

    # Check 2: Validate parent contact information

    contact_valid, contact_reason = validate_parent_contact_exists(
        parent_id,
        delivery_method
    )

    if not contact_valid:

        return False, contact_reason

    # Both checks passed

    return (
        True,
        f"Notification to parent {parent_id} about "
        f"student {student_id} is safe to send "
        f"via {delivery_method}."
    )
