import os
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlparse
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Parse DATABASE_URL if available to reuse credentials
main_db_url = os.getenv("DATABASE_URL")
if main_db_url:
    parsed = urlparse(main_db_url)
    default_user = parsed.username or "postgres"
    default_password = unquote(parsed.password) if parsed.password else ""
    default_host = parsed.hostname or "localhost"
    default_port = str(parsed.port or 5432)
else:
    default_user = "postgres"
    default_password = ""
    default_host = "localhost"
    default_port = "5432"

# Test database connection settings
TEST_DB_HOST = os.getenv('TEST_DB_HOST', default_host)
TEST_DB_PORT = os.getenv('TEST_DB_PORT', default_port)
TEST_DB_USER = os.getenv('TEST_DB_USER', default_user)
TEST_DB_PASSWORD = os.getenv('TEST_DB_PASSWORD', default_password)
TEST_DB_NAME = os.getenv('TEST_DB_NAME', 'student_attendance_sync_test')

TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL') or (
    f"postgresql://{TEST_DB_USER}:"
    f"{quote_plus(TEST_DB_PASSWORD)}@"
    f"{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"
)

# Test settings
TESTING = True
DEBUG = True

# API mock settings
MOCK_API_RESPONSES = True
API_TIMEOUT = 5

# Notification settings for testing
TEST_NOTIFICATION_EMAIL = 'test@example.com'
TEST_NOTIFICATION_PHONE = '+1234567890'

# Logging for tests
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'tests/test_logs.txt'