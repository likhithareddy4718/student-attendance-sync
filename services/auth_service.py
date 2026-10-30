
import os

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


# Load environment variables
load_dotenv(override=True)


def get_db_connection():
    """Connect to the PostgreSQL database."""

    load_dotenv(override=True)

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def find_administrator_by_email(email):
    """Find an administrator using their email."""

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    email,
                    password_hash,
                    school_id
                FROM administrators
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (email.strip(),)
            )

            return cursor.fetchone()

    finally:
        conn.close()


def log_login_attempt(email, success, details=None):
    """Save administrator login attempts."""

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO login_attempts
                    (email, success, details)
                    VALUES (%s, %s, %s)
                    """,
                    (email.strip(), success, details)
                )

    finally:
        conn.close()
