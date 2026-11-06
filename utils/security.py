import bcrypt


def hash_password(plain_password):
    """
    Turn a plain password into a hashed version that can't be reversed.
    This is what we store in the database instead of the real password.
    """
    password_bytes = plain_password.encode('utf-8')

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(rounds=12)
    )

    return hashed.decode('utf-8')


def verify_password(plain_password, hashed_password):
    """
    Check if a plain password matches a hashed one.
    Returns True if they match, False otherwise.
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')

    return bcrypt.checkpw(password_bytes, hashed_bytes)