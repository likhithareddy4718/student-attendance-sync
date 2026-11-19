from functools import wraps
import bcrypt
from flask import session, redirect, url_for, flash, request, jsonify


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


def login_required(f):
    """
    Decorator ensuring an administrator is authenticated in session.
    Redirects unauthenticated browser requests to /login and returns 401 for JSON/API.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session or not session.get("school_id"):
            if request.is_json or request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "Unauthorized. Please log in."}), 401
            flash("Please log in to access this page.", "error")
            return redirect(url_for("flask_auth.login"))
        return f(*args, **kwargs)
    return decorated_function