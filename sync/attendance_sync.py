
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
import psycopg2
import os
from sync.attendance_fetcher import fetch_attendance_from_api
from sync.attendance_converter import convert_record, load_status_map
from sync.attendance_storage import save_attendance_records, get_db_connection
from services.credential_storage_service import CredentialStorageService


load_dotenv()


def run_sync_for_school(school_id: int) -> Dict[str, Any]:
    """
    Fetch, convert, and store attendance records for one school.
    """

    result = {
        'success': False,
        'fetched': 0,
        'converted': 0,
        'saved': 0,
        'failed': 0,
        'errors': [],
        'message': ''
    }

    try:
        print(f"[{datetime.now()}] Starting sync for school {school_id}")

        # Step 1: Get school API endpoint
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT api_endpoint FROM schools WHERE id = %s",
            (school_id,)
        )
        school = cursor.fetchone()

        if not school:
            raise ValueError(f"School {school_id} not found")

        api_endpoint = school[0]

        cursor.execute(
            "SELECT id, name FROM students WHERE school_id = %s",
            (school_id,)
        )
        students = cursor.fetchall()

        cursor.close()
        conn.close()

        # Create student name-to-ID mapping
        student_map = {
            name.strip().lower(): student_id
            for student_id, name in students
        }

        # Step 2: Get decrypted API credentials
        # Step 2: Get API credentials only in real API mode
        demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        if demo_mode:
            api_key = ""
            print("Running in DEMO MODE")
        else:
            credential_service = CredentialStorageService()
            credentials = credential_service.get_decrypted_credentials(school_id)
            if not credentials or not credentials.get("api_key"):
                raise ValueError("API credentials not found for this school")
            api_key = credentials["api_key"]
        # Step 3: Fetch attendance records
        raw_records = fetch_attendance_from_api(
            school_id,
            api_endpoint,
            api_key
        )

        result['fetched'] = len(raw_records)

        print(f"[{datetime.now()}] Fetched {result['fetched']} records")

        if not raw_records:
            result['success'] = True
            result['message'] = "No attendance records fetched"
            log_sync_result(school_id, 'success', result['message'])
            return result

        # Step 4: Convert records
        status_map = load_status_map()
        converted_records = []

        for raw_record in raw_records:
            record = convert_record(raw_record, school_id, status_map)

            if not record:
                continue

            student_name = record['student_name'].strip().lower()
            student_id = student_map.get(student_name)

            if not student_id:
                result['errors'].append(
                    f"Student not found: {record['student_name']}"
                )
                continue

            converted_records.append({
                'student_id': student_id,
                'date': record['date'],
                'status': record['status']
            })

        result['converted'] = len(converted_records)

        print(f"[{datetime.now()}] Converted {result['converted']} records")

        if not converted_records:
            result['success'] = True
            result['message'] = "No matching student attendance records found"
            result['failed'] = len(result['errors'])
            log_sync_result(school_id, 'warning', result['message'])
            return result

        # Step 5: Store attendance records
        storage_result = save_attendance_records(
            school_id,
            converted_records
        )

        result['saved'] = storage_result['saved']
        result['failed'] = storage_result['failed'] + len(result['errors'])
        result['errors'].extend(storage_result['errors'])

        # Step 6: Build result message
        result['success'] = result['failed'] == 0

        result['message'] = (
            f"Sync complete: fetched {result['fetched']}, "
            f"converted {result['converted']}, "
            f"saved {result['saved']}, "
            f"failed {result['failed']}"
        )

        print(f"[{datetime.now()}] {result['message']}")

        log_sync_result(
            school_id,
            'success' if result['success'] else 'warning',
            result['message']
        )

    except Exception as e:
        result['success'] = False
        result['message'] = f"Sync failed for school {school_id}: {str(e)}"
        result['errors'].append(str(e))

        print(f"[{datetime.now()}] {result['message']}")

        log_sync_result(school_id, 'error', str(e))

    return result


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
        cursor = conn.cursor()

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
                message if status == 'error' else None
            )
        )

        conn.commit()
        cursor.close()

        print(f"[{datetime.now()}] Logged sync result for school {school_id}")

    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Failed to log sync result: {e}")

        if conn:
            conn.rollback()

    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    from flask_app import app

    with app.app_context():
        result = run_sync_for_school(school_id=8)
        print(f"\nSync result: {result}")
