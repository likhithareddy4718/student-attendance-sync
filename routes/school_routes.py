
import requests

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)
from models.school import (
    get_all_schools,
    add_school_connection,
    disable_school_connection,
    enable_school_system,
    remove_school_connection
)
school_bp = Blueprint("school", __name__)


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


# Add a new school connection
@school_bp.route("/add-school", methods=["POST"])
def add_school():

    name = request.form.get("name", "").strip()
    api_endpoint = request.form.get("api_endpoint", "").strip()
    api_key = request.form.get("api_key", "").strip()

    if not name or not api_endpoint or not api_key:
        flash("Please enter all required details.", "error")
        return redirect(url_for("school.school_connections"))

    if not api_endpoint.startswith("https://"):
        flash("Please enter a valid HTTPS API address.", "error")
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


# Test a school's API endpoint
@school_bp.route("/test-school/<int:school_id>", methods=["POST"])
def test_school(school_id):

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

        if not endpoint or not endpoint.startswith("https://"):
            flash("Only valid HTTPS endpoints are allowed.", "error")
            return redirect(url_for("school.school_connections"))

        response = requests.get(
            endpoint,
            timeout=5
        )

        if response.status_code < 400:
            flash(
                f"Endpoint responded successfully. HTTP {response.status_code}.",
                "success"
            )
        else:
            flash(
                f"Endpoint returned HTTP {response.status_code}.",
                "error"
            )

    except requests.RequestException as error:
        print("API TEST ERROR:", error)
        flash("Unable to reach the API endpoint.", "error")

    except Exception as error:
        print("TEST SCHOOL ERROR:", error)
        flash("Unable to test school connection.", "error")

    return redirect(url_for("school.school_connections"))
