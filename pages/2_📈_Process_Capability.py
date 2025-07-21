import streamlit as st
import pandas as pd
from datetime import timedelta
from veritas_core import session, auth
from veritas_core.engine import analytics, plotting

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Process Capability",
    page_icon="📈",
    layout="wide"
)

# --- 2. APPLICATION INITIALIZATION & AUTH ---
session.initialize_session()
session_manager = session.SessionManager()
auth.render_page()

# --- 3. DATA LOADING & FILTERING ---
hplc_data = session_manager.get_data('hplc')
deviations_data = session_manager.get_data('deviations')
cpk_config = session_manager.settings.app.process_capability

st.sidebar.subheader("Filter Data", divider='blue')

study_options = sorted(hplc_data['study_id'].unique())
study_filter = st.sidebar.multiselect("Filter by Study:", options=study_options, default=study_options[0] if study_options else None)

instrument_options = ['All'] + sorted(hplc_data['instrument_id'].unique())
instrument_filter = st.sidebar.selectbox("Filter by Instrument:", options=instrument_options)

if study_filter:
    filtered_df = hplc_data[hplc_data['study_id'].isin(study_filter)].copy()
else:
    st.warning("Please select at least one study to begin analysis.")
    st.stop()

if instrument_filter != 'All':
    filtered_df = filtered_df[filtered_df['instrument_id'] == instrument_filter]

st.sidebar.success(f"**{len(filtered_df)}** data points selected for analysis.")

# --- 4. PAGE HEADER ---
st.title("📈 Process Capability Dashboard")
st.markdown("Analyze historical process stability, quantify capability, and perform root cause analysis on process variation.")
st.markdown("---")

# --- 5. UI TABS FOR DIFFERENT ANALYSIS TYPES ---
tab1, tab2 = st.tabs(["📊 **Capability & Control Charts**", "🔬 **Root Cause Analysis (ANOVA)**"])

with tab1:
    st.header("Process Performance Analysis")
    col1, col2 = st.columns([1, 2])
    with col1:
        selected_cqa = st.selectbox("Select a CQA:", options=cpk_config.available_cqas)
    with col2:
        default_lsl = cpk_config.spec_limits[selected_cqa].lsl
        default_usl = cpk_config.spec_limits[selected_cqa].usl
        st.write("**Interactive Specification Limits (for 'What-If' Analysis):**")
        lsl_col, usl_col = st.columns(2)
        lsl = lsl_col.number_input("Lower Spec Limit (LSL)", value=default_lsl, format="%.2f", step=0.1)
        usl = usl_col.number_input("Upper Spec Limit (USL)", value=default_usl, format="%.2f", step=0.1)

    st.markdown("---")
    
    if len(filtered_df) > 2:
        cpk_value = analytics.calculate_cpk(filtered_df[selected_cqa], lsl, usl)
        plot_col1, plot_col2 = st.columns(2)
        with plot_col1:
            st.subheader("Process Stability (Control Chart)", anchor=False)
            st.plotly_chart(plotting.plot_historical_control_chart(filtered_df, selected_cqa, deviations_data), use_container_width=True)
        with plot_col2:
            st.subheader("Process Capability (Histogram)", anchor=False)
            st.plotly_chart(plotting.plot_process_capability(filtered_df, selected_cqa, lsl, usl, cpk_value, cpk_config.cpk_target), use_container_width=True)
    else:
        st.warning("Not enough data available for the selected filters to perform analysis.")

with tab2:
    st.header("Investigate Process Variation with ANOVA")
    col1, col2 = st.columns(2)
    with col1:
        value_col = st.selectbox("Select CQA to Analyze:", options=cpk_config.available_cqas, key="anova_value")
    with col2:
        group_col = st.selectbox("Select Grouping Factor to Test:", options=['instrument_id', 'analyst', 'batch_id'], key="anova_group")
        
    if st.button("🔬 Run ANOVA Analysis", type="primary"):
        if filtered_df[group_col].nunique() > 1:
            with st.spinner("Performing Analysis of Variance..."):
                anova_results = analytics.perform_anova(filtered_df, value_col, group_col)
                session_manager.update_page_state('anova_results', anova_results)
                if anova_results and anova_results['p_value'] <= 0.05 and filtered_df[group_col].nunique() > 2:
                    tukey_results = analytics.perform_tukey_hsd(filtered_df, value_col, group_col)
                    session_manager.update_page_state('tukey_results', tukey_results)
                else:
                    session_manager.clear_page_state('tukey_results')
        else:
            st.warning(f"Only one group found for '{group_col}'. Cannot perform ANOVA.")
            
    anova_results = session_manager.get_page_state('anova_results')
    if anova_results:
        st.markdown("---")
        st.subheader("2. ANOVA Results", anchor=False)
        p_value = anova_results['p_value']
        col1, col2 = st.columns(2)
        with col1:
            st.metric("P-value", f"{p_value:.4f}")
            if p_value <= 0.05:
                st.error(f"**Conclusion:** Significant difference detected.", icon="🚨")
            else:
                st.success(f"**Conclusion:** No significant difference detected.", icon="✅")
        with col2:
            st.plotly_chart(plotting.plot_anova_results(filtered_df, value_col, group_col, anova_results), use_container_width=True)
        tukey_results = session_manager.get_page_state('tukey_results')
        if tukey_results is not None and not tukey_results.empty:
            st.markdown("---")
            st.subheader("3. Post-Hoc Analysis (Tukey's HSD)", anchor=False)
            st.dataframe(tukey_results, use_container_width=True, hide_index=True)
            significant_pairs = tukey_results[tukey_results['reject'] == True]
            if not significant_pairs.empty:
                conclusion = "The following pairs are significantly different: "
                pairs_text = [f"**{row.group1}** vs **{row.group2}**" for index, row in significant_pairs.iterrows()]
                st.error(f"**Actionable Insight:** {conclusion}" + ", ".join(pairs_text) + ".", icon="🎯")

auth.display_compliance_footer()
