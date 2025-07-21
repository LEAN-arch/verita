import streamlit as st
import os
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Validate imports at module level
try:
    import settings
    import repository
    import auth
    if not all(hasattr(settings, 'app') and hasattr(settings.app, attr) for attr in ['help_url', 'version']):
        logger.error("Required settings.app attributes missing")
        raise ImportError("Invalid settings configuration")
    if not hasattr(repository, 'MockDataRepository'):
        logger.error("MockDataRepository not found in repository module")
        raise ImportError("Invalid repository configuration")
    if not all(hasattr(auth, func) for func in ['initialize_auth_state', 'render_common_elements']):
        logger.error("Required auth functions missing")
        raise ImportError("Invalid auth configuration")
except ImportError as e:
    logger.error(f"Module importation failed: {e}")
    raise

def run(page_title: str, page_icon: str) -> None:
    """
    The definitive, fail-safe application bootstrap function.
    This is called at the TOP of every page script. It is idempotent and
    handles all core initialization and rendering tasks in the correct order.

    Args:
        page_title (str): The title of the page.
        page_icon (str): The icon for the page.
    """
    # 1. Set Page Config (must be the first Streamlit command)
    with st.session_state:
        if 'page_config_set' not in st.session_state:
            try:
                st.set_page_config(
                    page_title=f"{page_title} - VERITAS",
                    page_icon=page_icon,
                    layout="wide",
                    initial_sidebar_state="expanded",
                    menu_items={
                        'Get Help': getattr(settings.app, 'help_url', 'https://example.com/help'),
                        'About': f"VERITAS, Version {getattr(settings.app, 'version', 'N/A')}"
                    }
                )
                st.session_state.page_config_set = True
                logger.debug(f"Page config set: title={page_title}, icon={page_icon}")
            except RuntimeError as e:
                logger.warning(f"Page config already set or invalid: {e}")
        else:
            logger.debug("Page config already set, skipping")

    # 2. Initialize Core Session State (only runs once per session)
    with st.session_state:
        if 'veritas_initialized' not in st.session_state:
            try:
                st.session_state.settings = settings
                # Only create repository if not already initialized
                if 'repo' not in st.session_state:
                    st.session_state.repo = repository.MockDataRepository()
                    logger.debug("MockDataRepository initialized")
                
                # Initialize data with error handling
                try:
                    st.session_state.hplc_data = st.session_state.repo.get_hplc_data()
                except Exception as e:
                    logger.error(f"Failed to load HPLC data: {e}")
                    st.session_state.hplc_data = None
                
                try:
                    st.session_state.deviations_data = st.session_state.repo.get_deviations_data()
                except Exception as e:
                    logger.error(f"Failed to load deviations data: {e}")
                    st.session_state.deviations_data = None
                
                try:
                    st.session_state.stability_data = st.session_state.repo.get_stability_data()
                except Exception as e:
                    logger.error(f"Failed to load stability data: {e}")
                    st.session_state.stability_data = None
                
                try:
                    st.session_state.audit_data = st.session_state.repo.get_audit_log()
                except Exception as e:
                    logger.error(f"Failed to load audit data: {e}")
                    st.session_state.audit_data = None
                
                st.session_state.page_states = {}  # Kept for compatibility, purpose unclear
                auth.initialize_auth_state()
                st.session_state.veritas_initialized = True
                logger.info("VERITAS Session Initialized Successfully")
            except Exception as e:
                logger.error(f"Session initialization failed: {e}")
                st.error("Failed to initialize application session")
                st.stop()

    # 3. Render common UI elements and perform auth check for the current page
    try:
        auth.render_common_elements()
        logger.debug("Common elements rendered and auth checked")
    except Exception as e:
        logger.error(f"Failed to render common elements or check auth: {e}")
        st.error("Error rendering application elements")
        st.stop()
