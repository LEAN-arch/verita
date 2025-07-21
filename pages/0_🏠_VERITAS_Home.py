import streamlit as st
import pandas as pd
from veritas_core import session, auth
from veritas_core.engine import plotting

# --- 1. PAGE CONFIGURATION ---
# This MUST be the first Streamlit command on each page.
st.set_page_config(
    page_title="VERITAS Mission Control",
    page_icon="🏠",
    layout="wide"
)

# --- 2. APPLICATION INITIALIZATION & AUTH ---
# This sequence is now the standard for every page.
session.initialize_session() 
session_manager = session.SessionManager()
auth.render_page() # This handles the auth check and sidebar rendering

# --- 3. PAGE CONTENT ---
st.title("🏠 VERITAS Mission Control")
st.subheader("Your Mission Briefing", divider='blue')
# ... (rest of the page logic is correct and remains the same)
action_items = session_manager.get_user_action_items()
if not action_items:
    st.success("✅ Your action item queue is clear. Well done!")
else:
    st.warning(f"You have **{len(action_items)}** items requiring your attention.")
    for item in action_items:
        st.page_link(page=item['page_link'], label=f"**{item['title']}**: {item['details']}", icon=item['icon'])
st.markdown("---")

user_role = st.session_state.user_role
st.header(f"'{user_role}' Command Center", anchor=False)
if user_role == 'DTE Leadership':
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
    st.info("💡 **Welcome to VERITAS.** Your mission-critical tools are available in the sidebar.")

auth.display_compliance_footer()
