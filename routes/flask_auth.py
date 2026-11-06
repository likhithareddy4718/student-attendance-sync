
from flask import Blueprint, render_template, request, redirect, session, flash
from services.auth_service import authenticate_administrator

flask_auth_bp = Blueprint("flask_auth", __name__)


@flask_auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter email and password.")
            return redirect("/login")

        admin = authenticate_administrator(email, password)

        if admin is None:
            flash("Invalid email or password.")
            return redirect("/login")

        session.clear()
        session["admin_id"] = admin["id"]
        session["admin_email"] = admin["email"]
        session["school_id"] = admin["school_id"]

        return redirect("/student-parent/matching")

    return render_template("flask_login.html")


@flask_auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
