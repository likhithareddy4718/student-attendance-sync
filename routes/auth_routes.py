
from flask import Blueprint, render_template, request, redirect, session, flash

from services.auth_service import (
    find_administrator_by_email,
    log_login_attempt
)
from utils.security import verify_password


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def handle_login():

    # Display login page
    if request.method == "GET":
        if "admin_id" in session:
            return redirect("/student-parent/matching")

        return render_template("login.html")

    # Get submitted credentials
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    # Validate email and password
    if not email or not password:
        flash("Please enter both email and password.", "error")
        return redirect("/login")

    # Find administrator
    admin = find_administrator_by_email(email)

    if admin is None:
        log_login_attempt(email, False, "Email not found")
        flash("Email or password is incorrect.", "error")
        return redirect("/login")

    # Verify password
    password_is_correct = verify_password(
        password,
        admin["password_hash"]
    )

    if not password_is_correct:
        log_login_attempt(email, False, "Incorrect password")
        flash("Email or password is incorrect.", "error")
        return redirect("/login")

    # Log successful login
    log_login_attempt(email, True, "Login successful")

    # Clear old session and store administrator information
    session.clear()
    session["admin_id"] = admin["id"]
    session["admin_email"] = admin["email"]
    session["school_id"] = admin["school_id"]

    flash("Login successful!", "success")

    return redirect("/student-parent/matching")


@auth_bp.route("/logout")
def logout():

    session.clear()
    flash("You have been logged out.", "success")

    return redirect("/login")
