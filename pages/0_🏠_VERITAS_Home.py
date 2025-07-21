
# ==============================================================================
# VERITAS Home: The Intelligent Mission Control
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This is the main entry point for the VERITAS application's home page, providing
# a personalized, action-oriented landing page for all users. It displays user-specific
# action items, key performance indicators (KPIs) for leadership roles, and visualizations
# such as risk matrices and Pareto charts. The page integrates with the veritas_core
# modules (bootstrap, session, auth, plotting) and is designed for GxP compliance.
# ==============================================================================

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict, Any
from veritas_core import bootstrap, session, auth
from veritas_core.engine import plotting

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Render the VERITAS Mission Control home page.

    Displays user-specific action items, KPIs for leadership roles, and visualizations
    using Streamlit. Integrates with veritas_core modules for session management,
    authentication, and plotting.

    Raises:
        RuntimeError: If session initialization or data retrieval fails.
        ValueError: If session state or data structures are invalid.
    """
    # --- 1. Application Bootstrap ---
    try:
        bootstrap.run("VERITAS Mission Control", "🏠")
        if 'user_role' not in st.session_state or not isinstance(st.session_state.user_role, str) or not st.session_state.user_role.strip():
            raise ValueError("user_role not set or invalid in session state")
    except Exception as e:
        logger.error(f"Bootstrap failed: {str(e)}")
        st.error("Failed to initialize VERITAS Mission Control. Please contact support.")
        raise RuntimeError(f"Bootstrap failed: {str(e)}")

    # --- 2. Session Manager Access ---
    try:
        session_manager = session.SessionManager()
    except Exception as e:
        logger.error(f"SessionManager initialization failed: {str(e)}")
        st.error("Failed to initialize session. Please contact support.")
        raise RuntimeError(f"SessionManager initialization failed: {str(e)}")

    # --- 3. Page Content ---
    st.title("🏠 VERITAS Mission Control")

    # Action Items Section
    st.subheader("Your Mission Briefing", divider='blue')
    try:
        action_items = session_manager.get_user_action_items()
        if not isinstance(action_items, list):
            raise ValueError("get_user_action_items must return a list")
        required_keys = ['page_link', 'title', 'details', 'icon']
        if action_items and not all(isinstance(item, dict) and all(key in item for key in required_keys) for item in action_items):
            raise ValueError("Action items must be a list of dictionaries with keys: page_link, title, details, icon")

        if not action_items:
            st.success("✅ Your action item queue is clear. Well done!")
        else:
            st.warning(f"You have **{len(action_items)}** items requiring your attention.")
            for item in action_items:
                try:
                    st.page_link(page=item['page_link'], label=f"**{item['title']}**: {item['details']}", icon=item['icon'])
                except Exception as e:
                    logger.warning(f"Failed to render action item {item.get('title', 'unknown')}: {str(e)}")
                    st.warning(f"Failed to display action item: {item.get('title', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to load action items: {str(e)}")
        st.error("Failed to load action items. Please try again later.")

    st.markdown("---")

    # Command Center Section
    user_role = st.session_state.user_role
    st.header(f"'{user_role}' Command Center", anchor=False)
    if user_role == 'DTE Leadership':
        try:
            # KPI Metrics
            kpi_cols = st.columns(4)
            kpis = {
                'active_deviations': {'label': "Active Deviations", 'delta': None, 'delta_color': "normal"},
                'data_quality_score': {'label': "Data Quality Score (DQS)", 'format': "{:.1f}%", 'delta_format': "{:.1f}% vs Target", 'delta_color': "normal"},
                'first_pass_yield': {'label': "First Pass Yield (FPY)", 'format': "{:.1f}%", 'delta_format': "{:.1f}%", 'delta_color': "normal"},
                'mean_time_to_resolution': {'label': "Deviation MTTR (Days)", 'format': "{:.1f}", 'delta_format': "{:.1f} Days", 'delta_color': "inverse"}
            }
            for idx, (kpi_key, kpi_info) in enumerate(kpis.items()):
                with kpi_cols[idx]:
                    try:
                        kpi_data = session_manager.get_kpi(kpi_key)
                        if not isinstance(kpi_data, dict) or not all(key in kpi_data for key in ['value', 'delta', 'sme_info']):
                            raise ValueError(f"Invalid KPI data for {kpi_key}")
                        st.metric(
                            label=kpi_info['label'],
                            value=kpi_info.get('format', "{}").format(kpi_data['value']),
                            delta=kpi_info.get('delta_format', "{}").format(kpi_data['delta']) if kpi_data['delta'] is not None else None,
                            delta_color=kpi_info.get('delta_color', "normal"),
                            help=kpi_data['sme_info']
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load KPI {kpi_key}: {str(e)}")
                        st.metric(kpi_info['label'], "N/A", help=f"Failed to load: {str(e)}")

            st.markdown("---")

            # Visualizations
            col1, col2 = st.columns((6, 4))
            with col1:
                st.subheader("Program Risk Matrix", divider='gray')
                try:
                    risk_matrix_data = session_manager.get_risk_matrix_data()
                    if not isinstance(risk_matrix_data, pd.DataFrame):
                        raise ValueError("get_risk_matrix_data must return a pandas DataFrame")
                    required_cols = ['program_id', 'days_to_milestone', 'dqs', 'active_deviations', 'risk_quadrant']
                    if not all(col in risk_matrix_data.columns for col in required_cols):
                        raise ValueError(f"Risk matrix data must contain columns: {required_cols}")
                    st.plotly_chart(plotting.plot_program_risk_matrix(risk_matrix_data), use_container_width=True)
                except Exception as e:
                    logger.error(f"Failed to render risk matrix: {str(e)}")
                    st.error("Failed to display Program Risk Matrix. Please try again later.")

            with col2:
                st.subheader("QC Failure Hotspots", divider='gray')
                try:
                    pareto_data = session_manager.get_pareto_data()
                    if not isinstance(pareto_data, pd.DataFrame):
                        raise ValueError("get_pareto_data must return a pandas DataFrame")
                    required_cols = ['Error Type', 'Frequency']
                    if not all(col in pareto_data.columns for col in required_cols):
                        raise ValueError(f"Pareto data must contain columns: {required_cols}")
                    st.plotly_chart(plotting.plot_pareto_chart(pareto_data), use_container_width=True)
                except Exception as e:
                    logger.error(f"Failed to render Pareto chart: {str(e)}")
                    st.error("Failed to display QC Failure Hotspots. Please try again later.")
        except Exception as e:
            logger.error(f"Failed to render leadership dashboard: {str(e)}")
            st.error("Failed to load leadership dashboard. Please contact support.")
    else:
        st.info("💡 **Welcome to VERITAS.** Your mission-critical tools are available in the sidebar.")

    # Compliance Footer
    try:
        auth.display_compliance_footer()
    except Exception as e:
        logger.error(f"Failed to render compliance footer: {str(e)}")
        st.warning("Failed to display compliance footer.")

if __name__ == "__main__":
    main()

