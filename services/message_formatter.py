
import logging
from datetime import date, datetime
from typing import Dict, Optional, Any


# Logger setup
logger = logging.getLogger(__name__)


# --------------------------------------------------
# MESSAGE FORMATTER
# --------------------------------------------------

class MessageFormatter:
    """
    Converts absence information into clear messages
    for parents through email and SMS.
    """

    def __init__(self, school_name: str = "Your School"):
        """
        Initialize formatter with school name.
        """
        self.school_name = school_name

    # --------------------------------------------------
    # FORMAT EMAIL MESSAGE
    # --------------------------------------------------

    def format_email(self, absence: Dict[str, Any]) -> Dict[str, str]:
        """
        Create an email subject and body from absence data.
        """

        student_name = absence.get("student_name") or "Your child"

        parent_name = absence.get("parent_name") or "Parent"

        # Accept both date and absence_date fields
        date_obj = (
            absence.get("date")
            or absence.get("absence_date")
        )

        reason = absence.get("reason") or "Not specified"

        # Format date
        if isinstance(date_obj, (datetime, date)):

            date_str = date_obj.strftime("%A, %B %d, %Y")

        elif date_obj:

            date_str = str(date_obj)

        else:

            date_str = "Today"

        # Email subject
        subject = (
            f"Attendance Alert: {student_name} "
            f"was absent on {date_str}"
        )

        # Email body
        body = f"""Hello {parent_name},

This is a message from {self.school_name}.

We wanted to let you know that {student_name} was marked absent on {date_str}.

Absence reason: {reason}

If you have any questions or believe this is an error, please contact the school office.

Best regards,
{self.school_name} Attendance System
"""

        return {
            "subject": subject,
            "body": body
        }

    # --------------------------------------------------
    # FORMAT SMS MESSAGE
    # --------------------------------------------------

    def format_sms(self, absence: Dict[str, Any]) -> str:
        """
        Create a short SMS message from absence data.
        """

        student_name = absence.get("student_name") or "Your child"

        date_obj = (
            absence.get("date")
            or absence.get("absence_date")
        )

        reason = absence.get("reason") or "Not specified"

        # Short date format for SMS
        if isinstance(date_obj, (datetime, date)):

            date_str = date_obj.strftime("%b %d")

        elif date_obj:

            date_str = str(date_obj)

        else:

            date_str = "today"

        # Create SMS
        message = (
            f"{self.school_name}: {student_name} was absent "
            f"on {date_str}. Reason: {reason}. "
            f"Reply STOP to opt out."
        )

        return message

    # --------------------------------------------------
    # VALIDATE MESSAGE
    # --------------------------------------------------

    def validate_message(
        self,
        message: str,
        message_type: str = "sms"
    ) -> bool:
        """
        Check whether a message is valid.

        SMS messages longer than 160 characters
        generate a warning.
        """

        # Check empty message
        if not message or not isinstance(message, str):

            logger.warning(
                "Message is empty or not a string: %s",
                message
            )

            return False

        # Check SMS length
        if message_type == "sms" and len(message) > 160:

            logger.warning(
                "SMS message is %s characters (over 160). "
                "It may be split into multiple messages.",
                len(message)
            )

        return True
