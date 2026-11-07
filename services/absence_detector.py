
import logging
from datetime import datetime
from typing import List

import psycopg2
from psycopg2.extras import RealDictCursor


# Configure logger
logger = logging.getLogger(__name__)


# --------------------------------------------------
# ABSENCE DETECTOR
# --------------------------------------------------

class AbsenceDetector:
    """
    Finds new absences in attendance records
    and prepares them for parent notifications.
    """

    def __init__(self, db_connection):
        """
        Initialize detector with PostgreSQL connection.
        """
        self.db = db_connection

    # --------------------------------------------------
    # GET NEW ABSENCES
    # --------------------------------------------------

    def get_new_absences(self, school_id: int) -> List[dict]:
        """
        Find recent absences that do not already have
        a notification record for the same student,
        parent and attendance date.
        """

        cursor = None

        try:
            cursor = self.db.cursor(
                cursor_factory=RealDictCursor
            )

            query = """
                SELECT
                    ar.id AS attendance_id,
                    ar.student_id,
                    ar.school_id,
                    ar.date,
                    ar.status,
                    ar.sync_timestamp,
                    s.name AS student_name,
                    p.id AS parent_id,
                    p.email,
                    p.phone,
                    p.name AS parent_name

                FROM attendance_records ar

                JOIN students s
                    ON ar.student_id = s.id

                JOIN student_parents sp
                    ON s.id = sp.student_id

                JOIN parents p
                    ON sp.parent_id = p.id

                WHERE
                    ar.school_id = %s
                    AND ar.status = 'absent'
                    AND ar.sync_timestamp >
                        NOW() - INTERVAL '10 minutes'

                    AND NOT EXISTS (
                        SELECT 1
                        FROM notifications n
                        WHERE n.student_id = ar.student_id
                          AND n.parent_id = p.id
                          AND DATE(n.sent_at) = ar.date
                    )

                ORDER BY ar.sync_timestamp DESC;
            """

            cursor.execute(query, (school_id,))

            absences = cursor.fetchall()

            logger.info(
                "Found %s new absences for school %s",
                len(absences),
                school_id
            )

            return absences

        except psycopg2.Error:
            logger.exception(
                "Database error while detecting absences"
            )
            raise

        finally:
            if cursor:
                cursor.close()

    # --------------------------------------------------
    # MARK ABSENCE AS NOTIFIED
    # --------------------------------------------------

    def mark_absence_as_notified(
        self,
        attendance_id: int,
        parent_id: int
    ) -> bool:
        """
        Create a pending notification record to prevent
        duplicate notification processing.

        The notification sender should later update this
        record with the actual message and delivery status.
        """

        cursor = None

        try:
            cursor = self.db.cursor()

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

                SELECT
                    %s,
                    ar.student_id,
                    '',
                    NOW(),
                    'pending',
                    'pending'

                FROM attendance_records ar

                JOIN student_parents sp
                    ON sp.student_id = ar.student_id
                   AND sp.parent_id = %s

                WHERE ar.id = %s

                AND NOT EXISTS (
                    SELECT 1
                    FROM notifications n
                    WHERE n.student_id = ar.student_id
                      AND n.parent_id = %s
                      AND DATE(n.sent_at) = ar.date
                )

                RETURNING id;
            """

            cursor.execute(
                query,
                (
                    parent_id,
                    parent_id,
                    attendance_id,
                    parent_id
                )
            )

            result = cursor.fetchone()

            if not result:
                self.db.rollback()

                logger.info(
                    "Notification record already exists or "
                    "student-parent relationship is invalid."
                )

                return False

            notification_id = result[0]

            self.db.commit()

            logger.info(
                "Created pending notification record %s "
                "for attendance %s",
                notification_id,
                attendance_id
            )

            return True

        except psycopg2.Error:

            self.db.rollback()

            logger.exception(
                "Database error while marking absence as notified"
            )

            return False

        finally:
            if cursor:
                cursor.close()

    # --------------------------------------------------
    # DETECT AND PREPARE NOTIFICATIONS
    # --------------------------------------------------

    def detect_and_prepare(self, school_id: int) -> List[dict]:
        """
        Find new absences and prepare notification data.

        Returns a list of records containing student,
        parent contact and attendance details.
        """

        absences = self.get_new_absences(school_id)

        if not absences:

            logger.info(
                "No new absences to notify for school %s",
                school_id
            )

            return []

        prepared = []

        for absence in absences:

            notification_data = {

                "attendance_id": absence["attendance_id"],

                "student_id": absence["student_id"],

                "student_name": absence["student_name"],

                "parent_id": absence["parent_id"],

                "parent_name": absence["parent_name"],

                "parent_email": absence["email"],

                "parent_phone": absence["phone"],

                "absence_date": absence["date"],

                "absence_status": absence["status"],

                "sync_timestamp": absence["sync_timestamp"]

            }

            prepared.append(notification_data)

        logger.info(
            "Prepared %s absences for notification",
            len(prepared)
        )

        return prepared
