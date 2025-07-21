# ==============================================================================
# VERITAS Application Launcher
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Ultimate Version)
#
# Description:
# This file serves as the primary entry point for the Streamlit application.
# Per modern Streamlit best practices for robust multi-page applications, this
# script's only role is to set the initial page configuration and then direct
# the user to the main home page located in the `pages/` directory.
#
# How to run: `streamlit run VERITAS_Home.py`
# ==============================================================================

import streamlit as st

# Set a basic, wide-layout page config for the initial load.
# The actual page configs will be set within each page file.
st.set_page_config(
    page_title="VERITAS",
    page_icon="🧪",
    layout="wide"
)

# Provide a clean loading experience and an explicit link to the main application page.
st.title("Welcome to the VERITAS Platform")
st.info("Initializing application... Please navigate using the sidebar or the link below.")
st.page_link("pages/0_🏠_VERITAS_Home.py", label="Go to Mission Control", icon="🚀")

# This is a useful technique to hide the default "VERITAS_Home" page from the sidebar,
# making the user experience cleaner as they will only see the numbered pages.
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] li:nth-child(1) {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)
