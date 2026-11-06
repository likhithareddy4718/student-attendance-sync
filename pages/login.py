
import streamlit as st


def show_login_page():
    """
    Display the login page for school administrators.
    Returns the email and password entered by the user, or None if not submitted.
    """

    st.set_page_config(
        page_title="Administrator Log In",
        layout="centered"
    )

    # Custom page design
    st.markdown("""
        <style>

        /* Page background */
        .stApp {
            background-color: #f4f7fc;
        }

        /* Center the login container */
        .block-container {
            max-width: 650px;
            padding-top: 4rem;
            padding-bottom: 3rem;
            margin: auto;
        }

        /* Login heading */
        .stApp h1,
        .stApp [data-testid="stHeading"] h1 {
            color: #1e293b !important;
            text-align: center !important;
            font-size: 42px !important;
            font-weight: 700 !important;
            margin-bottom: 30px !important;
        }

        /* Login form card */
        div[data-testid="stForm"] {
            background-color: #ffffff !important;
            padding: 30px !important;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.06);
        }

        /* Input labels */
        div[data-testid="stTextInput"] label {
            color: #1e293b !important;
            font-weight: 600 !important;
        }

        /* Input fields */
        div[data-testid="stTextInput"] input {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 7px !important;
            min-height: 45px;
        }

        /* Placeholder text */
        div[data-testid="stTextInput"] input::placeholder {
            color: #94a3b8 !important;
            opacity: 1 !important;
        }

        /* Full-width Login button */
        div[data-testid="stFormSubmitButton"] {
            width: 100% !important;
        }

        div[data-testid="stFormSubmitButton"] button {
            width: 100% !important;
            min-height: 45px !important;
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 7px !important;
            font-size: 16px !important;
            font-weight: 600 !important;
        }

        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #1d4ed8 !important;
            color: #ffffff !important;
        }

        /* Forgot password link */
        .stApp a {
            color: #2563eb !important;
            font-weight: 500;
        }

        </style>
    """, unsafe_allow_html=True)

    # Page heading
    st.title("Log In")

    # Login form
    with st.form("login_form"):

        # Email field
        email = st.text_input(
            label="Email",
            placeholder="Enter your email address"
        )

        # Password field
        password = st.text_input(
            label="Password",
            type="password",
            placeholder="Enter your password"
        )

        # Full-width Login button
        submitted = st.form_submit_button(
            "Login",
            use_container_width=True
        )

    # Forgot password link
    st.markdown("[Forgot password?](#)")

    # Return credentials
    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
            return None

        return {
            "email": email,
            "password": password
        }

    return None


# Test the login page
if __name__ == "__main__":

    credentials = show_login_page()

    if credentials:
        st.write(f"Email entered: {credentials['email']}")
        st.write("Password received (not shown for security)")
