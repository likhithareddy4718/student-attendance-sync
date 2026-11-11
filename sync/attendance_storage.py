
import os
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import execute_values


def get_db_connection():
    """
    Create a connection to the PostgreSQL database.
    Uses the DATABASE_URL environment variable.
    """
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Set it to: postgresql://username:password@localhost:5432/student_attendance_sync"
        )

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except psycopg2.OperationalError as e:
        print(f"[{datetime.now()}] Failed to connect to database: {e}")
        raise


def save_attendance_records(
    school_id: int,
    converted_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Save converted attendance records to the database.

    Each record should contain: student_id, date, status.
    """
    if not converted_records:
        return {'saved': 0, 'failed': 0, 'errors': []}

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        saved_count = 0
        failed_count = 0
        errors = []

        for record in converted_records:
            try:
                student_id = record.get('student_id')
                date = record.get('date')
                status = record.get('status')

                if not student_id or not date or not status:
                    failed_count += 1
                    errors.append(
                        f"Record missing required fields: {record}"
                    )
                    continue

                cursor.execute(
                    """
                    INSERT INTO attendance_records
                    (student_id, school_id, date, status, sync_timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (student_id, school_id, date) DO UPDATE
                    SET status = EXCLUDED.status,
                        sync_timestamp = EXCLUDED.sync_timestamp
                    """,
                    (student_id, school_id, date, status, datetime.now())
                )

                saved_count += 1

            except psycopg2.IntegrityError as e:
                failed_count += 1
                errors.append(
                    f"Database integrity error for record {record}: {e}"
                )
                conn.rollback()

            except Exception as e:
                failed_count += 1
                errors.append(
                    f"Unexpected error saving record {record}: {e}"
                )

        conn.commit()
        cursor.close()

        print(
            f"[{datetime.now()}] School {school_id}: "
            f"saved {saved_count}, failed {failed_count}"
        )

        return {
            'saved': saved_count,
            'failed': failed_count,
            'errors': errors
        }

    except Exception as e:
        print(
            f"[{datetime.now()}] Fatal error saving attendance records: {e}"
        )

        if conn:
            conn.rollback()

        return {
            'saved': 0,
            'failed': len(converted_records),
            'errors': [str(e)]
        }

    finally:
        if conn:
            conn.close()
