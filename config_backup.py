
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(override=True)


class Config:
    """Application configuration settings."""

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgresql://", "postgresql+psycopg2://", 1
            )

    # Fallback if DATABASE_URL is not configured
    if not SQLALCHEMY_DATABASE_URI:
        db_user = os.getenv("DB_USER", "postgres")
        db_password = quote_plus(os.getenv("DB_PASSWORD", ""))
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "student_attendance_sync")

        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+psycopg2://{db_user}:{db_password}"
            f"@{db_host}:{db_port}/{db_name}"
        )

    # Disable unnecessary modification tracking
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask secret key
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-key-change-in-production"
    )
