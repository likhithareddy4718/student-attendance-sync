
from flask import Flask, redirect, url_for, render_template, session

from config import Config
from models import db, School
from utils.security import login_required

from screens.dashboard import get_dashboard_data

# Blueprints
from routes.flask_auth import flask_auth_bp
from routes.school_routes import school_bp
from routes.connections import connections_bp
from routes.admin_routes import admin_routes_bp

# Other pages
from pages.review_matches import review_matches_bp
from pages.student_parent_matching import student_parent_bp


app = Flask(__name__)

# Load configuration
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]

# Check database configuration
if not app.config.get("SQLALCHEMY_DATABASE_URI"):
    raise RuntimeError(
        "Database URL is missing. Check config.py and .env."
    )

# Initialize database
db.init_app(app)

# Register blueprints
app.register_blueprint(flask_auth_bp)
app.register_blueprint(school_bp)
app.register_blueprint(connections_bp)
app.register_blueprint(student_parent_bp)
app.register_blueprint(review_matches_bp)
app.register_blueprint(admin_routes_bp)


# Homepage
@app.route("/")
def home():
    if "admin_id" not in session or not session.get("school_id"):
        return redirect(url_for("flask_auth.login"))
    return redirect(url_for("dashboard"))


# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    try:
        school_id = session.get("school_id")
        school = None
        if school_id:
            school = db.session.get(School, school_id)

        if not school:
            school = School.query.first()

        if not school:
            return redirect(
                url_for("school.school_connections")
            )

        dashboard_data = get_dashboard_data(school.id)

        return render_template(
            "dashboard.html",
            school=school,
            dashboard_data=dashboard_data
        )

    except Exception as e:
        print("DASHBOARD ERROR:", e)
        return "Unable to load dashboard. Please check server logs.", 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
