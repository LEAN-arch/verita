# ==============================================================================
# Core Module: Authentication & Authorization (Ultimate Version)
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
#
# Description:
# This module provides all core functions related to user authentication,
# role-based access control (RBAC), and UI components like the sidebar and
# compliance footer. It works in concert with the SessionManager for a robust
# and secure user experience.
# ==============================================================================

import streamlit as st
import os
from . import settings # Use relative import within the package

def initialize_auth_state():
    """
    Initializes only the authentication-related parts of the session state.
    This is called once by the main `initialize_session` function.
    """
    if 'auth_initialized' not in st.session_state:
        st.session_state.auth_initialized = True
        st.session_state.username = settings.AUTH.default_user
        st.session_state.user_role = settings.AUTH.default_role
        st.session_state.login_audited = False

def _check_page_authorization():
    """
    Internal function to check if the current user's role is authorized to
    view the currently executing Streamlit page. This is the core of RBAC.
    """
    # --- DEFINITIVE ATTRIBUTE ERROR FIX ---
    # This robust method uses the official, documented Streamlit API to get
    # the current page script path, resolving all previous AttributeError issues.
    try:
        current_page_hash = st.get_page_script_hash()
        # The main script path for st.get_pages should point to the *actual* home page file
        pages = st.get_pages("pages/0_🏠_VERITAS_Home.py")
        
        current_page_script_path = "pages/0_🏠_VERITAS_Home.py" # Default to home
        for page_details in pages.values():
            if page_details["page_script_hash"] == current_page_hash:
                current_page_script_path = page_details["page_script_path"]
                break
        current_page_script_name = os.path.basename(current_page_script_path)
    except Exception:
        # Failsafe in case the API has issues.
        current_page_script_name = "0_🏠_VERITAS_Home.py"
        
    user_role = st.session_state.get('user_role', '')
    page_permissions = settings.AUTH.page_permissions
    
    # Map the new, numbered home page filename to the key used in the permissions dictionary
    permission_key = {
        "0_🏠_VERITAS_Home.py": "VERITAS_Home.py"
    }.get(current_page_script_name, current_page_script_name)
    
    authorized_roles = page_permissions.get(permission_key)
    
    if authorized_roles is None or user_role not in authorized_roles:
        st.error("🔒 Access Denied")
        st.warning(f"Your assigned role ('{user_role}') does not have permission to view this page.")
        st.page_link("pages/0_🏠_VERITAS_Home.py", label="Return to Mission Control", icon="⬅️")
        st.stop()

def render_sidebar():
    """
    Renders the main application sidebar, including the user welcome message,
    role switcher, and logout button.
    """
    st.sidebar.title("VERITAS")
    st.sidebar.caption(settings.app.description)
    st.sidebar.markdown("---")
    
    # Global search is now part of the home page, keeping the sidebar cleaner.
    
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
        # Log the role change action
        st.session_state.repo.write_audit_log(
            user=st.session_state.username,
            action="Role View Changed",
            details=f"Switched to '{selected_role}' view."
        )
        st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("Reset Session / Logout", type="secondary"):
        st.session_state.clear()
        st.rerun()

def display_compliance_footer():
    """
    Renders a standardized GxP compliance footer at the bottom of each page.
    """
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; font-size: 0.8em; color: grey; padding-top: 2em;">
        <p>VERITAS {settings.app.version} | For Internal Vertex Use Only</p>
        <p><strong>GxP Compliance Notice:</strong> All actions are logged. Data integrity is enforced per <strong>21 CFR Part 11</strong>.</p>
    </div>
    """, unsafe_allow_html=True)

def page_setup(page_title: str, page_icon: str):
    """
    A single, consolidated function to be called at the top of every UI page.
    It handles page configuration and authorization checks.
    """
    st.set_page_config(
        page_title=f"{page_title} - VERITAS",
        page_icon=page_icon,
        layout="wide"
    )
    # Sidebar is now rendered by the home page to ensure it exists before page navigation.
    # We just need to check authorization here.
    _check_page_authorization()
