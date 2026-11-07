
import logging
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DeduplicationChecker:
    """
    Checks if a notification has already been sent for an absence.
    Prevents the same parent from getting the same message twice.
    """

    def __init__(self, db_connection):
        """
        Set up the checker with a database connection.
        """
        self.db = db_connection

    def has_notification_been_sent(
        self,
        student_id: int,
        parent_id: int,
        attendance_date: str,
        delivery_method: Optional[str] = None
    ) -> bool:
        """
        Check whether a notification was already sent
        to this parent for this student's absence.

        delivery_method can be email, sms, or None.
        None checks all delivery methods.
        """

        try:
            query = """
                SELECT COUNT(*) AS count
                FROM notifications
                WHERE student_id = %s
                  AND parent_id = %s
                  AND DATE(sent_at) = %s
                  AND status IN ('sent', 'delivered')
                  AND (%s IS NULL OR delivery_method = %s)
            """

            with self.db.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:

                cursor.execute(
                    query,
                    (
                        student_id,
                        parent_id,
                        attendance_date,
                        delivery_method,
                        delivery_method
                    )
                )

                result = cursor.fetchone()

            count = result["count"] if result else 0

            if count > 0:
                logger.info(
                    f"Notification already sent: "
                    f"student_id={student_id}, "
                    f"parent_id={parent_id}, "
                    f"date={attendance_date}, "
                    f"method={delivery_method}"
                )
                return True

            return False

        except psycopg2.Error:
            logger.exception(
                "Database error checking duplicate notification"
            )
            # Do not risk sending a duplicate if the check fails.
            raise

    def mark_notification_sent(
        self,
        parent_id: int,
        student_id: int,
        message: str,
        delivery_method: str
    ) -> bool:
        """
        Record a notification after the provider accepts it.
        """

        query = """
            INSERT INTO notifications
                (
                    parent_id,
                    student_id,
                    message,
                    sent_at,
                    status,
                    delivery_method
                )
            VALUES
                (%s, %s, %s, NOW(), %s, %s)
        """

        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        parent_id,
                        student_id,
                        message,
                        "sent",
                        delivery_method
                    )
                )

            self.db.commit()

            logger.info(
                f"Notification record created: "
                f"parent_id={parent_id}, "
                f"student_id={student_id}, "
                f"delivery_method={delivery_method}"
            )

            return True

        except psycopg2.Error:
            self.db.rollback()
            logger.exception(
                "Database error marking notification as sent"
            )
            return False

    def update_notification_status(
        self,
        parent_id: int,
        student_id: int,
        new_status: str,
        delivery_method: Optional[str] = None
    ) -> bool:
        """
        Update the status of the latest notification.

        Example: sent to delivered.
        Optionally specify email or sms.
        """

        allowed_statuses = {
            "pending",
            "sent",
            "delivered",
            "failed"
        }

        if new_status not in allowed_statuses:
            logger.error(
                f"Unsupported notification status: {new_status}"
            )
            return False

        query = """
            WITH latest_notification AS (
                SELECT ctid
                FROM notifications
                WHERE parent_id = %s
                  AND student_id = %s
                  AND (
                      %s IS NULL
                      OR delivery_method = %s
                  )
                ORDER BY sent_at DESC NULLS LAST
                LIMIT 1
            )
            UPDATE notifications AS n
            SET status = %s
            FROM latest_notification AS latest
            WHERE n.ctid = latest.ctid
        """

        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        parent_id,
                        student_id,
                        delivery_method,
                        delivery_method,
                        new_status
                    )
                )

                updated = cursor.rowcount

            self.db.commit()

            if updated == 0:
                logger.warning(
                    "No notification found to update"
                )
                return False

            logger.info(
                f"Notification status updated: "
                f"parent_id={parent_id}, "
                f"student_id={student_id}, "
                f"new_status={new_status}, "
                f"method={delivery_method}"
            )

            return True

        except psycopg2.Error:
            self.db.rollback()
            logger.exception(
                "Database error updating notification status"
            )
            return False
