
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
import psycopg2
import os

from sync.attendance_fetcher import fetch_attendance_from_api
from sync.attendance_converter import convert_record, load_status_map
from sync.attendance_storage import get_db_connection
from services.credential_storage_service import CredentialStorageService

from integrations.sync_orchestrator import SyncOrchestrator
from config.notifications import NotificationConfig


load_dotenv()


def run_sync_for_school(school_id: int) -> Dict[str, Any]:
    """
    Fetch, convert, store attendance records,
    detect absences and trigger parent notifications.
    """

    result = {
        "success": False,
        "fetched": 0,
        "converted": 0,
        "saved": 0,
        "notifications_sent": 0,
        "failed": 0,
        "errors": [],
        "message": ""
    }

    orchestration_started = False

    try:
        print(
            f"[{datetime.now()}] Starting sync for school {school_id}"
        )

        # ------------------------------------------
        # STEP 1: GET SCHOOL DETAILS
        # ------------------------------------------

        conn = get_db_connection()

        try:
            with conn.cursor() as cursor:

                cursor.execute(
                    "SELECT api_endpoint FROM schools WHERE id = %s",
                    (school_id,)
                )

                school = cursor.fetchone()

                if not school:
                    raise ValueError(
                        f"School {school_id} not found"
                    )

                api_endpoint = school[0]

                cursor.execute(
                    """
                    SELECT id, name
                    FROM students
                    WHERE school_id = %s
                    """,
                    (school_id,)
                )

                students = cursor.fetchall()

        finally:
            conn.close()

        student_map = {
            name.strip().lower(): student_id
            for student_id, name in students
        }

        # ------------------------------------------
        # STEP 2: GET API CREDENTIALS
        # ------------------------------------------

        demo_mode = (
            os.getenv("DEMO_MODE", "false").lower() == "true"
        )

        if demo_mode:
            api_key = ""
            print("Running in DEMO MODE")

        else:
            credential_service = CredentialStorageService()

            credentials = (
                credential_service.get_decrypted_credentials(
                    school_id
                )
            )

            if not credentials or not credentials.get("api_key"):
                raise ValueError(
                    "API credentials not found for this school"
                )

            api_key = credentials["api_key"]

        # ------------------------------------------
        # STEP 3: FETCH ATTENDANCE FROM API
        # ------------------------------------------

        raw_records = fetch_attendance_from_api(
            school_id,
            api_endpoint,
            api_key
        )

        result["fetched"] = len(raw_records)

        print(
            f"[{datetime.now()}] Fetched {result['fetched']} records"
        )

        if not raw_records:
            result["success"] = True
            result["message"] = "No attendance records fetched"

            log_sync_result(
                school_id,
                "success",
                result["message"]
            )

            return result

        # ------------------------------------------
        # STEP 4: CONVERT ATTENDANCE RECORDS
        # ------------------------------------------

        status_map = load_status_map()
        converted_records = []

        for raw_record in raw_records:

            record = convert_record(
                raw_record,
                school_id,
                status_map
            )

            if not record:
                continue

            student_name = (
                record["student_name"].strip().lower()
            )

            student_id = student_map.get(student_name)

            if not student_id:
                result["errors"].append(
                    f"Student not found: {record['student_name']}"
                )
                continue

            converted_records.append({
                "student_id": student_id,
                "date": record["date"],
                "status": record["status"]
            })

        result["converted"] = len(converted_records)

        print(
            f"[{datetime.now()}] Converted "
            f"{result['converted']} records"
        )

        if not converted_records:
            result["success"] = True
            result["message"] = (
                "No matching student attendance records found"
            )

            result["failed"] = len(result["errors"])

            log_sync_result(
                school_id,
                "warning",
                result["message"]
            )

            return result

        # ------------------------------------------
        # STEP 5: RUN COMPLETE SYNC ORCHESTRATOR
        # ------------------------------------------

        print(
            f"[{datetime.now()}] Starting attendance "
            "storage and notification workflow"
        )

        sync_conn = get_db_connection()

        try:
            notification_config = NotificationConfig()

            orchestrator = SyncOrchestrator(
                db_connection=sync_conn,
                notification_config=notification_config
            )

            orchestration_started = True

            sync_result = orchestrator.run_sync(
                school_id=school_id,
                attendance_data=converted_records
            )

        finally:
            sync_conn.close()

        # ------------------------------------------
        # STEP 6: UPDATE MAIN SYNC RESULT
        # ------------------------------------------

        result["saved"] = sync_result["records_synced"]

        result["notifications_sent"] = (
            sync_result["notifications_sent"]
        )

        result["errors"].extend(
            sync_result["errors"]
        )

        result["failed"] = len(result["errors"])

        result["success"] = (
            sync_result["success"]
            and result["failed"] == 0
        )

        result["message"] = (
            f"Sync complete: fetched {result['fetched']}, "
            f"converted {result['converted']}, "
            f"saved {result['saved']}, "
            f"notifications sent {result['notifications_sent']}, "
            f"failed {result['failed']}"
        )

        print(
            f"[{datetime.now()}] {result['message']}"
        )

        # SyncOrchestrator already records this sync in sync_logs.

    except Exception as e:

        result["success"] = False

        result["message"] = (
            f"Sync failed for school {school_id}: {str(e)}"
        )

        result["errors"].append(str(e))
        result["failed"] = len(result["errors"])

        print(
            f"[{datetime.now()}] {result['message']}"
        )

        # Avoid creating a duplicate log when the orchestrator
        # has already taken responsibility for sync logging.
        if not orchestration_started:
            log_sync_result(
                school_id,
                "error",
                result["message"]
            )

    return result


# --------------------------------------------------
# LOG SYNC RESULT
# --------------------------------------------------

def log_sync_result(
    school_id: int,
    status: str,
    message: str
) -> None:
    """
    Save the sync result in the sync_logs table.
    """

    conn = None

    try:
        conn = get_db_connection()

        with conn.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO sync_logs
                    (school_id, timestamp, status, error_message)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    school_id,
                    datetime.now(),
                    status,
                    message if status == "error" else None
                )
            )

        conn.commit()

        print(
            f"[{datetime.now()}] Logged sync result "
            f"for school {school_id}"
        )

    except psycopg2.Error as e:

        print(
            f"[{datetime.now()}] Failed to log sync result: {e}"
        )

        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    from flask_app import app

    with app.app_context():

        result = run_sync_for_school(school_id=8)

        print(f"\nSync result: {result}")
