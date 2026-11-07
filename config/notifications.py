
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()


# --------------------------------------------------
# EMAIL CONFIGURATION
# --------------------------------------------------

@dataclass
class EmailConfig:
    """Settings for sending emails to parents."""

    smtp_server: str
    smtp_port: int
    sender_email: Optional[str]
    sender_password: Optional[str]


# --------------------------------------------------
# SMS CONFIGURATION
# --------------------------------------------------

@dataclass
class SMSConfig:
    """Settings for sending SMS messages to parents."""

    provider: str
    account_sid: Optional[str]
    auth_token: Optional[str]
    from_number: Optional[str]


# --------------------------------------------------
# MAIN NOTIFICATION CONFIGURATION
# --------------------------------------------------

class NotificationConfig:
    """Load and store notification settings from environment variables."""

    def __init__(self):

        # Email settings
        self.email = EmailConfig(
            smtp_server=os.getenv(
                "SMTP_SERVER",
                "smtp.gmail.com"
            ),

            smtp_port=int(
                os.getenv("SMTP_PORT", "587")
            ),

            sender_email=os.getenv("SENDER_EMAIL"),

            sender_password=os.getenv("SENDER_PASSWORD")
        )

        # SMS settings
        self.sms = SMSConfig(
            provider=os.getenv(
                "SMS_PROVIDER",
                "twilio"
            ),

            account_sid=os.getenv("TWILIO_ACCOUNT_SID"),

            auth_token=os.getenv("TWILIO_AUTH_TOKEN"),

            from_number=os.getenv("TWILIO_FROM_NUMBER")
        )

        # Notification controls
        self.enabled = (
            os.getenv(
                "NOTIFICATIONS_ENABLED",
                "false"
            ).lower() == "true"
        )

        self.send_email = (
            os.getenv(
                "SEND_EMAIL",
                "false"
            ).lower() == "true"
        )

        self.send_sms = (
            os.getenv(
                "SEND_SMS",
                "false"
            ).lower() == "true"
        )

    # ----------------------------------------------
    # VALIDATE NOTIFICATION SETTINGS
    # ----------------------------------------------

    def validate(self):
        """
        Check required settings before sending notifications.
        """

        # Notifications globally disabled
        if not self.enabled:
            return True

        # At least one delivery method must be enabled
        if not self.send_email and not self.send_sms:
            raise ValueError(
                "Enable at least one delivery method: "
                "SEND_EMAIL or SEND_SMS."
            )

        # Validate email configuration
        if self.send_email:

            if not self.email.sender_email:
                raise ValueError(
                    "SENDER_EMAIL environment variable is required."
                )

            if not self.email.sender_password:
                raise ValueError(
                    "SENDER_PASSWORD environment variable is required."
                )

        # Validate SMS configuration
        if self.send_sms:

            if not self.sms.account_sid:
                raise ValueError(
                    "TWILIO_ACCOUNT_SID environment variable is required."
                )

            if not self.sms.auth_token:
                raise ValueError(
                    "TWILIO_AUTH_TOKEN environment variable is required."
                )

            if not self.sms.from_number:
                raise ValueError(
                    "TWILIO_FROM_NUMBER environment variable is required."
                )

        return True


# --------------------------------------------------
# GLOBAL NOTIFICATION CONFIGURATION
# --------------------------------------------------

notification_config = NotificationConfig()
