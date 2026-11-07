
import logging
import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from config.notifications import NotificationConfig
from integrations.sync_orchestrator import SyncOrchestrator


load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def setup_test_data(db_connection):
    """
    Create a test school, student, parent,
    and student-parent relationship.
    """

    cursor = db_connection.cursor(
        cursor_factory=RealDictCursor
    )

    try:
        # Create a test school.
        cursor.execute(
            """
            INSERT INTO schools
                (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (
                f"E2E Test School {datetime.now().strftime('%Y%m%d%H%M%S')}",
                "https://api.testschool.edu",
                True
            )
        )

        school_id = cursor.fetchone()["id"]

        logger.info("Created test school: %s", school_id)

        # Create a test student.
        cursor.execute(
            """
            INSERT INTO students (name, school_id)
            VALUES (%s, %s)
            RETURNING id
            """,
            ("Alice Johnson", school_id)
        )

        student_id = cursor.fetchone()["id"]

        logger.info("Created test student: %s", student_id)

        # Get test parent contact details from .env.
        parent_email = os.getenv("TEST_PARENT_EMAIL") or None
        parent_phone = os.getenv("TEST_PARENT_PHONE") or None

        # Create a test parent.
        cursor.execute(
            """
            INSERT INTO parents (name, email, phone)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (
                "Bob Johnson",
                parent_email,
                parent_phone
            )
        )

        parent_id = cursor.fetchone()["id"]

        logger.info("Created test parent: %s", parent_id)

        # Link student to parent.
        cursor.execute(
            """
            INSERT INTO student_parents
                (student_id, parent_id)
            VALUES (%s, %s)
            """,
            (student_id, parent_id)
        )

        db_connection.commit()

        logger.info(
            "Linked student %s with parent %s",
            student_id,
            parent_id
        )

        return school_id, student_id, parent_id

    except Exception:
        db_connection.rollback()
        logger.exception("Failed to create test data")
        raise

    finally:
        cursor.close()


def test_notification_flow():
    """
    Test the complete attendance and notification workflow.
    """

    db_connection = None

    try:
        # Connect using the project's DATABASE_URL.
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError(
                "DATABASE_URL is missing from .env"
            )

        db_connection = psycopg2.connect(database_url)

        logger.info("Connected to PostgreSQL database")

        # Create test school, student and parent.
        school_id, student_id, parent_id = setup_test_data(
            db_connection
        )

        # Load the existing notification configuration.
        # All settings are read from .env.
        config = NotificationConfig()

        logger.info(
            "Notifications enabled: %s",
            config.enabled
        )

        logger.info(
            "Email enabled: %s | SMS enabled: %s",
            config.send_email,
            config.send_sms
        )

        # Create the orchestrator.
        orchestrator = SyncOrchestrator(
            db_connection,
            config
        )

        logger.info("Sync orchestrator initialized")

        # Prepare one test absence.
        test_attendance_data = [
            {
                "student_id": student_id,
                "date": datetime.now().date().isoformat(),
                "status": "absent",
                "reason": "E2E test absence"
            }
        ]

        # Execute the complete workflow.
        logger.info("Starting end-to-end notification test")

        result = orchestrator.run_sync(
            school_id,
            test_attendance_data
        )

        logger.info("Sync result: %s", result)

        print("\n========== TEST RESULTS ==========")
        print("Success:", result["success"])
        print("Records synced:", result["records_synced"])
        print("Notifications sent:", result["notifications_sent"])
        print("Errors:", result["errors"])
        print("Test school ID:", school_id)
        print("Test student ID:", student_id)
        print("Test parent ID:", parent_id)
        print("==================================")

        if result["success"]:
            print("END-TO-END SYNC TEST PASSED")
        else:
            print("END-TO-END SYNC TEST FAILED")

        return result

    except Exception:
        logger.exception("End-to-end test failed")
        raise

    finally:
        if db_connection is not None:
            db_connection.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    logger.info("Starting notification flow test")

    test_notification_flow()

    logger.info("Test completed")
