
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password securely before storing it in the database."""

    if not password:
        raise ValueError("Password cannot be empty.")

    password_bytes = password.encode("utf-8")
    hashed_bytes = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed_bytes.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check whether a password matches its stored hash."""

    if not password or not password_hash:
        return False

    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False
