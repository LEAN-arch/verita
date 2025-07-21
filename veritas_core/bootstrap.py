
# ==============================================================================
# Bootstrap Module for VERITAS Application
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# Initializes the Streamlit application and session state for VERITAS pages.
# Ensures proper setup of page configuration and session management with robust
# error handling and logging.
# ==============================================================================

import streamlit as st
import logging
from typing import Any
from . import config, repository, auth

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run(page_title: str, page_icon: str) -> None:
    """
    Initialize a Streamlit page with the given title and icon.

    Args:
        page_title (str): The title of the page.
        page_icon (str): The icon for the page (emoji or image path).

    Raises:
        ValueError: If page_title or page_icon is invalid.
        RuntimeError: If page initialization fails.
    """
    try:
        if not isinstance(page_title, str) or not page_title.strip():
            raise ValueError("page_title must be a non-empty string")
        if not isinstance(page_icon, str) or not page_icon.strip():
            raise ValueError("page_icon must be a non-empty string")
        
        # Set Streamlit page configuration
        st.set_page_config(
            page_title=page_title,
            page_icon=page_icon,
            layout="wide",
            initial_sidebar_state="auto"
        )
        
        # Initialize session state
        if 'username' not in st.session_state:
            st.session_state.username = None  # Placeholder; set via auth.login
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            logger.info(f"Initialized Streamlit page: {page_title}")
        
        # Validate configuration and repository
        if not hasattr(config, 'app'):
            raise ValueError("config.app not found")
        if not hasattr(repository, 'get_data'):
            raise ValueError("repository.get_data not found")
        
    except Exception as e:
        logger.error(f"Failed to initialize page '{page_title}': {str(e)}")
        st.error(f"Failed to initialize page '{page_title}'. Please contact support.")
        raise RuntimeError(f"Page initialization failed: {str(e)}")
