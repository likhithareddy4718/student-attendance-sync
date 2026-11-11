
from services.auth_service import get_db_connection
from utils.security import hash_password


ADMIN_NAME = "School Admin"
ADMIN_EMAIL = "admin@school.com"
ADMIN_PASSWORD = "Admin@12345"

conn = get_db_connection()

try:
    with conn:
        with conn.cursor() as cursor:

            # Check whether the school already exists
            cursor.execute(
                "SELECT id FROM schools WHERE name = %s LIMIT 1",
                ("Demo School",)
            )
            school = cursor.fetchone()

            # Create school if it does not exist
            if school:
                school_id = school[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO schools
                        (name, api_endpoint, is_connected)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    ("Demo School", None, False)
                )
                school_id = cursor.fetchone()[0]

            # Check whether administrator already exists
            cursor.execute(
                """
                SELECT id FROM administrators
                WHERE LOWER(email) = LOWER(%s)
                """,
                (ADMIN_EMAIL,)
            )

            existing_admin = cursor.fetchone()

            if existing_admin:
                print("Administrator already exists.")

            else:
                # Hash password before storing it
                password_hash = hash_password(ADMIN_PASSWORD)

                cursor.execute(
                    """
                    INSERT INTO administrators
                        (username, password_hash, email, school_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        ADMIN_NAME,
                        password_hash,
                        ADMIN_EMAIL,
                        school_id
                    )
                )

                print("Administrator account created successfully!")

finally:
    conn.close()
