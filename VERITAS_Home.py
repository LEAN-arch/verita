# ==============================================================================
# VERITAS Home: The Intelligent Mission Control
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
#
# Description:
# This is the main entry point for the VERITAS application. It serves as a
# personalized, action-oriented landing page for all users. Its primary goals are:
#   1. Initialize the application state securely and robustly using the SessionManager.
#   2. Provide a personalized "Mission Briefing" with immediate action items.
#   3. Offer high-level, strategic KPIs with embedded SME explanations.
#   4. Enable quick navigation and data discovery via a global search.
#   5. Direct users to specialized modules in the `pages/` directory for deep dives.
# ==============================================================================

import streamlit as st
import pandas as pd

# Import the core backend components.
from veritas_core import session, auth
from veritas_core.engine import plotting

# --- 1. APPLICATION INITIALIZATION ---
# The SessionManager encapsulates all session state logic.
session_manager = session.SessionManager()
session_manager.initialize_app("VERITAS Mission Control", "🧪")

# --- 2. PERSONALIZED MISSION BRIEFING ---
st.subheader("Your Mission Briefing", divider='blue')
action_items = session_manager.get_user_action_items()

if not action_items:
    st.success("✅ Your action item queue is clear. Well done!")
else:
    st.warning(f"You have **{len(action_items)}** items requiring your attention.")
    for item in action_items:
        st.page_link(
            page=item['page_link'],
            label=f"**{item['title']}**: {item['details']}",
            icon=item['icon']
        )
st.markdown("---")

# --- 3. GLOBAL ENTITY SEARCH ---
st.sidebar.subheader("Global Search", divider='blue')
search_term = st.sidebar.text_input(
    "Search by Lot, Study, or Instrument ID",
    placeholder="e.g., A202301, VX-561-Tox-03...",
    key="global_search"
)
if search_term:
    search_results = session_manager.perform_global_search(search_term)
    if search_results:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Search Results:**")
        for result in search_results:
            st.sidebar.page_link(
                page=result['page_link'],
                label=f"Found in **{result['module']}**: {result['id']}",
                icon=result['icon']
            )
    else:
        st.sidebar.info(f"No results found for '{search_term}'.")

# --- 4. ROLE-BASED STRATEGIC DASHBOARD ---
user_role = st.session_state.user_role
st.header(f"'{user_role}' Command Center", anchor=False)

# --- DTE Leadership View: Strategic & Operational Health ---
if user_role == 'DTE Leadership':
    st.markdown("##### High-level overview of operational efficiency, program risk, and system health.")
    
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        active_devs = session_manager.get_kpi('active_deviations')
        st.metric("Active Deviations", active_devs['value'], help=active_devs['sme_info'])
    with kpi_cols[1]:
        dqs = session_manager.get_kpi('data_quality_score')
        st.metric("Data Quality Score (DQS)", f"{dqs['value']:.1f}%", f"{dqs['delta']:.1f}% vs Target", help=dqs['sme_info'])
    with kpi_cols[2]:
        fpy = session_manager.get_kpi('first_pass_yield')
        st.metric("First Pass Yield (FPY)", f"{fpy['value']:.1f}%", f"{fpy['delta']:.1f}%", help=fpy['sme_info'])
    with kpi_cols[3]:
        mttr = session_manager.get_kpi('mean_time_to_resolution')
        st.metric("Deviation MTTR (Days)", f"{mttr['value']:.1f}", f"{mttr['delta']:.1f} Days", delta_color="inverse", help=mttr['sme_info'])

    st.markdown("---")
    
    col1, col2 = st.columns((6, 4))
    with col1:
        st.subheader("Program Risk Matrix", divider='gray')
        risk_matrix_data = session_manager.get_risk_matrix_data()
        st.plotly_chart(plotting.plot_program_risk_matrix(risk_matrix_data), use_container_width=True)
    with col2:
        st.subheader("QC Failure Hotspots", divider='gray')
        pareto_data = session_manager.get_pareto_data()
        st.plotly_chart(plotting.plot_pareto_chart(pareto_data), use_container_width=True)

else:
    st.info("💡 **Welcome to VERITAS.** Your mission-critical tools are available in the sidebar. Your personalized **Mission Briefing** above will guide you to urgent tasks.")
    st.markdown("""
    This centralized platform is designed to accelerate our scientific mission by providing robust, automated, and compliant data solutions.
    - **QC & Integrity Center:** Perform deep-dive analysis and validate data quality.
    - **Process Capability:** Monitor historical process performance and stability.
    - **Stability Program:** Analyze stability trends and project shelf-life.
    - **Regulatory Support:** Compile and generate submission-ready reports.
    - **Deviation Hub:** Manage the lifecycle of all quality events.
    - **Governance & Audit:** Ensure compliance and trace data lineage.
    """)

# --- 5. COMPLIANCE FOOTER ---
auth.display_compliance_footer()
