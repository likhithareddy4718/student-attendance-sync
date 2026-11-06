
from flask import Flask, redirect, url_for
from routes.flask_auth import flask_auth_bp
from pages.review_matches import review_matches_bp
from config import Config
from models import db

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

@app.route("/")
def home():
    return redirect(url_for("school.school_connections"))


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
