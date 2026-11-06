import streamlit as st

from pages.login import show_login_page
from services.auth_service import (
    find_administrator_by_email,
    log_login_attempt
)
from utils.security import verify_password


def handle_login():
    """
    Handle the login flow: show the login page, check credentials,
    and either log the admin in or show an error message.
    """

    # Show the login form
    credentials = show_login_page()

    # Stop if the form wasn't submitted
    if credentials is None:
        return

    email = credentials["email"]
    password = credentials["password"]

    # Validate email and password
    if not email or not password:
        st.error("Please enter both email and password.")
        return

    # Look up administrator
    admin = find_administrator_by_email(email)

    if admin is None:
        st.error("Email or password is incorrect.")
        log_login_attempt(email, False, "Email not found")
        return

    # Verify password
    password_is_correct = verify_password(
        password,
        admin["password_hash"]
    )

    if not password_is_correct:
        st.error("Email or password is incorrect.")
        log_login_attempt(email, False, "Incorrect password")
        return

    # Log successful login
    log_login_attempt(email, True, "Login successful")

    # Store admin information
    st.session_state.admin_id = admin["id"]
    st.session_state.admin_email = admin["email"]
    st.session_state.school_id = admin["school_id"]
    st.session_state.is_logged_in = True

    st.success("Login successful! Redirecting to dashboard...")
    st.info("You are now logged in. The dashboard will load on the next page refresh.")