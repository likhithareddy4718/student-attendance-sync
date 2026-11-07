
import logging
from typing import Any, Dict, List

from services.absence_detector import AbsenceDetector
from services.notification_sender import NotificationSender
from services.message_formatter import MessageFormatter
from config.notifications import NotificationConfig

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """
    Coordinates attendance synchronization and parent notifications.

    Workflow:
    1. Store attendance records.
    2. Detect recent absences.
    3. Format notification messages.
    4. Validate contacts and send email/SMS.
    5. Prevent duplicate notifications.
    6. Log the synchronization result.
    """

    def __init__(
        self,
        db_connection,
        notification_config: NotificationConfig
    ):
        self.db = db_connection
        self.config = notification_config

        self.absence_detector = AbsenceDetector(db_connection)

        self.notification_sender = NotificationSender(
            notification_config,
            db_connection=db_connection
        )

        self.message_formatter = MessageFormatter()

    # --------------------------------------------------
    # MAIN SYNC METHOD
    # --------------------------------------------------

    def run_sync(
        self,
        school_id: int,
        attendance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run the complete attendance sync for one school.
        """

        result = {
            "success": False,
            "records_synced": 0,
            "notifications_sent": 0,
            "errors": []
        }

        try:
            logger.info(
                "Starting sync for school_id=%s with %s records",
                school_id,
                len(attendance_data)
            )

            # Step 1: Store attendance records.
            records_stored = self._store_attendance_records(
                school_id,
                attendance_data
            )

            result["records_synced"] = records_stored

            logger.info(
                "Stored %s attendance records",
                records_stored
            )

            # Step 2: Detect recent absences.
            absences = self.absence_detector.detect_and_prepare(
                school_id
            )

            logger.info(
                "Found %s recent absences for school_id=%s",
                len(absences),
                school_id
            )

            # Step 3: Process each absence.
            for absence in absences:

                # Clear errors from the previous absence.
                self.notification_sender.delivery_errors = []

                try:
                    count = self._process_absence(absence)

                    result["notifications_sent"] += count

                    # Collect email/SMS delivery errors.
                    result["errors"].extend(
                        self.notification_sender.delivery_errors
                    )

                except Exception as error:
                    error_message = (
                        "Error processing absence for "
                        f"student_id={absence.get('student_id')}: "
                        f"{error}"
                    )

                    logger.exception(error_message)
                    result["errors"].append(error_message)

            # Sync is fully successful only when there are no errors.
            result["success"] = len(result["errors"]) == 0

        except Exception as error:
            error_message = (
                f"Sync failed for school_id={school_id}: {error}"
            )

            logger.exception(error_message)
            result["errors"].append(error_message)
            result["success"] = False

        finally:
            # Step 4: Save the final sync result.
            self._log_sync_result(school_id, result)

        logger.info(
            "Sync completed for school_id=%s: %s",
            school_id,
            result
        )

        return result

    # --------------------------------------------------
    # STORE ATTENDANCE RECORDS
    # --------------------------------------------------

    def _store_attendance_records(
        self,
        school_id: int,
        attendance_data: List[Dict[str, Any]]
    ) -> int:
        """
        Insert attendance records into the database.
        Returns the number of newly inserted records.
        """

        if not attendance_data:
            return 0

        records_stored = 0

        query = """
            INSERT INTO attendance_records
                (
                    student_id,
                    school_id,
                    date,
                    status,
                    sync_timestamp
                )
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """

        try:
            with self.db.cursor() as cursor:

                for record in attendance_data:

                    student_id = record.get("student_id")

                    attendance_date = (
                        record.get("date")
                        or record.get("attendance_date")
                    )

                    status = str(
                        record.get("status", "unknown")
                    ).strip().lower()

                    if not student_id or not attendance_date:
                        logger.warning(
                            "Skipping record with missing "
                            "student_id or date: %s",
                            record
                        )
                        continue

                    cursor.execute(
                        query,
                        (
                            student_id,
                            school_id,
                            attendance_date,
                            status
                        )
                    )

                    records_stored += cursor.rowcount

            self.db.commit()

            return records_stored

        except Exception:
            self.db.rollback()

            logger.exception(
                "Error storing attendance records"
            )

            raise

    # --------------------------------------------------
    # PROCESS ONE ABSENCE
    # --------------------------------------------------

    def _process_absence(
        self,
        absence: Dict[str, Any]
    ) -> int:
        """
        Format and send notifications for one absence.

        NotificationSender handles validation,
        duplicate checks and notification database records.
        """

        student_id = absence.get("student_id")
        parent_id = absence.get("parent_id")

        attendance_date = (
            absence.get("absence_date")
            or absence.get("date")
        )

        parent_email = absence.get("parent_email")
        parent_phone = absence.get("parent_phone")

        if not student_id or not parent_id or not attendance_date:
            logger.warning(
                "Skipping absence with missing student, parent "
                "or attendance date: %s",
                absence
            )
            return 0

        if not self.config.enabled:
            logger.info(
                "Notifications are disabled. "
                "Skipping student_id=%s",
                student_id
            )
            return 0

        # Determine enabled delivery methods.
        email_enabled = (
            self.config.send_email and bool(parent_email)
        )

        sms_enabled = (
            self.config.send_sms and bool(parent_phone)
        )

        if email_enabled and sms_enabled:
            delivery_method = "both"

        elif email_enabled:
            delivery_method = "email"

        elif sms_enabled:
            delivery_method = "sms"

        else:
            logger.info(
                "No enabled contact method for parent_id=%s",
                parent_id
            )
            return 0

        # Format messages.
        email_message = self.message_formatter.format_email(
            absence
        )

        sms_message = self.message_formatter.format_sms(
            absence
        )

        # Send through NotificationSender.
        # It also handles deduplication and saves successful sends.
        results = self.notification_sender.send_notification(
            parent_id=parent_id,
            student_id=student_id,
            recipient_email=parent_email,
            recipient_phone=parent_phone,
            email_subject=email_message["subject"],
            email_body=email_message["body"],
            sms_body=sms_message,
            delivery_method=delivery_method,
            attendance_date=attendance_date
        )

        notifications_sent = sum(
            1 for sent in results.values() if sent
        )

        logger.info(
            "Notification processing completed for "
            "student_id=%s, parent_id=%s: %s",
            student_id,
            parent_id,
            results
        )

        if self.notification_sender.delivery_errors:
            logger.error(
                "Notification delivery errors: %s",
                self.notification_sender.delivery_errors
            )

        return notifications_sent

    # --------------------------------------------------
    # LOG SYNC RESULT
    # --------------------------------------------------

    def _log_sync_result(
        self,
        school_id: int,
        result: Dict[str, Any]
    ) -> None:
        """
        Save the final sync result in sync_logs.
        """

        status = (
            "success" if result["success"] else "failed"
        )

        error_message = (
            " | ".join(result["errors"])
            if result["errors"]
            else None
        )

        query = """
            INSERT INTO sync_logs
                (school_id, timestamp, status, error_message)
            VALUES (%s, NOW(), %s, %s)
        """

        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        school_id,
                        status,
                        error_message
                    )
                )

            self.db.commit()

            logger.info(
                "Sync result saved for school_id=%s",
                school_id
            )

        except Exception:
            self.db.rollback()

            logger.exception(
                "Could not save sync result for school_id=%s",
                school_id
            )
