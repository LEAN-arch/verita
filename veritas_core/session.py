
# ==============================================================================
# Session Management Module for VERITAS Application
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# Provides session management for the VERITAS application, including page
# initialization, session state management, and data access integration.
# Ensures GxP compliance with robust error handling and logging.
# ==============================================================================

import streamlit as st
import pandas as pd
import logging
from typing import Optional
from . import config, repository, auth

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionManager:
    """
    Session manager for the VERITAS application.

    Attributes:
        settings: Application configuration from config.AppConfig.
        _repo: Data repository instance for data access.

    Methods:
        initialize_page: Initialize a Streamlit page with title and icon.
        get_data: Retrieve data for a given data type.
        get_signatures_log: Retrieve electronic signature log.
    """
    def __init__(self):
        try:
            self.settings = config.AppConfig()
            self._repo = repository.MockDataRepository()
            logger.info("SessionManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SessionManager: {str(e)}")
            raise RuntimeError(f"SessionManager initialization failed: {str(e)}")

    @property
    def repo(self) -> 'repository.MockDataRepository':
        """
        Get the data repository instance.

        Returns:
            repository.MockDataRepository: The data repository instance.
        """
        return self._repo

    def initialize_page(self, page_title: str, page_icon: str) -> None:
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
            
            st.set_page_config(
                page_title=page_title,
                page_icon=page_icon,
                layout="wide",
                initial_sidebar_state="auto"
            )
            
            if 'username' not in st.session_state:
                st.session_state.username = None
            if 'initialized' not in st.session_state:
                st.session_state.initialized = True
                logger.info(f"Initialized Streamlit page: {page_title}")
        except Exception as e:
            logger.error(f"Failed to initialize page '{page_title}': {str(e)}")
            st.error(f"Failed to initialize page '{page_title}'. Please contact support.")
            raise RuntimeError(f"Page initialization failed: {str(e)}")

    def get_data(self, data_type: str) -> pd.DataFrame:
        """
        Retrieve data for the specified data type.

        Args:
            data_type (str): The type of data to retrieve (e.g., 'hplc', 'deviations', 'audit').

        Returns:
            pd.DataFrame: The requested data.

        Raises:
            ValueError: If data_type is invalid or data cannot be retrieved.
        """
        try:
            return self._repo.get_data(data_type)
        except Exception as e:
            logger.error(f"Failed to retrieve data for {data_type}: {str(e)}")
            raise ValueError(f"Data retrieval failed: {str(e)}")

    def get_signatures_log(self) -> pd.DataFrame:
        """
        Retrieve the electronic signature log.

        Returns:
            pd.DataFrame: The signature log with columns 'timestamp', 'user', 'action', 'record_id', 'details'.

        Raises:
            ValueError: If signature log cannot be retrieved.
        """
        try:
            # Placeholder: Simulate signature log retrieval
            sig_data = pd.DataFrame({
                'timestamp': [pd.Timestamp('2025-01-01 10:00:00'), pd.Timestamp('2025-01-02 12:00:00')],
                'user': ['user1', 'user2'],
                'action': ['sign', 'sign'],
                'record_id': ['REC1', 'REC2'],
                'details': ['Signed document A', 'Signed document B']
            })
            if sig_data.empty:
                return sig_data
            required_cols = ['timestamp', 'user', 'action', 'record_id', 'details']
            if not all(col in sig_data.columns for col in required_cols):
                raise ValueError("Signature log missing required columns")
            return sig_data
        except Exception as e:
            logger.error(f"Failed to retrieve signature log: {str(e)}")
            raise ValueError(f"Signature log retrieval failed: {str(e)}")
