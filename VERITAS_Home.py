import streamlit as st

st.set_page_config(
    page_title="VERITAS",
    page_icon="🧪",
    layout="wide"
)

st.title("Welcome to the VERITAS Platform")
st.info("Initializing application... Please navigate using the sidebar or the link below.")
st.page_link("pages/0_🏠_VERITAS_Home.py", label="Go to Mission Control", icon="🚀")

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] li:nth-child(1) {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)
