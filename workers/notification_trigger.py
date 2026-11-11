
import logging

from sync.attendance_storage import get_db_connection
from services.absence_detector import AbsenceDetector
from services.notification_sender import NotificationSender
from services.message_formatter import MessageFormatter
from config.notifications import NotificationConfig


logger = logging.getLogger(__name__)


# --------------------------------------------------
# TRIGGER NOTIFICATIONS AFTER ATTENDANCE SYNC
# --------------------------------------------------

def trigger_notifications_for_sync(school_id):
    """
    Find recent absences for a school and notify parents.

    Uses the existing:
    - AbsenceDetector
    - NotificationSender
    - MessageFormatter
    - DeduplicationChecker
    """

    db = None
    result = {
        "success": False,
        "absences_found": 0,
        "notifications_sent": 0,
        "errors": []
    }

    try:
        # Connect to the existing PostgreSQL database.
        db = get_db_connection()

        # Load notification configuration.
        config = NotificationConfig()

        # Create existing service objects.
        detector = AbsenceDetector(db)

        sender = NotificationSender(
            config,
            db_connection=db
        )

        formatter = MessageFormatter()

        # Detect recently recorded absences.
        absences = detector.detect_and_prepare(school_id)

        result["absences_found"] = len(absences)

        logger.info(
            "Found %s absences for school %s",
            len(absences),
            school_id
        )

        # Do not attempt delivery while notifications are disabled.
        if not config.enabled:
            logger.info(
                "Notifications disabled. No messages will be sent."
            )
            result["success"] = True
            return result

        # Process each absence.
        for absence in absences:

            try:
                count = send_notification_for_absence(
                    absence,
                    sender,
                    formatter,
                    config
                )

                result["notifications_sent"] += count

                # Collect delivery errors.
                result["errors"].extend(
                    sender.delivery_errors
                )

                # Reset errors before processing the next absence.
                sender.delivery_errors = []

            except Exception as error:
                error_message = (
                    f"Error processing student "
                    f"{absence.get('student_id')}: {error}"
                )

                logger.exception(error_message)
                result["errors"].append(error_message)

        result["success"] = len(result["errors"]) == 0

        logger.info(
            "Notification trigger completed: %s",
            result
        )

    except Exception as error:

        result["errors"].append(str(error))

        logger.exception(
            "Error triggering notifications for school %s",
            school_id
        )

    finally:
        if db is not None:
            db.close()
            logger.info("Notification trigger database connection closed")

    return result


# --------------------------------------------------
# SEND NOTIFICATION FOR ONE ABSENCE
# --------------------------------------------------

def send_notification_for_absence(
    absence_record,
    sender,
    formatter,
    config
):
    """
    Format and send notifications to the parents
    linked to one absent student.

    NotificationSender handles parent validation,
    duplicate checking and notification records.
    """

    student_id = absence_record.get("student_id")
    parent_id = absence_record.get("parent_id")

    attendance_date = (
        absence_record.get("absence_date")
        or absence_record.get("date")
    )

    parent_email = absence_record.get("parent_email")
    parent_phone = absence_record.get("parent_phone")

    if not student_id or not parent_id or not attendance_date:
        logger.warning(
            "Skipping absence with missing student, parent or date: %s",
            absence_record
        )
        return 0

    # Check which delivery methods are available.
    email_enabled = (
        config.send_email and bool(parent_email)
    )

    sms_enabled = (
        config.send_sms and bool(parent_phone)
    )

    if email_enabled and sms_enabled:
        delivery_method = "both"

    elif email_enabled:
        delivery_method = "email"

    elif sms_enabled:
        delivery_method = "sms"

    else:
        logger.warning(
            "No enabled contact method for parent %s",
            parent_id
        )
        return 0

    # Format email and SMS messages.
    email_message = formatter.format_email(absence_record)
    sms_message = formatter.format_sms(absence_record)

    # Send using the existing notification service.
    results = sender.send_notification(
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

    count = sum(
        1 for sent in results.values() if sent
    )

    logger.info(
        "Notification results for student %s, parent %s: %s",
        student_id,
        parent_id,
        results
    )

    return count
