
import os

from flask import Flask, redirect, url_for
from routes.school_routes import school_bp

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "local-development-secret-key"
)

app.register_blueprint(school_bp)


@app.route("/")
def home():
    return redirect(url_for("school.school_connections"))


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
