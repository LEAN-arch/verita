import streamlit as st
import os
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Validate settings at module level
try:
    import settings
    if not hasattr(settings, 'AUTH') or not all(hasattr(settings.AUTH, attr) for attr in ['default_user', 'default_role', 'page_permissions', 'role_options']):
        logger.error("Required AUTH settings missing")
        raise ImportError("Invalid settings configuration")
except ImportError as e:
    logger.error(f"Settings import failed: {e}")
    raise

def initialize_auth_state() -> None:
    """Initialize session state for authentication."""
    with st.session_state:
        if 'auth_initialized' not in st.session_state:
            st.session_state.auth_initialized = True
            st.session_state.username = getattr(settings.AUTH, 'default_user', 'User')
            st.session_state.user_role = getattr(settings.AUTH, 'default_role', 'Guest')
            st.session_state.login_audited = False
            logger.debug(f"Initialized auth state: username={st.session_state.username}, role={st.session_state.user_role}")

def _check_page_authorization() -> None:
    """Check if the current user role is authorized to access the current page."""
    initialize_auth_state()  # Ensure state is initialized
    
    try:
        # Get current page information
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        current_page_hash = ctx.page_script_hash if ctx else ""
        # Note: Streamlit's page handling requires explicit page configuration
        # This assumes pages are defined in st.navigation or similar
        current_page_script_path = "VERITAS_Home.py"  # Fallback
        current_page_script_name = os.path.basename(current_page_script_path)
        
        # If you have a custom page registry, you can implement page lookup here
        # For example, if using st.navigation with Page objects
        pages = getattr(st, 'pages', {})
        for page_details in pages.values():
            if page_details.get("page_script_hash") == current_page_hash:
                current_page_script_path = page_details.get("page_script_path", current_page_script_path)
                break
        current_page_script_name = os.path.basename(current_page_script_path)
    except (AttributeError, KeyError, TypeError) as e:
        logger.warning(f"Page detection error: {e}")
        current_page_script_name = "VERITAS_Home.py"

    # Validate settings.AUTH
    if not hasattr(settings, 'AUTH') or not hasattr(settings.AUTH, 'page_permissions'):
        logger.error("Configuration error: AUTH settings not properly defined")
        st.error("Configuration error: AUTH settings not properly defined")
        st.stop()
    
    user_role = st.session_state.get('user_role', '')
    page_permissions: Dict[str, List[str]] = settings.AUTH.page_permissions
    
    # Map page names to permission keys
    permission_key = {
        "0_🏠_VERITAS_Home.py": "VERITAS_Home.py"
    }.get(current_page_script_name, current_page_script_name)
    
    authorized_roles = page_permissions.get(permission_key, [])
    if not authorized_roles or user_role not in authorized_roles:
        logger.warning(f"Access denied for user_role={user_role} on page={permission_key}")
        st.error("🔒 Access Denied")
        st.warning(f"Your assigned role ('{user_role}') does not have permission to view this page.")
        st.page_link("pages/0_🏠_VERITAS_Home.py", label="Return to Mission Control", icon="⬅️")
        st.stop()

def render_sidebar() -> None:
    """Render the sidebar with user information and role selection."""
    initialize_auth_state()  # Ensure state is initialized
    
    st.sidebar.title("VERITAS")
    st.sidebar.caption(getattr(settings, 'app', type('App', (), {'description': ''})).description)
    st.sidebar.markdown("---")
    st.sidebar.info(f"Welcome, **{st.session_state.get('username', 'User')}**")
    
    # Validate role options
    role_options: List[str] = getattr(settings.AUTH, 'role_options', ['default'])
    if not isinstance(role_options, list):
        logger.warning("role_options is not a list, using default")
        role_options = ['default']
    
    try:
        current_role_index = role_options.index(st.session_state.user_role)
    except ValueError:
        current_role_index = 0
        logger.warning(f"User role {st.session_state.user_role} not in role_options, defaulting to index 0")
    
    selected_role = st.sidebar.selectbox(
        "Switch Role View",
        options=role_options,
        index=current_role_index,
        help="Switch roles to see how dashboards and permissions change."
    )
    if selected_role != st.session_state.user_role:
        st.session_state.user_role = selected_role
        logger.debug(f"Role switched to {selected_role}")
        st.rerun()
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Reset Session / Logout", type="secondary"):
        logger.info("Session reset triggered")
        st.session_state.clear()
        st.rerun()

def display_compliance_footer() -> None:
    """Display the compliance footer with version and regulatory notice."""
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; font-size: 0.8em; color: grey; padding-top: 2em;">
        <p>VERITAS {getattr(settings.app, 'version', 'N/A')} | For Internal Vertex Use Only</p>
        <p><strong>GxP Compliance Notice:</strong> All actions are logged. Data integrity is enforced per <strong>21 CFR Part 11</strong>.</p>
    </div>
    """, unsafe_allow_html=True)

def render_common_elements() -> None:
    """Single function to render sidebar and check auth, called by bootstrap."""
    render_sidebar()
    _check_page_authorization()
