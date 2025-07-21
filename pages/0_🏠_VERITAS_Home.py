# ==============================================================================
# VERITAS Home: The Intelligent Mission Control
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Ultimate Version)
#
# Description:
# This is the true home page for the VERITAS application. It serves as a
# personalized, action-oriented landing page for all users.
#
# Key Features:
# - Fail-Safe Initialization: This is the ONLY place where the full session
#   state is initialized, eliminating all previous race conditions and errors.
# - Personalized "Mission Briefing": An actionable task list for each user.
# - Strategic "Program Risk Matrix": A high-level visualization for leadership.
# - KPIs with Embedded SME Explanations: Deep, contextual information on hover.
# ==============================================================================

import streamlit as st
import pandas as pd
from veritas_core import session, auth
from veritas_core.engine import plotting

# --- 1. APPLICATION INITIALIZATION ---
# This is the single, definitive entry point for initializing the entire app state.
# This robust, idempotent function resolves all previously seen race conditions.
session.initialize_session() 
session_manager = session.SessionManager()

# --- 2. PAGE SETUP (must come after initialization) ---
# This call handles page config, authentication, and sidebar rendering.
auth.page_setup("VERITAS Mission Control", "🏠")

# --- 3. PERSONALIZED MISSION BRIEFING ---
st.subheader("Your Mission Briefing", divider='blue')
st.markdown("A prioritized list of tasks and alerts requiring your immediate attention.")
action_items = session_manager.get_user_action_items()

if not action_items:
    st.success("✅ **Action Item Queue Clear:** No high-priority items require your attention. Well done!")
else:
    st.warning(f"**Attention Required:** You have **{len(action_items)}** items in your queue.")
    for item in action_items:
        st.page_link(
            page=item['page_link'],
            label=f"**{item['title']}**: {item['details']}",
            icon=item['icon']
        )
st.markdown("---")

# --- 4. ROLE-BASED STRATEGIC DASHBOARD ---
user_role = st.session_state.user_role
st.header(f"'{user_role}' Command Center", anchor=False)

# --- DTE Leadership View: Strategic & Operational Health ---
if user_role == 'DTE Leadership':
    st.markdown("##### High-level overview of operational efficiency, program risk, and system health.")
    
    # --- KPIs with Embedded SME Explanations ---
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        active_devs = session_manager.get_kpi('active_deviations')
        st.metric(
            "Active Deviations",
            active_devs['value'],
            help=active_devs['sme_info']
        )
    with kpi_cols[1]:
        dqs = session_manager.get_kpi('data_quality_score')
        st.metric(
            "Data Quality Score (DQS)",
            f"{dqs['value']:.1f}%",
            f"{dqs['delta']:.1f}% vs Target",
            help=dqs['sme_info']
        )
    with kpi_cols[2]:
        fpy = session_manager.get_kpi('first_pass_yield')
        st.metric(
            "First Pass Yield (FPY)",
            f"{fpy['value']:.1f}%",
            f"{fpy['delta']:.1f}%",
            help=fpy['sme_info']
        )
    with kpi_cols[3]:
        mttr = session_manager.get_kpi('mean_time_to_resolution')
        st.metric(
            "Deviation MTTR (Days)",
            f"{mttr['value']:.1f}",
            f"{mttr['delta']:.1f} Days",
            delta_color="inverse",
            help=mttr['sme_info']
        )

    st.markdown("---")
    
    # --- Strategic Visualizations ---
    col1, col2 = st.columns((6, 4))
    with col1:
        st.subheader("Program Risk Matrix", divider='gray')
        with st.expander("ℹ️ How to Read This Chart"):
            st.markdown("""
            This matrix provides a strategic overview of all major programs, plotting them based on data quality and schedule risk.
            - **X-axis (Days to Milestone):** Programs further to the left are closer to their next critical deadline.
            - **Y-axis (Data Quality Score):** Programs lower on the chart have more underlying data integrity issues.
            - **Bubble Size (Active Deviations):** Larger bubbles indicate a higher burden of unresolved quality events.
            
            **Your goal:** Proactively address programs moving towards the **High Priority** quadrant (bottom-left) before they become critical.
            """)
        risk_matrix_data = session_manager.get_risk_matrix_data()
        st.plotly_chart(
            plotting.plot_program_risk_matrix(risk_matrix_data),
            use_container_width=True
        )

    with col2:
        st.subheader("QC Failure Hotspots", divider='gray')
        with st.expander("ℹ️ How to Read This Chart"):
            st.markdown("""
            This Pareto chart follows the 80/20 rule to identify the "vital few" sources of error that cause the majority of data quality issues.
            - **Orange Bars (Count):** Show the raw frequency of each error type.
            - **Blue Line (Cumulative %):** Shows the cumulative percentage of total errors.
            
            **Your goal:** Focus systemic improvement efforts on the top 2-3 error types to achieve the greatest impact on overall data quality.
            """)
        pareto_data = session_manager.get_pareto_data()
        st.plotly_chart(
            plotting.plot_pareto_chart(pareto_data),
            use_container_width=True
        )

# --- Scientist, Director, Analyst Views: Focus on Navigation ---
else:
    st.info("💡 **Welcome to VERITAS.** Your mission-critical tools are available in the sidebar. Your personalized **Mission Briefing** above will guide you to urgent tasks.")
    st.markdown("""
    This centralized platform is designed to accelerate our scientific mission by providing robust, automated, and compliant data solutions. Use the navigation on the left to access the following modules:
    - **QC & Integrity Center:** Perform deep-dive analysis and validate data quality.
    - **Process Capability:** Monitor historical process performance and stability.
    - **Stability Program:** Analyze stability trends and project shelf-life.
    - **Regulatory Support:** Compile and generate submission-ready reports.
    - **Deviation Hub:** Manage the lifecycle of all quality events.
    - **Governance & Audit:** Ensure compliance and trace data lineage.
    """)

# --- 5. COMPLIANCE FOOTER ---
auth.display_compliance_footer()
