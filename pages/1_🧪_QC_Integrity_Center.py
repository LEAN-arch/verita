
# ==============================================================================
# Page 1: QC & Integrity Center
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This module serves as the primary workbench for scientists and QC analysts in the
# VERITAS application, providing tools for data quality validation and anomaly detection.
# It includes tabs for rule-based QC, statistical analysis, and ML-powered anomaly detection,
# integrating with veritas_core modules for session management, analytics, and plotting.
# The module ensures GxP compliance and robust error handling for reliable operation.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple
from veritas_core import bootstrap, session
from veritas_core.engine import analytics, plotting

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Render the QC & Integrity Center page for the VERITAS application.

    Provides a Streamlit-based interface with three tabs:
    1. Rule-Based QC Engine: Applies configurable QC rules and creates deviation tickets.
    2. Statistical Deep Dive: Performs normality tests and displays descriptive statistics.
    3. ML Anomaly Detection: Runs 3D anomaly detection using machine learning.

    Raises:
        RuntimeError: If session initialization, data loading, or analytics fail.
        ValueError: If data or session state is invalid.
    """
    # --- 1. Application Bootstrap ---
    try:
        bootstrap.run("QC & Integrity Center", "🧪")
    except Exception as e:
        logger.error(f"Bootstrap failed: {str(e)}")
        st.error("Failed to initialize QC & Integrity Center. Please contact support.")
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
        if not isinstance(hplc_data, pd.DataFrame):
            raise ValueError("get_data('hplc') must return a pandas DataFrame")
        if hplc_data.empty or 'study_id' not in hplc_data.columns:
            raise ValueError("HPLC data must be non-empty and contain 'study_id' column")
    except Exception as e:
        logger.error(f"Failed to load HPLC data: {str(e)}")
        st.error("Failed to load HPLC data. Please try again later.")
        return

    st.sidebar.subheader("Data Selection", divider='blue')
    try:
        study_id_options = sorted(hplc_data['study_id'].unique())
        if not study_id_options:
            st.sidebar.warning("No studies available for selection.")
            return
        study_id = st.sidebar.selectbox("Select Study for QC", options=study_id_options)
        selected_df = hplc_data[hplc_data['study_id'] == study_id].copy()
        if selected_df.empty:
            st.sidebar.warning(f"No data points available for study '{study_id}'.")
        else:
            st.sidebar.info(f"**{len(selected_df)}** data points loaded for study **'{study_id}'**.")
    except Exception as e:
        logger.error(f"Failed to filter data: {str(e)}")
        st.sidebar.error("Failed to load study data. Please try again.")
        return

    # --- 4. Page Content ---
    st.title("🧪 QC & Integrity Center")
    st.markdown("A suite of advanced tools for data quality validation and anomaly detection.")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 **Rule-Based QC Engine**", "📊 **Statistical Deep Dive**", "🤖 **ML Anomaly Detection**"])

    with tab1:
        st.header("Automated Rule-Based Quality Control")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("1. Configure QC Rules", anchor=False)
            with st.form("qc_rules_form"):
                rules_config = {
                    'check_nulls': st.checkbox("Check for critical missing values", value=True),
                    'check_negatives': st.checkbox("Check for impossible negative values", value=True),
                    'check_spec_limits': st.checkbox("Check against CQA specifications", value=True),
                }
                submitted = st.form_submit_button("▶️ Execute QC Analysis", type="primary")
            if submitted:
                with st.spinner("Running QC checks..."):
                    try:
                        discrepancy_report = analytics.apply_qc_rules(
                            df=selected_df,
                            rules_config=rules_config,
                            app_config=session_manager.settings.app
                        )
                        if not isinstance(discrepancy_report, pd.DataFrame):
                            raise ValueError("apply_qc_rules must return a pandas DataFrame")
                        session_manager.update_page_state('qc_report', discrepancy_report)
                    except Exception as e:
                        logger.error(f"QC analysis failed: {str(e)}")
                        st.error("Failed to execute QC analysis. Please try again.")
        with col2:
            st.subheader("2. Review QC Results", anchor=False)
            try:
                report_df = session_manager.get_page_state('qc_report')
                if report_df is None:
                    st.info("Configure rules and click 'Execute QC Analysis' to see results.")
                else:
                    if not isinstance(report_df, pd.DataFrame):
                        raise ValueError("qc_report must be a pandas DataFrame")
                    st.metric("Discrepancies Found", len(report_df))
                    if not report_df.empty:
                        st.error(f"Found **{len(report_df)}** issues requiring attention.")
                        st.dataframe(report_df, use_container_width=True, hide_index=True)
                        st.subheader("3. Take Action", anchor=False)
                        if st.button("Create Deviation Ticket from Results", type="secondary"):
                            try:
                                new_dev_id = session_manager.create_deviation_from_qc(report_df, study_id)
                                if not isinstance(new_dev_id, str):
                                    raise ValueError("create_deviation_from_qc must return a string")
                                st.success(f"Successfully created and pre-populated a new ticket: **{new_dev_id}**.")
                            except Exception as e:
                                logger.error(f"Failed to create deviation ticket: {str(e)}")
                                st.error("Failed to create deviation ticket. Please try again.")
                    else:
                        st.success("✅ Congratulations! No rule-based discrepancies were found.")
            except Exception as e:
                logger.error(f"Failed to render QC results: {str(e)}")
                st.error("Failed to display QC results. Please try again.")

    with tab2:
        st.header("Statistical Deep Dive")
        try:
            numeric_cols = selected_df.select_dtypes(include=np.number).columns.tolist()
            if not numeric_cols:
                st.warning("No numeric columns available for statistical analysis.")
            else:
                param = st.selectbox("Select Parameter for Statistical Analysis", options=numeric_cols, index=numeric_cols.index('purity') if 'purity' in numeric_cols else 0)
                data_to_test = selected_df[param].dropna()
                if data_to_test.empty:
                    st.warning(f"No valid data for parameter '{param}'.")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Shapiro-Wilk Normality Test", anchor=False)
                        try:
                            normality_results = analytics.perform_normality_test(data_to_test)
                            if not isinstance(normality_results, dict) or not all(key in normality_results for key in ['p_value', 'conclusion']):
                                raise ValueError("perform_normality_test must return a dict with 'p_value' and 'conclusion'")
                            if normality_results['p_value'] is not None:
                                st.metric("P-value", f"{normality_results['p_value']:.4f}")
                                if normality_results['p_value'] > 0.05:
                                    st.success(normality_results['conclusion'])
                                else:
                                    st.warning(normality_results['conclusion'])
                            else:
                                st.info(normality_results['conclusion'])
                        except Exception as e:
                            logger.error(f"Normality test failed: {str(e)}")
                            st.error("Failed to perform normality test. Please try again.")
                    with col2:
                        st.subheader("Descriptive Statistics", anchor=False)
                        try:
                            st.dataframe(data_to_test.describe(), use_container_width=True)
                        except Exception as e:
                            logger.error(f"Failed to render descriptive statistics: {str(e)}")
                            st.error("Failed to display descriptive statistics.")
                    try:
                        st.plotly_chart(plotting.plot_qq(data_to_test), use_container_width=True)
                    except Exception as e:
                        logger.error(f"Failed to render Q-Q plot: {str(e)}")
                        st.error("Failed to display Q-Q plot. Please try again.")
        except Exception as e:
            logger.error(f"Statistical analysis failed: {str(e)}")
            st.error("Failed to load statistical analysis tab. Please try again.")

    with tab3:
        st.header("Machine Learning-Powered Anomaly Detection")
        try:
            numeric_cols_ml = selected_df.select_dtypes(include=np.number).columns.tolist()
            if len(numeric_cols_ml) < 3:
                st.warning("This dataset does not have enough numeric columns (minimum 3) for 3D ML anomaly detection.")
            else:
                with st.form("ml_anomaly_form"):
                    st.subheader("Configure Anomaly Detection", anchor=False)
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        x_col = st.selectbox("X-axis variable", numeric_cols_ml, index=numeric_cols_ml.index('purity') if 'purity' in numeric_cols_ml else 0)
                    with col2:
                        y_col = st.selectbox("Y-axis variable", numeric_cols_ml, index=numeric_cols_ml.index('bio_activity') if 'bio_activity' in numeric_cols_ml else 1)
                    with col3:
                        z_col = st.selectbox("Z-axis variable", numeric_cols_ml, index=numeric_cols_ml.index('main_impurity') if 'main_impurity' in numeric_cols_ml else 2)
                    with col4:
                        contamination = st.slider("Anomaly Sensitivity", 0.01, 0.2, 0.05, 0.01)
                    ml_submitted = st.form_submit_button("🤖 Find Anomalies", type="primary")
                if ml_submitted:
                    try:
                        predictions, data_fitted = analytics.run_anomaly_detection(selected_df, [x_col, y_col, z_col], contamination)
                        if not isinstance(predictions, np.ndarray) or not isinstance(data_fitted, pd.DataFrame):
                            raise ValueError("run_anomaly_detection must return a tuple of (np.ndarray, pd.DataFrame)")
                        session_manager.update_page_state('ml_results', {
                            'preds': predictions,
                            'data': data_fitted,
                            'cols': [x_col, y_col, z_col]
                        })
                    except Exception as e:
                        logger.error(f"Anomaly detection failed: {str(e)}")
                        st.error("Failed to run anomaly detection. Please try again.")
                try:
                    ml_results = session_manager.get_page_state('ml_results')
                    if ml_results and isinstance(ml_results, dict) and all(key in ml_results for key in ['preds', 'data', 'cols']):
                        if not isinstance(ml_results['preds'], np.ndarray) or not isinstance(ml_results['data'], pd.DataFrame) or not isinstance(ml_results['cols'], list):
                            raise ValueError("ml_results must contain 'preds' (np.ndarray), 'data' (pd.DataFrame), and 'cols' (list)")
                        st.plotly_chart(plotting.plot_ml_anomaly_results_3d(
                            df=ml_results['data'],
                            cols=ml_results['cols'],
                            labels=ml_results['preds']
                        ), use_container_width=True)
                        anomaly_count = (ml_results['preds'] == -1).sum()
                        st.success(f"Analysis complete. Found **{anomaly_count}** potential anomalies.")
                    else:
                        st.info("Configure anomaly detection and click 'Find Anomalies' to see results.")
                except Exception as e:
                    logger.error(f"Failed to render anomaly detection results: {str(e)}")
                    st.error("Failed to display anomaly detection results. Please try again.")
        except Exception as e:
            logger.error(f"ML anomaly detection tab failed: {str(e)}")
            st.error("Failed to load anomaly detection tab. Please try again.")

if __name__ == "__main__":
    main()
