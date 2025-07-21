import streamlit as st
import pandas as pd
import numpy as np
from veritas_core import session, auth
from veritas_core.engine import analytics, plotting

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="QC & Integrity Center",
    page_icon="🧪",
    layout="wide"
)

# --- 2. APPLICATION INITIALIZATION & AUTH ---
session.initialize_session() 
session_manager = session.SessionManager()
auth.render_page()

# --- 3. DATA LOADING & FILTERING ---
hplc_data = session_manager.get_data('hplc')

st.sidebar.subheader("Data Selection", divider='blue')
study_id_options = sorted(hplc_data['study_id'].unique())
study_id = st.sidebar.selectbox("Select Study for QC", options=study_id_options)
selected_df = hplc_data[hplc_data['study_id'] == study_id].copy()
st.sidebar.info(f"**{len(selected_df)}** data points loaded for study **'{study_id}'**.")

# --- 4. PAGE HEADER ---
st.title("🧪 QC & Integrity Center")
st.markdown("A suite of advanced tools for data quality validation and anomaly detection.")
st.markdown("---")

# --- 5. UI TABS FOR DIFFERENT QC WORKFLOWS ---
tab1, tab2, tab3 = st.tabs(["📋 **Rule-Based QC Engine**", "📊 **Statistical Deep Dive**", "🤖 **ML Anomaly Detection**"])

with tab1:
    st.header("Automated Rule-Based Quality Control")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("1. Configure QC Rules", anchor=False)
        with st.form("qc_rules_form"):
            st.write("**Select Checks to Perform:**")
            rules_config = {
                'check_nulls': st.checkbox("Check for critical missing values", value=True),
                'check_negatives': st.checkbox("Check for impossible negative values", value=True),
                'check_spec_limits': st.checkbox("Check against CQA specifications", value=True),
            }
            submitted = st.form_submit_button("▶️ Execute QC Analysis", type="primary")
    if submitted:
        with st.spinner("Running QC checks..."):
            discrepancy_report = analytics.apply_qc_rules(
                df=selected_df,
                rules_config=rules_config,
                app_config=session_manager.settings.app
            )
            session_manager.update_page_state('qc_report', discrepancy_report)
    with col2:
        st.subheader("2. Review QC Results", anchor=False)
        report_df = session_manager.get_page_state('qc_report')
        if report_df is None:
            st.info("Configure rules and click 'Execute QC Analysis' to see results.")
        else:
            st.metric("Discrepancies Found", len(report_df))
            if not report_df.empty:
                st.error(f"Found **{len(report_df)}** issues requiring attention.")
                st.dataframe(report_df, use_container_width=True, hide_index=True)
                st.subheader("3. Take Action", anchor=False)
                if st.button("Create Deviation Ticket from Results", type="secondary"):
                    new_dev_id = session_manager.create_deviation_from_qc(report_df, study_id)
                    st.success(f"Successfully created and pre-populated a new ticket: **{new_dev_id}**.")
                    st.info("Navigate to the **Deviation Hub** to manage the investigation.")
            else:
                st.success("✅ Congratulations! No rule-based discrepancies were found in this dataset.")

with tab2:
    st.header("Statistical Deep Dive")
    numeric_cols = selected_df.select_dtypes(include=np.number).columns.tolist()
    param = st.selectbox("Select Parameter for Statistical Analysis", options=numeric_cols)
    data_to_test = selected_df[param].dropna()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Shapiro-Wilk Normality Test", anchor=False)
        normality_results = analytics.perform_normality_test(data_to_test)
        if normality_results['p_value'] is not None:
            st.metric("P-value", f"{normality_results['p_value']:.4f}")
            if normality_results['p_value'] > 0.05:
                st.success(normality_results['conclusion'])
            else:
                st.warning(normality_results['conclusion'])
        else:
            st.info(normality_results['conclusion'])
    with col2:
        st.subheader("Descriptive Statistics", anchor=False)
        st.dataframe(data_to_test.describe())
    st.plotly_chart(plotting.plot_qq(data_to_test), use_container_width=True)

with tab3:
    st.header("Machine Learning-Powered Anomaly Detection")
    numeric_cols_ml = selected_df.select_dtypes(include=np.number).columns.tolist()
    if len(numeric_cols_ml) >= 3:
        with st.form("ml_anomaly_form"):
            st.subheader("Configure Anomaly Detection", anchor=False)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                x_col = st.selectbox("X-axis variable", numeric_cols_ml, index=numeric_cols_ml.index('Purity') if 'Purity' in numeric_cols_ml else 0)
            with col2:
                y_col = st.selectbox("Y-axis variable", numeric_cols_ml, index=numeric_cols_ml.index('Bio-activity') if 'Bio-activity' in numeric_cols_ml else 1)
            with col3:
                z_col = st.selectbox("Z-axis variable", numeric_cols_ml, index=numeric_cols_ml.index('Main Impurity') if 'Main Impurity' in numeric_cols_ml else 2)
            with col4:
                contamination = st.slider("Anomaly Sensitivity", 0.01, 0.2, 0.05, 0.01, help="The estimated proportion of outliers in the data.")
            ml_submitted = st.form_submit_button("🤖 Find Anomalies", type="primary")
        if ml_submitted:
            predictions, data_fitted = analytics.run_anomaly_detection(selected_df, [x_col, y_col, z_col], contamination)
            session_manager.update_page_state('ml_results', {
                'preds': predictions, 'data': data_fitted, 'cols': [x_col, y_col, z_col]
            })
        ml_results = session_manager.get_page_state('ml_results')
        if ml_results and ml_results['preds'] is not None:
            st.plotly_chart(
                plotting.plot_ml_anomaly_results_3d(
                    df=ml_results['data'],
                    cols=ml_results['cols'],
                    labels=ml_results['preds']
                ),
                use_container_width=True
            )
            anomaly_count = (ml_results['preds'] == -1).sum()
            st.success(f"Analysis complete. Found **{anomaly_count}** potential anomalies for review (highlighted in red).")
    else:
        st.warning("This dataset does not have enough numeric columns (at least 3 required) for 3D ML anomaly detection.")

auth.display_compliance_footer()
