
import requests
from urllib.parse import urlparse

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)

from models.school import (
    get_all_schools,
    add_school_connection,
    disable_school_connection,
    enable_school_system,
    remove_school_connection
)

from services.auth_service import get_db_connection


school_bp = Blueprint("school", __name__)


# Validate API endpoint
def is_valid_api_endpoint(endpoint):

    if not endpoint:
        return False

    parsed_url = urlparse(endpoint)

    # Allow HTTPS endpoints
    if parsed_url.scheme == "https":
        return True

    # Allow localhost only for development
    if (
        parsed_url.scheme == "http"
        and parsed_url.hostname in ["127.0.0.1", "localhost"]
        and parsed_url.port == 5000
    ):
        return True

    return False


# Display all school connections
@school_bp.route("/school-connections")
def school_connections():

    try:
        schools = get_all_schools()

        print("SCHOOLS FETCHED:", schools)
        print("NUMBER OF SCHOOLS:", len(schools))

        return render_template(
            "school_connections.html",
            schools=schools
        )

    except Exception as error:

        print("DATABASE ERROR:", error)

        flash("Unable to load school systems.", "error")

        return render_template(
            "school_connections.html",
            schools=[]
        )


# Add a new school connection using form
@school_bp.route("/add-school", methods=["POST"])
def add_school():

    name = request.form.get("name", "").strip()
    api_endpoint = request.form.get("api_endpoint", "").strip()
    api_key = request.form.get("api_key", "").strip()

    if not name or not api_endpoint or not api_key:

        flash("Please enter all required details.", "error")

        return redirect(url_for("school.school_connections"))

    if not is_valid_api_endpoint(api_endpoint):

        flash(
            "Please enter a valid HTTPS API address or localhost URL.",
            "error"
        )

        return redirect(url_for("school.school_connections"))

    try:

        school_id = add_school_connection(
            name,
            api_endpoint,
            api_key
        )

        flash(
            f"School connection added successfully! ID: {school_id}",
            "success"
        )

    except Exception as error:

        print("ADD SCHOOL ERROR:", error)

        flash("Unable to add school connection.", "error")

    return redirect(url_for("school.school_connections"))


# Test a new connection before saving using form
@school_bp.route("/test-new-connection", methods=["POST"])
def test_new_connection():

    api_endpoint = request.form.get("api_endpoint", "").strip()
    api_key = request.form.get("api_key", "").strip()

    if not api_endpoint or not api_key:

        flash("API address and API key are required.", "error")

        return redirect(url_for("school.school_connections"))

    if not is_valid_api_endpoint(api_endpoint):

        flash(
            "Please enter a valid HTTPS API address or localhost URL.",
            "error"
        )

        return redirect(url_for("school.school_connections"))

    try:

        response = requests.get(
            api_endpoint,
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            timeout=10
        )

        if response.status_code == 200:

            flash("API connection test successful!", "success")

        else:

            flash(
                f"API responded with HTTP {response.status_code}.",
                "error"
            )

    except requests.RequestException as error:

        print("API CONNECTION ERROR:", error)

        flash("Unable to connect to the school API.", "error")

    return redirect(url_for("school.school_connections"))


# Disable a school connection
@school_bp.route("/disable-school/<int:school_id>", methods=["POST"])
def disable_school(school_id):

    try:

        if disable_school_connection(school_id):

            flash("School connection disabled.", "success")

        else:

            flash("School not found.", "error")

    except Exception as error:

        print("DISABLE ERROR:", error)

        flash("Unable to disable school.", "error")

    return redirect(url_for("school.school_connections"))


# Enable a school connection
@school_bp.route("/enable-school/<int:school_id>", methods=["POST"])
def enable_school(school_id):

    try:

        if enable_school_system(school_id):

            flash("School connection enabled.", "success")

        else:

            flash("School not found.", "error")

    except Exception as error:

        print("ENABLE ERROR:", error)

        flash("Unable to enable school.", "error")

    return redirect(url_for("school.school_connections"))


# Remove a school connection
@school_bp.route("/remove-school/<int:school_id>", methods=["POST"])
def remove_school(school_id):

    try:

        if remove_school_connection(school_id):

            flash("School removed successfully.", "success")

        else:

            flash("School not found.", "error")

    except Exception as error:

        print("REMOVE ERROR:", error)

        flash("Unable to remove school.", "error")

    return redirect(url_for("school.school_connections"))


# Test an already saved school's API
@school_bp.route("/test-school/<int:school_id>", methods=["POST"])
def test_school(school_id):

    conn = None

    try:

        schools = get_all_schools()

        school = next(
            (item for item in schools if item["id"] == school_id),
            None
        )

        if not school:

            flash("School not found.", "error")

            return redirect(url_for("school.school_connections"))

        endpoint = school["api_endpoint"]

        if not is_valid_api_endpoint(endpoint):

            flash("Invalid API endpoint.", "error")

            return redirect(url_for("school.school_connections"))

        # Retrieve the saved API key
        conn = get_db_connection()

        with conn.cursor() as cursor:

            cursor.execute(
                """
                SELECT api_key
                FROM api_credentials
                WHERE school_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (school_id,)
            )

            credential = cursor.fetchone()

        if not credential or not credential[0]:

            flash("API credentials not found.", "error")

            return redirect(url_for("school.school_connections"))

        api_key = credential[0]

        response = requests.get(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            timeout=10
        )

        if response.status_code == 200:

            flash("School API connection successful!", "success")

        else:

            flash(
                f"API responded with HTTP {response.status_code}.",
                "error"
            )

    except requests.RequestException as error:

        print("API TEST ERROR:", error)

        flash("Unable to reach the API endpoint.", "error")

    except Exception as error:

        print("TEST SCHOOL ERROR:", error)

        flash("Unable to test school connection.", "error")

    finally:

        if conn:
            conn.close()

    return redirect(url_for("school.school_connections"))


# --------------------------------------------------
# LET'S TAM API ROUTES
# --------------------------------------------------


# API: Test a new school connection
@school_bp.route("/api/test-connection", methods=["POST"])
def api_test_connection():

    data = request.get_json(silent=True) or {}

    school_name = (data.get("school_name") or "").strip()
    api_endpoint = (data.get("api_endpoint") or "").strip()
    api_key = (data.get("api_key") or "").strip()

    if not school_name or not api_endpoint or not api_key:

        return jsonify({
            "success": False,
            "error": "Please fill in all fields."
        }), 400

    if not is_valid_api_endpoint(api_endpoint):

        return jsonify({
            "success": False,
            "error": "Invalid API endpoint."
        }), 400

    try:

        response = requests.get(
            api_endpoint,
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            timeout=10
        )

        if response.status_code == 200:

            return jsonify({
                "success": True,
                "message": "Connection successful!"
            }), 200

        return jsonify({
            "success": False,
            "error": f"API responded with HTTP {response.status_code}."
        }), 200

    except requests.RequestException as error:

        print("API TEST ERROR:", error)

        return jsonify({
            "success": False,
            "error": "Unable to connect to the school API."
        }), 200


# API: Save a new school connection
@school_bp.route("/api/save-connection", methods=["POST"])
def api_save_connection():

    data = request.get_json(silent=True) or {}

    school_name = (data.get("school_name") or "").strip()
    api_endpoint = (data.get("api_endpoint") or "").strip()
    api_key = (data.get("api_key") or "").strip()

    if not school_name or not api_endpoint or not api_key:

        return jsonify({
            "success": False,
            "error": "Please fill in all fields."
        }), 400

    if not is_valid_api_endpoint(api_endpoint):

        return jsonify({
            "success": False,
            "error": "Invalid API endpoint."
        }), 400

    try:

        school_id = add_school_connection(
            school_name,
            api_endpoint,
            api_key
        )

        return jsonify({
            "success": True,
            "message": "Connection saved successfully!",
            "school_id": school_id
        }), 201

    except Exception as error:

        print("API SAVE ERROR:", error)

        return jsonify({
            "success": False,
            "error": "Unable to save school connection."
        }), 500


# API: Get all saved school connections
@school_bp.route("/api/connections", methods=["GET"])
def api_get_connections():

    try:

        schools = get_all_schools()

        connections = []

        for school in schools:

            connections.append({
                "id": school["id"],
                "name": school["name"],
                "api_endpoint": school["api_endpoint"],
                "is_connected": school["is_connected"]
            })

        return jsonify({
            "success": True,
            "connections": connections
        }), 200

    except Exception as error:

        print("API GET CONNECTIONS ERROR:", error)

        return jsonify({
            "success": False,
            "error": "Unable to load connections.",
            "connections": []
        }), 500


# Mock School API for local testing
@school_bp.route("/mock-school-api", methods=["GET"])
def mock_school_api():

    api_key = request.headers.get("Authorization")

    if api_key != "Bearer demo_api_key_12345":

        return jsonify({
            "status": "error",
            "message": "Invalid API key"
        }), 401

    return jsonify({
        "status": "success",
        "message": "Mock School API connected successfully!",
        "school": "Demo School"
    }), 200
