# ==============================================================================
# VERITAS: The Intelligent Mission Control
#
# Author: Principal Engineer SME
# Refactored By: AI Engineering Assistant
# Last Updated: 2025-07-21
#
# Description:
# This is the main entry point for the VERITAS platform. It handles user
# authentication, session initialization, and renders the main "Mission Control"
# home page. The page is dynamic, showing action items for all users and a
# detailed command center for leadership roles.
#
# REFECTOR NOTES:
# - Consolidated the initial landing page and the home page into this single app.py.
# - Implemented caching for performance: @st.cache_resource for the SessionManager
#   and @st.cache_data for all data-fetching functions.
# - Refactored the monolithic `main` function into smaller, modular functions
#   (e.g., render_mission_briefing, render_command_center) for clarity.
# - Addressed the N+1 query problem by assuming a bulk KPI fetch method.
# - Improved error handling patterns and overall readability.
# ==============================================================================

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict

# Assuming veritas_core is in the python path
# In a real project, this would be managed by a setup.py or requirements.txt
from veritas_core import bootstrap, session, auth
from veritas_core.engine import plotting

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Cached Helper Functions for Performance ---

@st.cache_resource
def get_session_manager() -> session.SessionManager:
    """
    Initializes and returns a singleton SessionManager instance.
    `@st.cache_resource` ensures this object is created only once per session.
    """
    logger.info("Initializing SessionManager...")
    try:
        return session.SessionManager()
    except Exception as e:
        logger.critical(f"Fatal error initializing SessionManager: {e}", exc_info=True)
        # Use st.exception to show the full error in the app during development
        st.exception(e)
        st.stop() # Stop the script if session cannot be established

@st.cache_data
def get_action_items(user_id: str) -> List[Dict]:
    """
    Fetches and caches user-specific action items.
    `@st.cache_data` caches the return value. The cache is invalidated if `user_id` changes.
    """
    logger.info(f"Fetching action items for user: {user_id}")
    action_items = get_session_manager().get_user_action_items()
    
    # --- Data Validation ---
    if not isinstance(action_items, list):
        raise ValueError("get_user_action_items must return a list")
    required_keys = ['page_link', 'title', 'details', 'icon']
    if action_items and not all(isinstance(item, dict) and all(key in item for key in required_keys) for item in action_items):
        raise ValueError("Action items must be a list of dictionaries with required keys: page_link, title, details, icon")
    
    return action_items

@st.cache_data
def get_leadership_kpis() -> Dict[str, Dict]:
    """
    Fetches all leadership KPIs in a single batch call to avoid the N+1 problem.
    Caches the entire dictionary of KPIs.
    """
    logger.info("Fetching all leadership KPIs...")
    # REFACTOR: Assumes a new method `get_all_kpis()` exists in SessionManager for efficiency.
    # The old approach made one call per KPI inside a loop.
    kpis = get_session_manager().get_all_kpis()

    # --- Data Validation ---
    if not isinstance(kpis, dict):
        raise ValueError("get_all_kpis must return a dictionary.")
    # Example check for one KPI's structure
    if 'active_deviations' in kpis:
        if not isinstance(kpis['active_deviations'], dict) or not all(key in kpis['active_deviations'] for key in ['value', 'delta', 'sme_info']):
            raise ValueError("Invalid KPI data structure received.")

    return kpis

@st.cache_data
def get_risk_data() -> pd.DataFrame:
    """Fetches and caches the program risk matrix data."""
    logger.info("Fetching risk matrix data...")
    risk_df = get_session_manager().get_risk_matrix_data()

    # --- Data Validation ---
    if not isinstance(risk_df, pd.DataFrame):
        raise ValueError("get_risk_matrix_data must return a pandas DataFrame")
    required_cols = ['program_id', 'days_to_milestone', 'dqs', 'active_deviations', 'risk_quadrant']
    if not all(col in risk_df.columns for col in required_cols):
        raise ValueError(f"Risk matrix data must contain columns: {required_cols}")
        
    return risk_df

@st.cache_data
def get_failure_data() -> pd.DataFrame:
    """Fetches and caches the QC failure pareto chart data."""
    logger.info("Fetching Pareto data for QC failures...")
    pareto_df = get_session_manager().get_pareto_data()

    # --- Data Validation ---
    if not isinstance(pareto_df, pd.DataFrame):
        raise ValueError("get_pareto_data must return a pandas DataFrame")
    required_cols = ['Error Type', 'Frequency']
    if not all(col in pareto_df.columns for col in required_cols):
        raise ValueError(f"Pareto data must contain columns: {required_cols}")

    return pareto_df


# --- UI Rendering Functions ---

def render_mission_briefing(user_id: str) -> None:
    """Renders the user's action items section."""
    st.subheader("Your Mission Briefing", divider='blue')
    try:
        action_items = get_action_items(user_id)
        if not action_items:
            st.success("✅ Your action item queue is clear. Well done!")
        else:
            st.warning(f"You have **{len(action_items)}** items requiring your attention.")
            for item in action_items:
                # REFACTOR: Catching specific exceptions is better, but this is safe.
                try:
                    st.page_link(page=item['page_link'], label=f"**{item['title']}**: {item['details']}", icon=item['icon'])
                except Exception as e:
                    logger.warning(f"Failed to render action item '{item.get('title')}': {e}")
                    st.warning(f"Could not display action item: {item.get('title', 'Unknown')}")
    except Exception as e:
        logger.error(f"Failed to load action items: {e}", exc_info=True)
        st.error("Could not load your action items. Data may be temporarily unavailable.")

def render_command_center() -> None:
    """Renders the leadership-specific dashboard with KPIs and charts."""
    user_role = st.session_state.get('user_role', 'Guest')
    st.header(f"{user_role} Command Center", anchor=False)

    if user_role != 'DTE Leadership':
        st.info("💡 Welcome to VERITAS. Your mission-critical tools are available in the sidebar.")
        return

    # --- KPI Metrics ---
    # REFACTOR: This now uses a single, efficient data fetch.
    try:
        all_kpis = get_leadership_kpis()
        kpi_cols = st.columns(4)
        kpi_configs = {
            'active_deviations': {'label': "Active Deviations", 'col': kpi_cols[0]},
            'data_quality_score': {'label': "Data Quality Score (DQS)", 'col': kpi_cols[1], 'format': "{:.1f}%"},
            'first_pass_yield': {'label': "First Pass Yield (FPY)", 'col': kpi_cols[2], 'format': "{:.1f}%"},
            'mean_time_to_resolution': {'label': "Deviation MTTR (Days)", 'col': kpi_cols[3], 'format': "{:.1f}", 'delta_color': "inverse"}
        }

        for key, config in kpi_configs.items():
            with config['col']:
                if key in all_kpis:
                    kpi_data = all_kpis[key]
                    st.metric(
                        label=config['label'],
                        value=config.get('format', "{}").format(kpi_data['value']),
                        delta=f"{kpi_data['delta']:.1f}" if kpi_data.get('delta') is not None else None,
                        delta_color=config.get('delta_color', "normal"),
                        help=kpi_data.get('sme_info', 'No further details.')
                    )
                else:
                    st.metric(config['label'], "N/A", help=f"KPI '{key}' not available.")
    except Exception as e:
        logger.error(f"Failed to render KPIs: {e}", exc_info=True)
        st.error("Could not load key performance indicators.")

    st.markdown("---")

    # --- Visualizations ---
    col1, col2 = st.columns((6, 4))
    with col1:
        st.subheader("Program Risk Matrix", divider='gray')
        try:
            risk_df = get_risk_data()
            st.plotly_chart(plotting.plot_program_risk_matrix(risk_df), use_container_width=True)
        except Exception as e:
            logger.error(f"Failed to render risk matrix: {e}", exc_info=True)
            st.error("Failed to display Program Risk Matrix.")

    with col2:
        st.subheader("QC Failure Hotspots", divider='gray')
        try:
            pareto_df = get_failure_data()
            st.plotly_chart(plotting.plot_pareto_chart(pareto_df), use_container_width=True)
        except Exception as e:
            logger.error(f"Failed to render Pareto chart: {e}", exc_info=True)
            st.error("Failed to display QC Failure Hotspots.")

# --- Main Application Logic ---

def main() -> None:
    """
    Main function to run the VERITAS application.
    It handles bootstrap, authentication checks, and renders the appropriate view.
    """
    # --- 1. Application Bootstrap & Page Config ---
    # REFACTOR: This replaces the separate landing page file.
    st.set_page_config(page_title="VERITAS", page_icon="🧪", layout="wide")

    try:
        # The bootstrap function should handle authentication and populate session_state
        # It should return True on success and False on failure
        is_authenticated = bootstrap.run()
    except Exception as e:
        logger.critical(f"The bootstrap.run() function failed critically: {e}", exc_info=True)
        st.title("Welcome to VERITAS")
        st.error("A critical error occurred during application startup. Please contact support.")
        st.exception(e) # Show developers the error
        return # Stop execution

    # --- 2. Render Page based on Authentication Status ---
    if not is_authenticated or 'user_id' not in st.session_state:
        # Unauthenticated or Guest View
        st.title("Welcome to the VERITAS Platform")
        st.info("Please log in to access Mission Control.")
        # In a real app, you would have an st.form for username/password
        # or a button that redirects to an SSO provider.
        if st.button("Log In", type="primary"):
            # This is a placeholder for actual login logic.
            # In a real app, clicking this would trigger the login flow and a script rerun.
            st.rerun()
    else:
        # Authenticated View
        st.title("🏠 VERITAS Mission Control")
        
        # Pass the user_id to functions that need it for caching
        render_mission_briefing(user_id=st.session_state.user_id)
        
        st.markdown("---")
        
        render_command_center()

    # --- 3. Compliance Footer (runs for all users) ---
    try:
        auth.display_compliance_footer()
    except Exception as e:
        logger.error(f"Failed to render compliance footer: {e}")
        # This is a non-critical failure, so just log a warning.
        st.warning("Compliance information could not be displayed.")


if __name__ == "__main__":
    main()
