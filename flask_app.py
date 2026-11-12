
from flask import Flask, redirect, url_for
from routes.flask_auth import flask_auth_bp
from pages.review_matches import review_matches_bp
from config import Config
from models import db
from routes.admin_routes import admin_routes_bp
from flask import Flask, redirect, url_for, render_template
from models import db, School
from screens.dashboard import get_dashboard_data
# Existing blueprints
from routes.school_routes import school_bp
from routes.connections import connections_bp

# New Student-Parent Matching blueprint
from pages.student_parent_matching import student_parent_bp
from routes.auth_routes import auth_bp


app = Flask(__name__)

# Load database configuration from config.py
app.config.from_object(Config)

app.secret_key = app.config["SECRET_KEY"]
# Initialize SQLAlchemy
if not app.config.get("SQLALCHEMY_DATABASE_URI"):
    raise RuntimeError(
        "Database URL is missing. Check config.py and .env."
    )

db.init_app(app)

# Register existing blueprints
app.register_blueprint(school_bp)
app.register_blueprint(connections_bp)
app.register_blueprint(flask_auth_bp)
# Register Student-Parent Matching blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(student_parent_bp)
app.register_blueprint(review_matches_bp)
app.register_blueprint(admin_routes_bp)

@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    try:
        school = School.query.first()

        if not school:
            return "No school connected. Please add a school first."

        dashboard_data = get_dashboard_data(school.id)

        return render_template(
            "dashboard.html",
            school=school,
            dashboard_data=dashboard_data
        )

    except Exception as e:
        print("DASHBOARD ERROR:", e)
        return f"Unable to load dashboard: {e}", 500
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
