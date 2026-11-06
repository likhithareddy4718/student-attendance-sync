
from flask import Flask, redirect, url_for

from config import Config
from models import db
from routes.school_routes import school_bp
from routes.connections import connections_bp

app = Flask(__name__)

# Load database configuration from config.py
app.config.from_object(Config)

app.secret_key = app.config.get(
    "SECRET_KEY",
    "local-development-secret-key"
)

# Initialize SQLAlchemy
if not app.config.get("SQLALCHEMY_DATABASE_URI"):
    raise RuntimeError("Database URL is missing. Check config.py and .env.")

db.init_app(app)

# Register blueprints
app.register_blueprint(school_bp)
app.register_blueprint(connections_bp)


@app.route("/")
def home():
    return redirect(url_for("school.school_connections"))


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
