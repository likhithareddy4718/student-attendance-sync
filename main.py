import streamlit as st
from routes.auth_routes import handle_login

st.set_page_config(
    page_title="Student Attendance Sync Platform",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide automatic pages navigation
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

handle_login()