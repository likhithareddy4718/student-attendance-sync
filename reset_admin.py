
from services.auth_service import get_db_connection
from utils.security import hash_password

EMAIL = "admin@school.com"
PASSWORD = "Admin@12345"

conn = get_db_connection()

try:
    with conn:
        with conn.cursor() as cursor:

            # Find the existing administrator
            cursor.execute(
                """
                SELECT id
                FROM administrators
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (EMAIL,)
            )

            admin = cursor.fetchone()

            # Generate a fresh bcrypt password hash
            password_hash = hash_password(PASSWORD)

            if admin:
                # Update existing administrator password
                cursor.execute(
                    """
                    UPDATE administrators
                    SET password_hash = %s
                    WHERE id = %s
                    """,
                    (password_hash, admin[0])
                )

                print("Administrator password updated!")

            else:
                # Find or create the demo school
                cursor.execute(
                    """
                    SELECT id FROM schools
                    WHERE name = %s
                    LIMIT 1
                    """,
                    ("Demo School",)
                )

                school = cursor.fetchone()

                if school:
                    school_id = school[0]
                else:
                    cursor.execute(
                        """
                        INSERT INTO schools
                        (name, is_connected)
                        VALUES (%s, %s)
                        RETURNING id
                        """,
                        ("Demo School", False)
                    )
                    school_id = cursor.fetchone()[0]

                # Create administrator
                cursor.execute(
                    """
                    INSERT INTO administrators
                    (username, email, password_hash, school_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    ("School Admin", EMAIL, password_hash, school_id)
                )

                print("Administrator account created!")

finally:
    conn.close()
