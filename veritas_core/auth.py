import streamlit as st
import os
from . import settings

def initialize_auth_state():
    if 'auth_initialized' not in st.session_state:
        st.session_state.auth_initialized = True
        st.session_state.username = settings.AUTH.default_user
        st.session_state.user_role = settings.AUTH.default_role
        st.session_state.login_audited = False

def _check_page_authorization():
    try:
        current_page_hash = st.get_page_script_hash()
        pages = st.get_pages("VERITAS_Home.py")
        current_page_script_path = "VERITAS_Home.py"
        for page_details in pages.values():
            if page_details["page_script_hash"] == current_page_hash:
                current_page_script_path = page_details["page_script_path"]
                break
        current_page_script_name = os.path.basename(current_page_script_path)
    except Exception:
        current_page_script_name = "VERITAS_Home.py"
    
    user_role = st.session_state.get('user_role', '')
    page_permissions = settings.AUTH.page_permissions
    
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
    st.sidebar.title("VERITAS")
    st.sidebar.caption(settings.app.description)
    st.sidebar.markdown("---")
    st.sidebar.info(f"Welcome, **{st.session_state.get('username', 'User')}**")
    role_options = settings.AUTH.role_options
    try: current_role_index = role_options.index(st.session_state.user_role)
    except ValueError: current_role_index = 0
    
    selected_role = st.sidebar.selectbox(
        "Switch Role View", options=role_options, index=current_role_index,
        help="Switch roles to see how dashboards and permissions change."
    )
    if selected_role != st.session_state.user_role:
        st.session_state.user_role = selected_role
        st.rerun()
    st.sidebar.markdown("---")
    if st.sidebar.button("Reset Session / Logout", type="secondary"):
        st.session_state.clear()
        st.rerun()

def display_compliance_footer():
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; font-size: 0.8em; color: grey; padding-top: 2em;">
        <p>VERITAS {settings.app.version} | For Internal Vertex Use Only</p>
        <p><strong>GxP Compliance Notice:</strong> All actions are logged. Data integrity is enforced per <strong>21 CFR Part 11</strong>.</p>
    </div>
    """, unsafe_allow_html=True)

def render_common_elements():
    """Single function to render sidebar and check auth, called by bootstrap."""
    render_sidebar()
    _check_page_authorization()
