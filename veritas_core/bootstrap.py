import streamlit as st
from . import settings, repository, auth

def run(page_title: str, page_icon: str):
    """
    The definitive, fail-safe application bootstrap function.
    This is called at the TOP of every page script. It is idempotent and
    handles all core initialization and rendering tasks in the correct order.
    """
    # 1. Set Page Config (must be the first Streamlit command)
    # Use a session state flag to ensure it's only called once per page load.
    if st.session_state.get('page_config_set') != page_title:
        st.set_page_config(
            page_title=f"{page_title} - VERITAS", page_icon=page_icon, layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': settings.app.help_url,
                'About': f"VERITAS, Version {settings.app.version}"
            }
        )
        st.session_state.page_config_set = page_title

    # 2. Initialize Core Session State (only runs once per session)
    if 'veritas_initialized' not in st.session_state:
        st.session_state.settings = settings
        st.session_state.repo = repository.MockDataRepository()
        st.session_state.hplc_data = st.session_state.repo.get_hplc_data()
        st.session_state.deviations_data = st.session_state.repo.get_deviations_data()
        st.session_state.stability_data = st.session_state.repo.get_stability_data()
        st.session_state.audit_data = st.session_state.repo.get_audit_log()
        st.session_state.page_states = {}
        auth.initialize_auth_state()
        st.session_state.veritas_initialized = True
        print("VERITAS Session Initialized Successfully.")
    
    # 3. Render common UI elements and perform auth check for the current page
    auth.render_common_elements()
