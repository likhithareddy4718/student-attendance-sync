
import streamlit as st

from pages.login import show_login_page
from services.auth_service import find_administrator_by_email, log_login_attempt
from utils.security import verify_password


def handle_login():
    """
    Handle administrator login.
    Verify email and password using the database.
    """

    # Check existing login session
    if st.session_state.get("authenticated", False):
        admin_name = st.session_state.get(
            "admin_name", "Administrator"
        )

        st.success(f"Welcome, {admin_name}!")

        if st.button("Logout"):
            for key in [
                "authenticated",
                "admin_id",
                "admin_name",
                "admin_email",
                "school_id"
            ]:
                st.session_state.pop(key, None)

            st.rerun()

        return

    # Display login page
    credentials = show_login_page()

    if credentials is None:
        return

    email = credentials["email"].strip()
    password = credentials["password"]

    # Find administrator using email
    try:
        administrator = find_administrator_by_email(email)

    except Exception:
        st.error("Unable to connect to the database. Please try again.")
        return

    # Verify password
    password_is_valid = False

    if administrator:
        stored_hash = administrator.get("password_hash", "")

        password_is_valid = verify_password(
            password,
            stored_hash
        )

    # Check login result
    login_successful = (
        administrator is not None and password_is_valid
    )

    # Record login attempt
    try:
        log_login_attempt(
            email,
            login_successful,
            "Login successful" if login_successful
            else "Invalid credentials"
        )
    except Exception:
        pass

    # Handle incorrect credentials
    if not login_successful:
        st.error("Email or password is incorrect.")
        return

    # Save login session
    st.session_state["authenticated"] = True
    st.session_state["admin_id"] = administrator["id"]
    st.session_state["admin_name"] = (
        administrator.get("name")
        or administrator.get("username")
        or email
    )
    st.session_state["admin_email"] = email
    st.session_state["school_id"] = administrator.get("school_id")

    st.rerun()
