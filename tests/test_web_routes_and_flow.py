"""
Unit and integration tests for web routes, authentication flow, and template views.
"""

import io
import pytest
from flask_app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_unauthenticated_flow_redirects(client):
    """Unauthenticated users must be redirected to /login."""
    res = client.get("/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 302
    assert "/login" in res_dash.headers["Location"]


def test_login_page_renders(client):
    """GET /login should display the login template."""
    res = client.get("/login")
    assert res.status_code == 200
    assert b"Administrator Login" in res.data


def test_login_invalid_credentials(client):
    """POST /login with bad credentials must reject and stay on /login."""
    res = client.post("/login", data={"email": "invalid@school.com", "password": "wrong"})
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_login_success_and_dashboard_access(client):
    """Valid credentials redirect to /dashboard and populate session."""
    res = client.post(
        "/login",
        data={"email": "admin@school.com", "password": "Admin@12345"}
    )
    assert res.status_code == 302
    assert "/dashboard" in res.headers["Location"]

    with client.session_transaction() as sess:
        assert sess.get("admin_id") is not None
        assert sess.get("school_id") == 8

    # Authenticated / loads dashboard
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200
    assert b"Student Attendance Dashboard" in dash_res.data
    assert b"Connected School Information" in dash_res.data


def test_school_connections_flow(client):
    """Logged in admin can view and test connections."""
    client.post("/login", data={"email": "admin@school.com", "password": "Admin@12345"})

    res = client.get("/school-connections")
    assert res.status_code == 200
    assert b"Connected School Systems" in res.data
    assert b"main-nav" in res.data


def test_student_parent_matching_flow(client):
    """Logged in admin can view matching page and upload CSV."""
    client.post("/login", data={"email": "admin@school.com", "password": "Admin@12345"})

    res = client.get("/student-parent/matching")
    assert res.status_code == 200
    assert b"Student-Parent Matching" in res.data

    csv_data = b"student_id,student_name,parent_name,parent_email,parent_phone\n1,Aarav Sharma,Sunita Sharma,sunita@example.com,9876543210\n"
    upload_res = client.post(
        "/student-parent/upload-csv",
        data={"file": (io.BytesIO(csv_data), "test_contacts.csv")},
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 200
    json_data = upload_res.get_json()
    assert "preview" in json_data


def test_review_matches_get_no_405(client):
    """GET /review-matches/view must render without 405 Method Not Allowed."""
    client.post("/login", data={"email": "admin@school.com", "password": "Admin@12345"})

    res = client.get("/review-matches/view")
    assert res.status_code == 200
    assert b"Review Matches" in res.data


def test_sync_activity_log(client):
    """Sync activity log loads with navigation."""
    client.post("/login", data={"email": "admin@school.com", "password": "Admin@12345"})

    res = client.get("/admin/sync-activity-log")
    assert res.status_code == 200
    assert b"Sync Activity Log" in res.data
    assert b"main-nav" in res.data


def test_sync_error_details_404_on_missing(client):
    """Non-existent sync log returns 404."""
    client.post("/login", data={"email": "admin@school.com", "password": "Admin@12345"})

    res = client.get("/admin/sync-error-details/999999")
    assert res.status_code == 404


def test_logout_clears_session(client):
    """Logout clears session and blocks protected routes."""
    client.post("/login", data={"email": "admin@school.com", "password": "Admin@12345"})
    logout_res = client.get("/logout")
    assert logout_res.status_code == 302
    assert "/login" in logout_res.headers["Location"]

    # Blocked after logout
    for url in ["/dashboard", "/school-connections", "/student-parent/matching", "/admin/sync-activity-log"]:
        res = client.get(url)
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]
