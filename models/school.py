
from psycopg2.extras import RealDictCursor
from services.auth_service import get_db_connection
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def get_all_connected_schools():
    """Fetch only connected school systems."""

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, api_endpoint, is_connected
                FROM schools
                WHERE is_connected = TRUE
                ORDER BY id
            """)
            return cursor.fetchall()

    finally:
        conn.close()


def get_all_schools():
    """Fetch all school systems."""

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, api_endpoint, is_connected
                FROM schools
                ORDER BY id
            """)
            schools = cursor.fetchall()
            print("Database records fetched:", len(schools))
            return schools

    finally:
        conn.close()


def add_school_connection(name, api_endpoint, api_key):
    """Save school details and API credentials."""

    if not name or not api_endpoint or not api_key:
        raise ValueError("All fields are required.")

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cursor:

                cursor.execute("""
                    INSERT INTO schools
                    (name, api_endpoint, is_connected)
                    VALUES (%s, %s, TRUE)
                    RETURNING id
                """, (name, api_endpoint))

                school_id = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT INTO api_credentials
                    (school_id, api_key, api_token, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """, (school_id, api_key, None))

                return school_id

    finally:
        conn.close()


def add_school_system(name, api_endpoint):
    """Add a school without API credentials."""

    if not name or not api_endpoint:
        raise ValueError("School name and API endpoint are required.")

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO schools
                    (name, api_endpoint, is_connected)
                    VALUES (%s, %s, TRUE)
                    RETURNING id
                """, (name, api_endpoint))

                return cursor.fetchone()[0]

    finally:
        conn.close()


def disable_school_system(school_id):
    """Disable a school connection."""

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE schools
                    SET is_connected = FALSE
                    WHERE id = %s
                """, (school_id,))

                return cursor.rowcount > 0

    finally:
        conn.close()


def enable_school_system(school_id):
    """Enable a school connection."""

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE schools
                    SET is_connected = TRUE
                    WHERE id = %s
                """, (school_id,))

                return cursor.rowcount > 0

    finally:
        conn.close()


def remove_school_system(school_id):
    """Delete credentials and then remove the school."""

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cursor:

                cursor.execute("""
                    DELETE FROM api_credentials
                    WHERE school_id = %s
                """, (school_id,))

                cursor.execute("""
                    DELETE FROM schools
                    WHERE id = %s
                """, (school_id,))

                return cursor.rowcount > 0

    finally:
        conn.close()
    
def disable_school_connection(school_id):
    """Disable a school connection without deleting its data."""

    return disable_school_system(school_id)


def remove_school_connection(school_id):
    """Remove a school connection and its API credentials."""

    return remove_school_system(school_id)
