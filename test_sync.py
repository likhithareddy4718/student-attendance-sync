
#!/usr/bin/env python3

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sync.attendance_sync import run_sync_for_school


def get_connected_schools():
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("[ERROR] DATABASE_URL is not set.")
        return []

    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name FROM schools WHERE is_connected = TRUE AND id = 8")
                return cursor.fetchall()

    except psycopg2.OperationalError as e:
        print(f"[ERROR] Database connection failed: {e}")
        return []


def main():
    print(f"\n[{datetime.now()}] === Attendance Sync Test ===")
    print(f"[{datetime.now()}] Looking for connected schools...\n")

    schools = get_connected_schools()

    if not schools:
        print("No connected schools found.")
        return

    school_id, school_name = schools[0]

    print(f"Testing with school: {school_name} (ID: {school_id})")

    result = run_sync_for_school(school_id)

    print("\n=== Sync Result ===")
    print(f"Success: {result['success']}")
    print(f"Fetched: {result['fetched']} records")
    print(f"Converted: {result['converted']} records")
    print(f"Saved: {result['saved']} records")
    print(f"Failed: {result['failed']} records")

    if result['errors']:
        print("Errors:")
        for error in result['errors']:
            print(f"- {error}")

    print(f"\nMessage: {result['message']}")
    print(f"\n[{datetime.now()}] === Test Complete ===")


if __name__ == '__main__':
    main()
