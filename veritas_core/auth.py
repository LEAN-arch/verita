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
# ==============================================================================

import streamlit as st
import os
from . import settings # Use relative import within the package

def initialize_session_state():
    """
    Initializes the core session state variables if they don't exist.
    """
    if 'session_initialized' not in st.session_state:
        st.session_state.session_initialized = True
        st.session_state.username = settings.AUTH.default_user
        st.session_state.user_role = settings.AUTH.default_role
        st.session_state.login_audited = False
        st.session_state.page_states = {}

def _check_page_authorization():
    """
    Internal function to check if the current user's role is authorized to
    view the currently executing Streamlit page. This is the core of RBAC.
    """
    # --- DEFINITIVE ATTRIBUTE ERROR FIX ---
    # `st.main_script_path` and `st.source_file_path` are unreliable.
    # The robust, modern, and documented method is to use st.get_page_script_hash()
    # to identify the current page being executed.
    try:
        # Get the hash of the currently running page script
        current_page_hash = st.get_page_script_hash()
        # Get the dictionary of all pages in the app
        pages = st.get_pages("VERITAS_Home.py")
        
        # Find the script path that corresponds to the current hash
        current_page_script_path = ""
        for page_details in pages.values():
            if page_details["page_script_hash"] == current_page_hash:
                current_page_script_path = page_details["page_script_path"]
                break
        
        # If the hash isn't found, it means we are on the main page.
        if not current_page_script_path:
             current_page_script_path = "VERITAS_Home.py"
             
        # Extract the simple filename for the permissions dictionary
        current_page_script_name = os.path.basename(current_page_script_path)
            
    except Exception as e:
        # Failsafe in case the API has issues or changes. Default to the home page.
        st.warning(f"Could not determine current page for authorization check: {e}")
        current_page_script_name = "VERITAS_Home.py"

    user_role = st.session_state.get('user_role', '')
    
    # Get permissions from the Pydantic settings model
    page_permissions = settings.AUTH.page_permissions
    authorized_roles = page_permissions.get(current_page_script_name)
    
    if authorized_roles is None or user_role not in authorized_roles:
        st.error("🔒 Access Denied")
        st.warning(f"Your assigned role ('{user_role}') does not have permission to view this page.")
        st.page_link("VERITAS_Home.py", label="Return to Mission Control", icon="⬅️")
        st.stop()

def render_sidebar():
    """
    Renders the main application sidebar, including the user welcome message,
    role switcher, and logout button.
    """
    st.sidebar.title("VERITAS")
    st.sidebar.caption(settings.app.description)
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
        <p>VERITAS {settings.app.version} | For Internal Vertex Use Only</p>
        <p><strong>GxP Compliance Notice:</strong> All actions are logged. Data integrity is enforced per <strong>21 CFR Part 11</strong>.</p>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

def page_setup(page_title: str, page_icon: str):
    """
    A single, consolidated function to be called at the top of every UI page.
    It handles page configuration, session initialization, and authorization checks.
    """
    # This check is crucial for multipage apps. `st.set_page_config` can only be called once per script run.
    # The state variable ensures it's only called on the first execution.
    if 'page_config_set' not in st.session_state or st.session_state.page_config_set != page_title:
        st.set_page_config(
            page_title=f"{page_title} - VERITAS",
            page_icon=page_icon,
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': settings.app.help_url,
                'About': f"VERITAS, Version {settings.app.version}"
            }
        )
        st.session_state.page_config_set = page_title

    initialize_session_state()
    render_sidebar()
    _check_page_authorization()
