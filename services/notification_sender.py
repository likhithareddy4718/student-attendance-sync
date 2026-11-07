
import logging
import os
import smtplib

from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional

import psycopg2

try:
    from twilio.rest import Client
except ImportError:
    Client = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from config.notifications import NotificationConfig

from services.notification_validator import (
    validate_notification_safe_to_send,
    NotificationValidationError
)

from services.deduplication import DeduplicationChecker


logger = logging.getLogger(__name__)


class NotificationSender:
    """
    Sends parent notifications through email or SMS.
    Checks for duplicate notifications before sending.
    Reports delivery failures to the caller.
    """

    def __init__(
        self,
        config: NotificationConfig,
        db_connection=None
    ):
        self.config = config
        self.sms_client = None

        self.db_connection = db_connection
        self.owns_db_connection = False
        self.deduplication_checker = None

        # Collect errors from individual delivery attempts.
        self.delivery_errors = []

        self.config.validate()

        # Initialize Twilio only when SMS is enabled.
        if (
            self.config.enabled
            and self.config.send_sms
            and self.config.sms.account_sid
            and self.config.sms.auth_token
        ):
            if Client is None:
                error = (
                    "Twilio package is not installed. "
                    "Run: pip install twilio"
                )
                self.delivery_errors.append(error)
                logger.error(error)

            else:
                try:
                    self.sms_client = Client(
                        self.config.sms.account_sid,
                        self.config.sms.auth_token
                    )

                    logger.info(
                        "Twilio SMS client initialized"
                    )

                except Exception as e:
                    self.delivery_errors.append(
                        f"Twilio initialization failed: {e}"
                    )
                    logger.exception(
                        "Failed to initialize Twilio client"
                    )

                    self.sms_client = None

    # --------------------------------------------------
    # DATABASE AND DEDUPLICATION
    # --------------------------------------------------

    def _get_deduplication_checker(self):
        """
        Get the database connection and deduplication checker.
        """

        if self.deduplication_checker is not None:
            return self.deduplication_checker

        if self.db_connection is None:

            if load_dotenv is not None:
                load_dotenv(
                    dotenv_path=os.path.join(
                        os.getcwd(), ".env"
                    )
                )

            database_url = os.getenv("DATABASE_URL")

            if not database_url:
                raise RuntimeError(
                    "DATABASE_URL is missing from .env"
                )

            self.db_connection = psycopg2.connect(
                database_url
            )

            self.owns_db_connection = True

        self.deduplication_checker = DeduplicationChecker(
            self.db_connection
        )

        return self.deduplication_checker

    def close(self):
        """
        Close the database connection only if this sender
        created that connection.
        """

        if (
            self.owns_db_connection
            and self.db_connection is not None
        ):
            self.db_connection.close()

            self.db_connection = None
            self.deduplication_checker = None
            self.owns_db_connection = False

    def _send_with_deduplication(
        self,
        parent_id: int,
        student_id: int,
        attendance_date: str,
        delivery_method: str,
        message: str,
        send_function
    ) -> bool:
        """
        Check for duplicates, send the message,
        and save its notification record.
        """

        try:
            checker = self._get_deduplication_checker()

            already_sent = checker.has_notification_been_sent(
                student_id=student_id,
                parent_id=parent_id,
                attendance_date=attendance_date,
                delivery_method=delivery_method
            )

            if already_sent:
                logger.warning(
                    "Duplicate %s notification skipped: "
                    "student_id=%s, parent_id=%s, date=%s",
                    delivery_method,
                    student_id,
                    parent_id,
                    attendance_date
                )

                return False

        except Exception as e:
            error = (
                f"{delivery_method} deduplication check failed: {e}"
            )

            self.delivery_errors.append(error)

            logger.exception(
                "Deduplication check failed. "
                "Notification will not be sent."
            )

            return False

        # Send only after the duplicate check succeeds.
        sent = send_function()

        if not sent:
            return False

        # Save a record only after provider acceptance.
        recorded = checker.mark_notification_sent(
            parent_id=parent_id,
            student_id=student_id,
            message=message,
            delivery_method=delivery_method
        )

        if not recorded:
            error = (
                f"{delivery_method} was accepted by the provider, "
                "but its database notification record could not "
                "be saved. A duplicate may be possible."
            )

            self.delivery_errors.append(error)

            logger.error(error)

        return True

    # --------------------------------------------------
    # SEND EMAIL
    # --------------------------------------------------

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str
    ) -> bool:
        """
        Send an email to a parent.
        Returns True when SMTP accepts the message.
        """

        if not self.config.enabled or not self.config.send_email:
            logger.info(
                "Email notifications are disabled."
            )
            return False

        if not recipient_email:
            error = "No recipient email provided."
            self.delivery_errors.append(error)
            logger.warning(error)
            return False

        if (
            not self.config.email.sender_email
            or not self.config.email.sender_password
        ):
            error = "Email sender credentials are missing."
            self.delivery_errors.append(error)
            logger.error(error)
            return False

        try:
            msg = MIMEMultipart()

            msg["From"] = self.config.email.sender_email
            msg["To"] = recipient_email
            msg["Subject"] = subject

            msg.attach(
                MIMEText(body, "plain", "utf-8")
            )

            with smtplib.SMTP(
                self.config.email.smtp_server,
                self.config.email.smtp_port,
                timeout=30
            ) as server:

                server.starttls()

                server.login(
                    self.config.email.sender_email,
                    self.config.email.sender_password
                )

                server.send_message(msg)

            logger.info(
                "Email accepted by SMTP server for %s",
                recipient_email
            )

            return True

        except smtplib.SMTPAuthenticationError as e:
            error = f"SMTP authentication failed: {e}"
            self.delivery_errors.append(error)

            logger.exception(
                "SMTP authentication failed. "
                "Check your Gmail App Password."
            )

            return False

        except Exception as e:
            error = f"Email delivery failed: {e}"
            self.delivery_errors.append(error)

            logger.exception(
                "Failed to send email to %s",
                recipient_email
            )

            return False

    # --------------------------------------------------
    # SEND SMS
    # --------------------------------------------------

    def send_sms(
        self,
        recipient_phone: str,
        message_body: str
    ) -> bool:
        """
        Send an SMS using Twilio.
        Returns True when Twilio accepts the message.
        """

        if not self.config.enabled or not self.config.send_sms:
            logger.info(
                "SMS notifications are disabled."
            )
            return False

        if not recipient_phone:
            error = "No recipient phone number provided."
            self.delivery_errors.append(error)
            logger.warning(error)
            return False

        if not self.config.sms.from_number:
            error = "Twilio sender phone number is missing."
            self.delivery_errors.append(error)
            logger.error(error)
            return False

        if not self.sms_client:
            error = (
                "SMS client is not initialized. "
                "Check Twilio credentials and installation."
            )
            self.delivery_errors.append(error)
            logger.error(error)
            return False

        try:
            message = self.sms_client.messages.create(
                body=message_body,
                from_=self.config.sms.from_number,
                to=recipient_phone
            )

            logger.info(
                "SMS accepted by Twilio. Message SID: %s",
                message.sid
            )

            return True

        except Exception as e:
            error = f"SMS delivery failed: {e}"
            self.delivery_errors.append(error)

            logger.exception(
                "Failed to send SMS to %s",
                recipient_phone
            )

            return False

    # --------------------------------------------------
    # MAIN NOTIFICATION METHOD
    # --------------------------------------------------

    def send_notification(
        self,
        parent_id: int,
        student_id: int,
        recipient_email: Optional[str],
        recipient_phone: Optional[str],
        email_subject: str,
        email_body: str,
        sms_body: str,
        delivery_method: str = "email",
        attendance_date: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Send notification through email, SMS, or both.

        Validates student-parent relationship,
        checks contact details, prevents duplicates,
        and collects delivery errors.
        """

        # Clear errors from the previous notification.
        self.delivery_errors = []

        if delivery_method not in ["email", "sms", "both"]:
            raise ValueError(
                "delivery_method must be email, sms, or both"
            )

        if attendance_date is None:
            attendance_date = date.today().isoformat()

        elif hasattr(attendance_date, "isoformat"):
            attendance_date = attendance_date.isoformat()

        else:
            attendance_date = str(attendance_date)[:10]

        results = {
            "email": False,
            "sms": False
        }

        # ------------------------------------------
        # EMAIL DELIVERY
        # ------------------------------------------

        if delivery_method in ["email", "both"]:

            if not self.config.enabled or not self.config.send_email:
                logger.info(
                    "Email delivery skipped because it is disabled."
                )

            elif recipient_email:

                try:
                    safe, reason = validate_notification_safe_to_send(
                        student_id,
                        parent_id,
                        "email"
                    )

                    if safe:
                        results["email"] = (
                            self._send_with_deduplication(
                                parent_id=parent_id,
                                student_id=student_id,
                                attendance_date=attendance_date,
                                delivery_method="email",
                                message=email_body,
                                send_function=lambda: self.send_email(
                                    recipient_email,
                                    email_subject,
                                    email_body
                                )
                            )
                        )

                    else:
                        error = (
                            f"Email notification blocked: {reason}"
                        )

                        self.delivery_errors.append(error)
                        logger.warning(error)

                except NotificationValidationError as e:
                    error = f"Email validation failed: {e}"
                    self.delivery_errors.append(error)

                    logger.exception(error)

                except Exception as e:
                    error = f"Unexpected email error: {e}"
                    self.delivery_errors.append(error)

                    logger.exception(error)

            else:
                error = (
                    f"Parent {parent_id} has no email address."
                )

                self.delivery_errors.append(error)
                logger.warning(error)

        # ------------------------------------------
        # SMS DELIVERY
        # ------------------------------------------

        if delivery_method in ["sms", "both"]:

            if not self.config.enabled or not self.config.send_sms:
                logger.info(
                    "SMS delivery skipped because it is disabled."
                )

            elif recipient_phone:

                try:
                    safe, reason = validate_notification_safe_to_send(
                        student_id,
                        parent_id,
                        "phone"
                    )

                    if safe:
                        results["sms"] = (
                            self._send_with_deduplication(
                                parent_id=parent_id,
                                student_id=student_id,
                                attendance_date=attendance_date,
                                delivery_method="sms",
                                message=sms_body,
                                send_function=lambda: self.send_sms(
                                    recipient_phone,
                                    sms_body
                                )
                            )
                        )

                    else:
                        error = (
                            f"SMS notification blocked: {reason}"
                        )

                        self.delivery_errors.append(error)
                        logger.warning(error)

                except NotificationValidationError as e:
                    error = f"SMS validation failed: {e}"
                    self.delivery_errors.append(error)

                    logger.exception(error)

                except Exception as e:
                    error = f"Unexpected SMS error: {e}"
                    self.delivery_errors.append(error)

                    logger.exception(error)

            else:
                error = (
                    f"Parent {parent_id} has no phone number."
                )

                self.delivery_errors.append(error)
                logger.warning(error)

        return results
