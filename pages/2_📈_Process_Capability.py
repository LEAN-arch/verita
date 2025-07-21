# ==============================================================================
# Page 2: Process Capability Dashboard
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This module provides a Streamlit-based interface for Statistical Process Control
# (SPC) and root cause analysis in the VERITAS application. It includes tabs for
# process capability/control charts and ANOVA-based root cause analysis, integrating
# with veritas_core modules for session management, analytics, and plotting. The
# module ensures GxP compliance with robust error handling and data validation.
# ==============================================================================

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict, Any
from veritas_core import bootstrap, session, auth
from veritas_core.engine import analytics, plotting

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Render the Process Capability Dashboard page for the VERITAS application.

    Provides two tabs:
    1. Capability & Control Charts: Displays process stability and capability metrics.
    2. Root Cause Analysis (ANOVA): Investigates process variation using ANOVA and Tukey's HSD.

    Raises:
        RuntimeError: If session initialization, data loading, or analytics fail.
        ValueError: If data, configuration, or session state is invalid.
    """
    # --- 1. Application Bootstrap ---
    try:
        bootstrap.run("Process Capability", "📈")
    except Exception as e:
        logger.error(f"Bootstrap failed: {str(e)}")
        st.error("Failed to initialize Process Capability Dashboard. Please contact support.")
        raise RuntimeError(f"Bootstrap failed: {str(e)}")

    # --- 2. Session Manager Access ---
    try:
        session_manager = session.SessionManager()
    except Exception as e:
        logger.error(f"SessionManager initialization failed: {str(e)}")
        st.error("Failed to initialize session. Please contact support.")
        raise RuntimeError(f"SessionManager initialization failed: {str(e)}")

    # --- 3. Data Loading & Filtering ---
    try:
        hplc_data = session_manager.get_data('hplc')
        deviations_data = session_manager.get_data('deviations')
        if not isinstance(hplc_data, pd.DataFrame) or not isinstance(deviations_data, pd.DataFrame):
            raise ValueError("get_data('hplc') and get_data('deviations') must return pandas DataFrames")
        if hplc_data.empty or 'study_id' not in hplc_data.columns or 'instrument_id' not in hplc_data.columns:
            raise ValueError("HPLC data must be non-empty and contain 'study_id' and 'instrument_id' columns")
        if deviations_data.empty:
            logger.warning("Deviations data is empty")
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        st.error("Failed to load HPLC or deviations data. Please try again later.")
        return

    try:
        cpk_config = session_manager.settings.app.process_capability
        if not hasattr(cpk_config, 'available_cqas') or not isinstance(cpk_config.available_cqas, list):
            raise ValueError("cpk_config.available_cqas must be a list")
        if not hasattr(cpk_config, 'spec_limits') or not isinstance(cpk_config.spec_limits, dict):
            raise ValueError("cpk_config.spec_limits must be a dictionary")
        if not hasattr(cpk_config, 'cpk_target') or not isinstance(cpk_config.cpk_target, (int, float)):
            raise ValueError("cpk_config.cpk_target must be a number")
        for cqa in cpk_config.available_cqas:
            if cqa not in cpk_config.spec_limits or not hasattr(cpk_config.spec_limits[cqa], 'lsl') or not hasattr(cpk_config.spec_limits[cqa], 'usl'):
                raise ValueError(f"spec_limits for CQA '{cqa}' must have 'lsl' and 'usl' attributes")
    except Exception as e:
        logger.error(f"Invalid cpk_config: {str(e)}")
        st.error("Invalid process capability configuration. Please contact support.")
        return

    st.sidebar.subheader("Filter Data", divider='blue')
    try:
        study_options = sorted(hplc_data['study_id'].unique())
        if not study_options:
            st.sidebar.warning("No studies available for selection.")
            st.warning("No studies available for analysis.")
            return
        study_filter = st.sidebar.multiselect("Filter by Study:", options=study_options, default=[study_options[0]] if study_options else [])
        instrument_options = ['All'] + sorted(hplc_data['instrument_id'].unique())
        instrument_filter = st.sidebar.selectbox("Filter by Instrument:", options=instrument_options)

        if not study_filter:
            st.warning("Please select at least one study to begin analysis.")
            return
        filtered_df = hplc_data[hplc_data['study_id'].isin(study_filter)].copy()
        if instrument_filter != 'All':
            filtered_df = filtered_df[filtered_df['instrument_id'] == instrument_filter]
        if filtered_df.empty:
            st.sidebar.warning("No data points match the selected filters.")
            st.warning("No data available for the selected filters.")
            return
        st.sidebar.success(f"**{len(filtered_df)}** data points selected for analysis.")
    except Exception as e:
        logger.error(f"Failed to filter data: {str(e)}")
        st.error("Failed to filter data. Please try again.")
        return

    # --- 4. Page Content ---
    st.title("📈 Process Capability Dashboard")
    st.markdown("Analyze historical process stability, quantify capability, and perform root cause analysis on process variation.")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📊 **Capability & Control Charts**", "🔬 **Root Cause Analysis (ANOVA)**"])

    with tab1:
        st.header("Process Performance Analysis")
        st.info("""
        **Purpose:** To assess process performance over time. A process must be **stable** (in control) before its **capability** can be meaningfully calculated. Use the interactive tools below to monitor stability and simulate capability under different scenarios.
        """)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            try:
                if not all(cqa in filtered_df.columns for cqa in cpk_config.available_cqas):
                    raise ValueError("Some CQAs in available_cqas are not in filtered DataFrame")
                selected_cqa = st.selectbox("Select a CQA:", options=cpk_config.available_cqas, index=cpk_config.available_cqas.index('purity') if 'purity' in cpk_config.available_cqas else 0)
            except Exception as e:
                logger.error(f"Failed to select CQA: {str(e)}")
                st.error("Failed to load CQAs. Please try again.")
                return
        with col2:
            try:
                default_lsl = cpk_config.spec_limits[selected_cqa].lsl
                default_usl = cpk_config.spec_limits[selected_cqa].usl
                st.write("**Interactive Specification Limits (for 'What-If' Analysis):**")
                lsl_col, usl_col = st.columns(2)
                lsl = lsl_col.number_input("Lower Spec Limit (LSL)", value=float(default_lsl), format="%.2f", step=0.1)
                usl = usl_col.number_input("Upper Spec Limit (USL)", value=float(default_usl), format="%.2f", step=0.1)
                if lsl >= usl:
                    st.error("LSL must be less than USL.")
                    return
            except Exception as e:
                logger.error(f"Failed to configure spec limits: {str(e)}")
                st.error("Invalid specification limits. Please try again.")
                return

        st.markdown("---")
        
        if len(filtered_df) > 2:
            try:
                cpk_value = analytics.calculate_cpk(filtered_df[selected_cqa], lsl, usl)
                if cpk_value is not None and not isinstance(cpk_value, (int, float)):
                    raise ValueError("calculate_cpk must return a number or None")
                plot_col1, plot_col2 = st.columns(2)
                with plot_col1:
                    st.subheader("Process Stability (Control Chart)", anchor=False)
                    try:
                        st.plotly_chart(plotting.plot_historical_control_chart(filtered_df, selected_cqa, deviations_data), use_container_width=True)
                    except Exception as e:
                        logger.error(f"Failed to render control chart: {str(e)}")
                        st.error("Failed to display control chart. Please try again.")
                with plot_col2:
                    st.subheader("Process Capability (Histogram)", anchor=False)
                    try:
                        st.plotly_chart(plotting.plot_process_capability(filtered_df, selected_cqa, lsl, usl, cpk_value, cpk_config.cpk_target), use_container_width=True)
                    except Exception as e:
                        logger.error(f"Failed to render capability histogram: {str(e)}")
                        st.error("Failed to display capability histogram. Please try again.")
            except Exception as e:
                logger.error(f"Process capability analysis failed: {str(e)}")
                st.error("Failed to perform process capability analysis. Please try again.")
        else:
            st.warning("Not enough data available (minimum 3 points) for the selected filters to perform analysis.")

    with tab2:
        st.header("Investigate Process Variation with ANOVA")
        st.info("""
        **Purpose:** To determine if there is a statistically significant difference between the means of two or more groups. This is a powerful tool to investigate if a factor like **Instrument** or **Analyst** is causing variation in your process.
        """)
        
        st.subheader("1. Configure ANOVA Test", anchor=False)
        
        col1, col2 = st.columns(2)
        with col1:
            try:
                value_col = st.selectbox("Select CQA to Analyze:", options=cpk_config.available_cqas, key="anova_value", index=cpk_config.available_cqas.index('purity') if 'purity' in cpk_config.available_cqas else 0)
                if value_col not in filtered_df.columns:
                    raise ValueError(f"CQA '{value_col}' not found in filtered DataFrame")
            except Exception as e:
                logger.error(f"Failed to select ANOVA CQA: {str(e)}")
                st.error("Failed to load CQAs for ANOVA. Please try again.")
                return
        with col2:
            try:
                group_options = ['instrument_id', 'analyst', 'batch_id']
                if not all(col in filtered_df.columns for col in group_options):
                    raise ValueError("Not all grouping factors (instrument_id, analyst, batch_id) are in filtered DataFrame")
                group_col = st.selectbox("Select Grouping Factor to Test:", options=group_options, key="anova_group")
            except Exception as e:
                logger.error(f"Failed to select ANOVA grouping factor: {str(e)}")
                st.error("Failed to load grouping factors for ANOVA. Please try again.")
                return
                
        if st.button("🔬 Run ANOVA Analysis", type="primary"):
            try:
                if filtered of filtered_df[group_col].nunique() <= 1:
                    st.warning(f"Only one group found for '{group_col}'. Cannot perform ANOVA.")
                else:
                    with st.spinner("Performing Analysis of Variance..."):
                        anova_results = analytics.perform_anova(filtered_df, value_col, group_col)
                        if not isinstance(anova_results, dict) or 'p_value' not in anova_results:
                            raise ValueError("perform_anova must return a dict with 'p_value'")
                        session_manager.update_page_state('anova_results', anova_results)
                        if anova_results['p_value'] <= 0.05 and filtered_df[group_col].nunique() > 2:
                            tukey_results = analytics.perform_tukey_hsd(filtered_df, value_col, group_col)
                            if not isinstance(tukey_results, pd.DataFrame) or not all(col in tukey_results.columns for col in ['group1', 'group2', 'reject']):
                                raise ValueError("perform_tukey_hsd must return a DataFrame with 'group1', 'group2', 'reject' columns")
                            session_manager.update_page_state('tukey_results', tukey_results)
                        else:
                            session_manager.clear_page_state('tukey_results')
            except Exception as e:
                logger.error(f"ANOVA analysis failed: {str(e)}")
                st.error("Failed to perform ANOVA analysis. Please try again.")
                
        try:
            anova_results = session_manager.get_page_state('anova_results')
            if anova_results and isinstance(anova_results, dict) and 'p_value' in anova_results:
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
                    try:
                        st.plotly_chart(plotting.plot_anova_results(filtered_df, value_col, group_col, anova_results), use_container_width=True)
                    except Exception as e:
                        logger.error(f"Failed to render ANOVA plot: {str(e)}")
                        st.error("Failed to display ANOVA results plot. Please try again.")
                
                tukey_results = session_manager.get_page_state('tukey_results')
                if tukey_results is not None and isinstance(tukey_results, pd.DataFrame) and not tukey_results.empty:
                    st.markdown("---")
                    st.subheader("3. Post-Hoc Analysis (Tukey's HSD)", anchor=False)
                    st.info("""
                    **What is this?** Since the ANOVA test was significant (p <= 0.05), we run a Tukey's HSD test to determine **exactly which groups are different from each other**.
                    **How to read the table:** The `reject` column is the key. If `True`, it means there is a statistically significant difference between `group1` and `group2`.
                    """)
                    try:
                        st.dataframe(tukey_results, use_container_width=True, hide_index=True)
                        significant_pairs = tukey_results[tukey_results['reject'] == True]
                        if not significant_pairs.empty:
                            conclusion = "The following pairs are significantly different: "
                            pairs_text = [f"**{row['group1']}** vs **{row['group2']}**" for index, row in significant_pairs.iterrows()]
                            st.error(f"**Actionable Insight:** {conclusion}" + ", ".join(pairs_text) + ".", icon="🎯")
                    except Exception as e:
                        logger.error(f"Failed to render Tukey HSD results: {str(e)}")
                        st.error("Failed to display Tukey's HSD results. Please try again.")
            else:
                st.info("Run ANOVA analysis to see results.")
        except Exception as e:
            logger.error(f"Failed to render ANOVA results: {str(e)}")
            st.error("Failed to load ANOVA results. Please try again.")

    # --- 5. Compliance Footer ---
    try:
        auth.display_compliance_footer()
    except Exception as e:
        logger.error(f"Failed to render compliance footer: {str(e)}")
        st.warning("Failed to display compliance footer.")

if __name__ == "__main__":
    main()

