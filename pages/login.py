
import streamlit as st


def show_login_page():
    """Display the login page for school administrators.
    Returns the email and password entered by the user, or None if not submitted.
    """

    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #eef2ff, #e0f7fa, #f3e8ff);
        }

        .block-container {
            max-width: 560px;
            padding-top: 2rem;
        }

        .brand {
            text-align: center;
            font-size: 30px;
            font-weight: 800;
            color: #4338ca;
        }

        .subtitle {
            text-align: center;
            color: #64748b;
            margin-bottom: 25px;
        }

        .login-heading {
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            color: #1e293b;
        }

        div[data-testid="stFormSubmitButton"] button {
            background: linear-gradient(90deg, #4f46e5, #7c3aed);
            color: white;
            border-radius: 10px;
            width: 100%;
            height: 45px;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="brand">🎓 AttendSync</div>'
        '<div class="subtitle">Student Attendance Sync Platform</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):

        st.markdown(
            '<div class="login-heading">Welcome Back!</div>',
            unsafe_allow_html=True,
        )

        st.caption("Sign in to your administrator account")

        with st.form("login_form", clear_on_submit=False):

            email = st.text_input(
                "Email Address",
                placeholder="admin@school.com",
                key="login_email",
                disabled=False,
            )

            password = st.text_input(
                "Password",
                placeholder="Enter your password",
                type="password",
                key="login_password",
                disabled=False,
            )

            submitted = st.form_submit_button(
                "Login →",
                use_container_width=True,
            )

        if submitted:
            if not email.strip() or not password:
                st.error("Please enter both email and password.")
                return None

            return {
                "email": email.strip(),
                "password": password,
            }

        if st.button("Forgot password?", key="forgot_password"):
            st.info("Password reset functionality will be added here.")

    st.markdown(
        """
        <div style="text-align:center;color:#94a3b8;
                    margin-top:25px;font-size:12px;">
            Secure access for school administrators
        </div>
        """,
        unsafe_allow_html=True,
    )

    return None
