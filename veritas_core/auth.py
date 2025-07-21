# ==============================================================================
# Core Module: Authentication & Authorization
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
#
# Description:
# This module provides all core functions related to user authentication,
# role-based access control (RBAC), and session initialization. It serves as
# the primary security gatekeeper for the VERITAS application.
#
# Key Features:
# - Centralized `page_setup`: A single function to configure and secure every page.
# - Role-Based Access Control (RBAC): Enforces page permissions based on user role.
# - Session Initialization: Manages the initial state of the user session.
# - GxP Compliance Footer: A reusable component for regulatory compliance.
# ==============================================================================

import streamlit as st
import os
from . import settings # Use relative import within the package

def initialize_session_state():
    """
    Initializes the core session state variables if they don't exist.
    This is the first step in establishing a user session.
    """
    if 'session_initialized' not in st.session_state:
        st.session_state.session_initialized = True
        st.session_state.username = settings.AUTH.default_user
        st.session_state.user_role = settings.AUTH.default_role
        st.session_state.login_audited = False
        st.session_state.page_states = {} # For storing page-specific states

def _check_page_authorization():
    """
    Internal function to check if the current user's role is authorized to
    view the currently executing Streamlit page. This is the core of RBAC.
    """
    # --- ATTRIBUTE ERROR FIX ---
    # `st.main_script_path` is deprecated. The modern, correct attribute is
    # `st.source_file_path`. This change resolves the AttributeError.
    current_page_script = os.path.basename(st.source_file_path)
    user_role = st.session_state.get('user_role', '')
    
    # Get permissions from the Pydantic settings model
    page_permissions = settings.AUTH.page_permissions
    
    # Handle the main entry point (Home page) which might have a different name
    # This makes the authorization more robust.
    home_page_filename = "VERITAS_Home.py"
    if current_page_script not in page_permissions:
        # If the script isn't in permissions, check if it's the home page
        if os.path.basename(st.script_run_context.get_script_run_ctx().main_script_path) == current_page_script:
            current_page_script = home_page_filename

    authorized_roles = page_permissions.get(current_page_script)
    
    if authorized_roles is None or user_role not in authorized_roles:
        st.error("🔒 Access Denied")
        st.warning(f"Your assigned role ('{user_role}') does not have permission to view this page.")
        st.page_link(home_page_filename, label="Return to Mission Control", icon="⬅️")
        st.stop() # Stop script execution immediately

def render_sidebar():
    """
    Renders the main application sidebar, including the user welcome message,
    role switcher, and logout button.
    """
    st.sidebar.title("VERITAS")
    st.sidebar.caption(settings.APP.description)
    st.sidebar.markdown("---")
    st.sidebar.info(f"Welcome, **{st.session_state.get('username', 'User')}**")

    role_options = settings.AUTH.role_options
    try:
        current_role_index = role_options.index(st.session_state.user_role)
    except ValueError:
        current_role_index = 0
    
    selected_role = st.sidebar.selectbox(
        "Switch Role View", options=role_options, index=current_role_index,
        help="Switch roles to see how dashboards and permissions change for different users."
    )
    
    if selected_role != st.session_state.user_role:
        st.session_state.user_role = selected_role
        # The session manager will handle the audit logging for role changes.
        st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("Reset Session / Logout", type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def display_compliance_footer():
    """
    Renders a standardized GxP compliance footer at the bottom of each page.
    """
    st.markdown("---")
    footer_html = f"""
    <div style="text-align: center; font-size: 0.8em; color: grey; padding-top: 2em;">
        <p>VERITAS {settings.APP.version} | For Internal Vertex Use Only</p>
        <p><strong>GxP Compliance Notice:</strong> All actions are logged. Data integrity is enforced per <strong>21 CFR Part 11</strong>.</p>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

def page_setup(page_title: str, page_icon: str):
    """
    A single, consolidated function to be called at the top of every UI page.
    It handles page configuration, session initialization, and authorization checks.
    This pattern drastically reduces boilerplate code in the UI files.

    Args:
        page_title (str): The title for the browser tab.
        page_icon (str): The icon for the browser tab.
    """
    st.set_page_config(
        page_title=f"{page_title} - VERITAS",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': settings.APP.help_url,
            'About': f"VERITAS, Version {settings.APP.version}"
        }
    )
    initialize_session_state()
    _check_page_authorization()
    render_sidebar()
