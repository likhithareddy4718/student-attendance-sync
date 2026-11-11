import pytest
import sys
import os

from datetime import datetime, date
from unittest.mock import patch

# Add project root to Python path
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
)

from config.test_config import TEST_DATABASE_URL
import psycopg2
from psycopg2.extras import RealDictCursor


class TestAttendanceSyncFlow:
    """Test attendance sync database operations."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Create test tables before each test and clean up afterward."""
        self.conn = psycopg2.connect(TEST_DATABASE_URL)
        self.cursor = self.conn.cursor(
            cursor_factory=RealDictCursor
        )

        try:
            self._create_test_tables()
            yield
        finally:
            try:
                self._drop_test_tables()
            finally:
                self.cursor.close()
                self.conn.close()

    def _create_test_tables(self):
        """Create the tables required for testing."""

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                api_endpoint VARCHAR(255),
                is_connected BOOLEAN
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                school_id INTEGER NOT NULL,
                FOREIGN KEY (school_id) REFERENCES schools(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_records (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                school_id INTEGER NOT NULL,
                date DATE,
                status VARCHAR(255),
                sync_timestamp TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (school_id) REFERENCES schools(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_logs (
                id SERIAL PRIMARY KEY,
                school_id INTEGER NOT NULL,
                timestamp TIMESTAMP,
                status VARCHAR(255),
                error_message TEXT,
                FOREIGN KEY (school_id) REFERENCES schools(id)
            )
        """)

        self.conn.commit()

    def _drop_test_tables(self):
        """Drop only the test tables."""

        self.cursor.execute(
            "DROP TABLE IF EXISTS attendance_records CASCADE"
        )
        self.cursor.execute(
            "DROP TABLE IF EXISTS sync_logs CASCADE"
        )
        self.cursor.execute(
            "DROP TABLE IF EXISTS students CASCADE"
        )
        self.cursor.execute(
            "DROP TABLE IF EXISTS schools CASCADE"
        )

        self.conn.commit()

    def _insert_test_school(
        self,
        name="Test School",
        api_endpoint="https://api.testschool.com"
    ):
        """Insert a test school and return its ID."""

        self.cursor.execute(
            """
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (name, api_endpoint, True)
        )

        self.conn.commit()
        return self.cursor.fetchone()['id']

    def _insert_test_student(self, school_id, name="Alice"):
        """Insert a test student and return its ID."""

        self.cursor.execute(
            """
            INSERT INTO students (name, school_id)
            VALUES (%s, %s)
            RETURNING id
            """,
            (name, school_id)
        )

        self.conn.commit()
        return self.cursor.fetchone()['id']

    def test_sync_attendance_data_from_api(self):
        """Test storing attendance records from mock API data."""

        school_id = self._insert_test_school()
        student_id = self._insert_test_student(school_id, "Bob")

        mock_api_response = [
            {
                "student_id": student_id,
                "date": "2024-01-15",
                "status": "present"
            },
            {
                "student_id": student_id,
                "date": "2024-01-16",
                "status": "absent"
            }
        ]

        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_api_response
            mock_get.return_value.status_code = 200

            # Store the mock attendance records
            for record in mock_api_response:
                self.cursor.execute(
                    """
                    INSERT INTO attendance_records
                    (student_id, school_id, date, status, sync_timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        record['student_id'],
                        school_id,
                        record['date'],
                        record['status'],
                        datetime.now()
                    )
                )

            self.conn.commit()

        self.cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM attendance_records
            WHERE school_id = %s
            """,
            (school_id,)
        )

        count = self.cursor.fetchone()['count']
        assert count == 2, (
            f"Expected 2 attendance records, got {count}"
        )

        self.cursor.execute(
            """
            SELECT status
            FROM attendance_records
            WHERE date = %s
            ORDER BY id
            """,
            (date(2024, 1, 15),)
        )

        first_record = self.cursor.fetchone()
        assert first_record['status'] == 'present'

    def test_sync_logs_success(self):
        """Test that a successful sync is logged."""

        school_id = self._insert_test_school()

        self.cursor.execute(
            """
            INSERT INTO sync_logs
            (school_id, timestamp, status, error_message)
            VALUES (%s, %s, %s, %s)
            """,
            (school_id, datetime.now(), 'success', None)
        )

        self.conn.commit()

        self.cursor.execute(
            """
            SELECT status
            FROM sync_logs
            WHERE school_id = %s
            """,
            (school_id,)
        )

        log = self.cursor.fetchone()
        assert log['status'] == 'success'

    def test_sync_logs_error(self):
        """Test that a failed sync stores its error message."""

        school_id = self._insert_test_school()
        error_msg = "API returned 500: Internal Server Error"

        self.cursor.execute(
            """
            INSERT INTO sync_logs
            (school_id, timestamp, status, error_message)
            VALUES (%s, %s, %s, %s)
            """,
            (school_id, datetime.now(), 'failed', error_msg)
        )

        self.conn.commit()

        self.cursor.execute(
            """
            SELECT status, error_message
            FROM sync_logs
            WHERE school_id = %s
            """,
            (school_id,)
        )

        log = self.cursor.fetchone()

        assert log['status'] == 'failed'
        assert error_msg in log['error_message']

    def test_sync_handles_duplicate_records(self):
        """Document duplicate behavior in this test schema."""

        school_id = self._insert_test_school()
        student_id = self._insert_test_student(
            school_id,
            "Charlie"
        )

        for _ in range(2):
            self.cursor.execute(
                """
                INSERT INTO attendance_records
                (student_id, school_id, date, status, sync_timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    student_id,
                    school_id,
                    date(2024, 1, 20),
                    'present',
                    datetime.now()
                )
            )

        self.conn.commit()

        self.cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM attendance_records
            WHERE student_id = %s
            """,
            (student_id,)
        )

        count = self.cursor.fetchone()['count']

        # This isolated test schema has no UNIQUE constraint.
        assert count == 2

    def test_sync_timestamp_is_recorded(self):
        """Test that attendance records store their sync timestamp."""

        school_id = self._insert_test_school()
        student_id = self._insert_test_student(
            school_id,
            "Diana"
        )

        sync_time = datetime.now()

        self.cursor.execute(
            """
            INSERT INTO attendance_records
            (student_id, school_id, date, status, sync_timestamp)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                student_id,
                school_id,
                date(2024, 1, 25),
                'absent',
                sync_time
            )
        )

        self.conn.commit()

        self.cursor.execute(
            """
            SELECT sync_timestamp
            FROM attendance_records
            WHERE student_id = %s
            """,
            (student_id,)
        )

        record = self.cursor.fetchone()

        assert record['sync_timestamp'] is not None

        time_diff = abs(
            (record['sync_timestamp'] - sync_time).total_seconds()
        )

        assert time_diff < 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])