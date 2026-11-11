import os
from urllib.parse import quote_plus

# Test database connection settings
TEST_DB_HOST = os.getenv('TEST_DB_HOST', 'localhost')
TEST_DB_PORT = os.getenv('TEST_DB_PORT', '5432')
TEST_DB_USER = os.getenv('TEST_DB_USER', 'postgres')
TEST_DB_PASSWORD = os.getenv(
    'TEST_DB_PASSWORD',
    'your-test-password-here'
)
TEST_DB_NAME = 'student_attendance_sync_test'

# Build the connection string for PostgreSQL
TEST_DATABASE_URL = (
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