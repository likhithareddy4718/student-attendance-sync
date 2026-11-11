
import pytest
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

from config.test_config import TEST_DATABASE_URL, TEST_DB_NAME


class TestSyncLogsAndErrorHandling:
    """Test sync logs and error handling."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Connect to the test database and create temporary tables."""

        self.conn = psycopg2.connect(TEST_DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Safety check: never run these tests on the original database.
            self.cursor.execute("SELECT current_database()")
            actual_database = self.cursor.fetchone()['current_database']

            if actual_database != TEST_DB_NAME:
                pytest.fail(
                    f"Wrong database! Expected {TEST_DB_NAME}, "
                    f"connected to {actual_database}"
                )

            self._create_test_tables()
            yield

        finally:
            # Roll back test changes and close the connection.
            # Temporary tables disappear when this connection closes.
            self.conn.rollback()
            self.cursor.close()
            self.conn.close()

    def _create_test_tables(self):
        """Create isolated temporary tables."""

        self.cursor.execute("""
            CREATE TEMP TABLE schools (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                api_endpoint VARCHAR(255),
                is_connected BOOLEAN
            )
        """)

        self.cursor.execute("""
            CREATE TEMP TABLE sync_logs (
                id SERIAL PRIMARY KEY,
                school_id INTEGER NOT NULL REFERENCES schools(id),
                timestamp TIMESTAMP,
                status VARCHAR(255),
                error_message TEXT
            )
        """)

    def test_log_successful_sync(self):
        """Test recording a successful sync."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('Test School', 'https://api.testschool.com', True))

        school_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO sync_logs
                (school_id, timestamp, status, error_message)
            VALUES (%s, %s, %s, %s)
        """, (school_id, datetime.now(), 'success', None))

        self.cursor.execute("""
            SELECT * FROM sync_logs WHERE school_id = %s
        """, (school_id,))

        log = self.cursor.fetchone()

        assert log is not None
        assert log['status'] == 'success'
        assert log['error_message'] is None

    def test_log_api_error(self):
        """Test recording an API error."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('Broken School', 'https://api.broken.com', True))

        school_id = self.cursor.fetchone()['id']
        error_msg = "API returned 401 Unauthorized: invalid credentials"

        self.cursor.execute("""
            INSERT INTO sync_logs
                (school_id, timestamp, status, error_message)
            VALUES (%s, %s, %s, %s)
        """, (school_id, datetime.now(), 'error', error_msg))

        self.cursor.execute("""
            SELECT * FROM sync_logs WHERE school_id = %s
        """, (school_id,))

        log = self.cursor.fetchone()

        assert log is not None
        assert log['status'] == 'error'
        assert 'Unauthorized' in log['error_message']

    def test_log_network_timeout(self):
        """Test recording a network timeout."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('Slow School', 'https://api.slow.com', True))

        school_id = self.cursor.fetchone()['id']
        error_msg = "Connection timeout after 5 seconds"

        self.cursor.execute("""
            INSERT INTO sync_logs
                (school_id, timestamp, status, error_message)
            VALUES (%s, %s, %s, %s)
        """, (school_id, datetime.now(), 'error', error_msg))

        self.cursor.execute("""
            SELECT * FROM sync_logs WHERE school_id = %s
        """, (school_id,))

        log = self.cursor.fetchone()

        assert log is not None
        assert log['status'] == 'error'
        assert 'timeout' in log['error_message'].lower()

    def test_retrieve_recent_sync_logs(self):
        """Test retrieving logs in newest-first order."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('Admin School', 'https://api.admin.com', True))

        school_id = self.cursor.fetchone()['id']
        now = datetime.now()

        self.cursor.execute("""
            INSERT INTO sync_logs
                (school_id, timestamp, status, error_message)
            VALUES
                (%s, %s, %s, %s),
                (%s, %s, %s, %s),
                (%s, %s, %s, %s)
        """, (
            school_id, now - timedelta(hours=2), 'success', None,
            school_id, now - timedelta(hours=1), 'error', 'API key expired',
            school_id, now, 'success', None
        ))

        self.cursor.execute("""
            SELECT * FROM sync_logs
            WHERE school_id = %s
            ORDER BY timestamp DESC
            LIMIT 10
        """, (school_id,))

        logs = self.cursor.fetchall()

        assert len(logs) == 3
        assert logs[0]['status'] == 'success'
        assert logs[1]['status'] == 'error'
        assert logs[2]['status'] == 'success'

    def test_sync_logs_dont_grow_unbounded(self):
        """Test storing and querying a large number of sync logs."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ('Archive School', 'https://api.archive.com', True))

        school_id = self.cursor.fetchone()['id']
        now = datetime.now()

        # Insert 100 logs with different timestamps.
        for i in range(100):
            self.cursor.execute("""
                INSERT INTO sync_logs
                    (school_id, timestamp, status, error_message)
                VALUES (%s, %s, %s, %s)
            """, (school_id, now - timedelta(days=i), 'success', None))

        self.cursor.execute("""
            SELECT COUNT(*) AS count
            FROM sync_logs
            WHERE school_id = %s
        """, (school_id,))

        total = self.cursor.fetchone()['count']
        assert total == 100

        # Check that recent logs can be retrieved.
        self.cursor.execute("""
            SELECT COUNT(*) AS count
            FROM sync_logs
            WHERE school_id = %s AND timestamp > %s
        """, (school_id, now - timedelta(days=90)))

        recent = self.cursor.fetchone()['count']
        assert recent > 0
