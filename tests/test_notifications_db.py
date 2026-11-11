
import pytest
from datetime import datetime, date

import psycopg2
from psycopg2.extras import RealDictCursor

from config.test_config import TEST_DATABASE_URL


class TestStudentParentNotificationDatabase:
    """Test student-parent relationships and notification records."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        self.conn = psycopg2.connect(TEST_DATABASE_URL)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        try:
            self._create_test_tables()
            yield
        finally:
            # Roll back test data and close the connection.
            # TEMP tables disappear automatically when the connection closes.
            self.conn.rollback()
            self.cursor.close()
            self.conn.close()

    def _create_test_tables(self):
        """Create temporary tables for isolated testing."""

        self.cursor.execute("""
            CREATE TEMP TABLE schools (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                api_endpoint VARCHAR(255),
                is_connected BOOLEAN
            )
        """)

        self.cursor.execute("""
            CREATE TEMP TABLE students (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                school_id INTEGER REFERENCES schools(id)
            )
        """)

        self.cursor.execute("""
            CREATE TEMP TABLE parents (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(255)
            )
        """)

        self.cursor.execute("""
            CREATE TEMP TABLE student_parents (
                id SERIAL PRIMARY KEY,
                student_id INTEGER REFERENCES students(id),
                parent_id INTEGER REFERENCES parents(id)
            )
        """)

        self.cursor.execute("""
            CREATE TEMP TABLE attendance_records (
                id SERIAL PRIMARY KEY,
                student_id INTEGER REFERENCES students(id),
                school_id INTEGER REFERENCES schools(id),
                date DATE,
                status VARCHAR(255),
                sync_timestamp TIMESTAMP
            )
        """)

        self.cursor.execute("""
            CREATE TEMP TABLE notifications (
                id SERIAL PRIMARY KEY,
                parent_id INTEGER REFERENCES parents(id),
                student_id INTEGER REFERENCES students(id),
                message TEXT,
                sent_at TIMESTAMP,
                status VARCHAR(255),
                delivery_method VARCHAR(255)
            )
        """)

    def test_student_parent_matching(self):
        """Check that one student can have two parents."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Lincoln High', 'https://api.lincoln.edu', True))
        school_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO students (name, school_id)
            VALUES (%s, %s) RETURNING id
        """, ('Alice Johnson', school_id))
        student_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO parents (name, email, phone)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Mom Johnson', 'mom@example.com', '+1234567890'))
        parent1_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO parents (name, email, phone)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Dad Johnson', 'dad@example.com', '+0987654321'))
        parent2_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO student_parents (student_id, parent_id)
            VALUES (%s, %s)
        """, (student_id, parent1_id))

        self.cursor.execute("""
            INSERT INTO student_parents (student_id, parent_id)
            VALUES (%s, %s)
        """, (student_id, parent2_id))

        self.cursor.execute("""
            SELECT p.id, p.name, p.email, p.phone
            FROM parents p
            JOIN student_parents sp ON p.id = sp.parent_id
            WHERE sp.student_id = %s
            ORDER BY p.id
        """, (student_id,))

        parents = self.cursor.fetchall()

        assert len(parents) == 2
        assert parents[0]['name'] == 'Mom Johnson'
        assert parents[1]['name'] == 'Dad Johnson'
        assert parents[0]['email'] == 'mom@example.com'
        assert parents[1]['phone'] == '+0987654321'

    def test_notification_created_on_absence(self):
        """Check that an absence notification record can be stored."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Lincoln High', 'https://api.lincoln.edu', True))
        school_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO students (name, school_id)
            VALUES (%s, %s) RETURNING id
        """, ('Bob Smith', school_id))
        student_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO parents (name, email, phone)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Parent Smith', 'parent@example.com', '+1111111111'))
        parent_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO student_parents (student_id, parent_id)
            VALUES (%s, %s)
        """, (student_id, parent_id))

        self.cursor.execute("""
            INSERT INTO attendance_records
                (student_id, school_id, date, status, sync_timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, school_id, date.today(), 'absent', datetime.now()))

        # Record a notification for testing.
        # This does not send an actual email or SMS.
        self.cursor.execute("""
            INSERT INTO notifications
                (parent_id, student_id, message, sent_at,
                 status, delivery_method)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            parent_id,
            student_id,
            f'Alert: Bob Smith was absent on {date.today()}',
            datetime.now(),
            'queued',
            'email'
        ))

        self.cursor.execute("""
            SELECT * FROM notifications
            WHERE parent_id = %s AND student_id = %s
        """, (parent_id, student_id))

        notification = self.cursor.fetchone()

        assert notification is not None
        assert notification['status'] == 'queued'
        assert 'absent' in notification['message'].lower()
        assert notification['delivery_method'] == 'email'

    def test_no_notification_for_present_student(self):
        """Check that the present-student test case has no notification record."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Lincoln High', 'https://api.lincoln.edu', True))
        school_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO students (name, school_id)
            VALUES (%s, %s) RETURNING id
        """, ('Carol White', school_id))
        student_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO parents (name, email, phone)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Parent White', 'parent@example.com', '+2222222222'))
        parent_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO student_parents (student_id, parent_id)
            VALUES (%s, %s)
        """, (student_id, parent_id))

        self.cursor.execute("""
            INSERT INTO attendance_records
                (student_id, school_id, date, status, sync_timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, school_id, date.today(), 'present', datetime.now()))

        self.cursor.execute("""
            SELECT * FROM notifications
            WHERE parent_id = %s AND student_id = %s
        """, (parent_id, student_id))

        notification = self.cursor.fetchone()

        assert notification is None

    def test_retrieve_parent_notifications(self):
        """Check that one parent can retrieve notifications for two students."""

        self.cursor.execute("""
            INSERT INTO schools (name, api_endpoint, is_connected)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Lincoln High', 'https://api.lincoln.edu', True))
        school_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO students (name, school_id)
            VALUES (%s, %s) RETURNING id
        """, ('Student One', school_id))
        student1_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO students (name, school_id)
            VALUES (%s, %s) RETURNING id
        """, ('Student Two', school_id))
        student2_id = self.cursor.fetchone()['id']

        self.cursor.execute("""
            INSERT INTO parents (name, email, phone)
            VALUES (%s, %s, %s) RETURNING id
        """, ('Parent Multi', 'parent@example.com', '+3333333333'))
        parent_id = self.cursor.fetchone()['id']

        for student_id in (student1_id, student2_id):
            self.cursor.execute("""
                INSERT INTO student_parents (student_id, parent_id)
                VALUES (%s, %s)
            """, (student_id, parent_id))

            self.cursor.execute("""
                INSERT INTO notifications
                    (parent_id, student_id, message, sent_at,
                     status, delivery_method)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                parent_id,
                student_id,
                f'Attendance alert for student {student_id}',
                datetime.now(),
                'queued',
                'email'
            ))

        self.cursor.execute("""
            SELECT n.*, s.name AS student_name
            FROM notifications n
            JOIN students s ON n.student_id = s.id
            WHERE n.parent_id = %s
            ORDER BY n.id
        """, (parent_id,))

        notifications = self.cursor.fetchall()

        assert len(notifications) == 2
        assert notifications[0]['student_name'] == 'Student One'
        assert notifications[1]['student_name'] == 'Student Two'
