# ==============================================================================
# Page 3: Stability Program Dashboard (Ultimate Version)
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
#
# Description:
# This module provides a comprehensive suite for analyzing drug stability data,
# directly supporting shelf-life determination and regulatory filings.
# ==============================================================================

import streamlit as st
import pandas as pd

# Import the core backend components.
from veritas_core import session, auth
from veritas_core.engine import analytics, plotting

# --- 1. PAGE SETUP AND AUTHENTICATION ---
session_manager = session.SessionManager()
session_manager.initialize_page("Stability Dashboard", "⏳")

# --- 2. DATA LOADING & FILTERING ---
stability_data = session_manager.get_data('stability')
# --- ATTRIBUTE ERROR FIX ---
# Changed settings.APP to settings.app
stability_config = session_manager.settings.app.stability_specs

st.sidebar.subheader("Select Stability Study", divider='blue')

product_options = sorted(stability_data['product_id'].unique())
product_filter = st.sidebar.selectbox("Select Product:", options=product_options)

lot_options = sorted(stability_data[stability_data['product_id'] == product_filter]['lot_id'].unique())
lot_filter = st.sidebar.multiselect(
    "Select Lot(s):",
    options=lot_options,
    default=lot_options[0] if lot_options else None,
    help="Select multiple lots to perform a poolability analysis (per ICH Q1E guidelines)."
)

if not lot_filter:
    st.warning("Please select at least one lot to begin analysis.")
    st.stop()

filtered_df = stability_data[(stability_data['product_id'] == product_filter) & (stability_data['lot_id'].isin(lot_filter))]

# --- 3. PAGE HEADER ---
st.title("⏳ Stability Program Dashboard")
st.markdown("Monitor stability data, project shelf-life with statistical confidence, and perform multi-lot poolability analysis for regulatory submissions.")
with st.expander("ℹ️ SME Overview: The Role of a Stability Program (ICH Q1A & Q1E)"):
    st.info("""
        - **Purpose:** To provide evidence on how the quality of a drug product varies with time, which is foundational for determining storage conditions and shelf life.
        - **Data Pooling (ICH Q1E):** When data from multiple lots are shown to be statistically similar (via ANCOVA), they can be pooled. This provides a single, more precise shelf-life estimate, which is highly desirable for regulatory filings.
        - **How to Use:** Select a product and one or more lots. The system will automatically perform a poolability assessment and generate trend analyses.
    """)
st.markdown("---")

# --- 4. MULTI-LOT POOLABILITY ANALYSIS ---
poolability_results = {}
if len(lot_filter) > 1:
    st.header("Multi-Lot Poolability Assessment (ANCOVA)")
    assays_to_test = list(stability_config.spec_limits.keys())
    
    with st.spinner("Performing ANCOVA tests for lot poolability..."):
        for assay in assays_to_test:
            poolability_results[assay] = analytics.test_stability_poolability(filtered_df, assay)

    col1, col2 = st.columns(2)
    with col1:
        purity_result = poolability_results.get('Purity (%)', {})
        if purity_result:
            st.metric("Purity (%) Poolability p-value", f"{purity_result['p_value']:.3f}")
            if purity_result['poolable']:
                st.success(f"Purity data from these lots can be pooled.", icon="✅")
            else:
                st.warning(f"Purity data from these lots should NOT be pooled. Analyze separately.", icon="⚠️")
    with col2:
        impurity_result = poolability_results.get('Main Impurity (%)', {})
        if impurity_result:
            st.metric("Main Impurity (%) Poolability p-value", f"{impurity_result['p_value']:.3f}")
            if impurity_result['poolable']:
                st.success(f"Impurity data from these lots can be pooled.", icon="✅")
            else:
                st.warning(f"Impurity data from these lots should NOT be pooled. Analyze separately.", icon="⚠️")
    st.markdown("---")


# --- 5. STABILITY TREND ANALYSIS ---
st.header(f"Stability Profile for {product_filter} - Lot(s): {', '.join(lot_filter)}")

if not filtered_df.empty:
    col1, col2 = st.columns(2)

    with col1:
        assay_purity = 'Purity (%)'
        if assay_purity in stability_config.spec_limits:
            use_pooled_purity = poolability_results.get(assay_purity, {}).get('poolable', False)
            title = f"Purity (%) Trend {'(Pooled Data)' if use_pooled_purity else ''}"
            projection = analytics.calculate_stability_projection(filtered_df, assay_purity, use_pooled_purity)
            st.plotly_chart(
                plotting.plot_stability_trend(filtered_df, assay_purity, title, stability_config.spec_limits[assay_purity], projection),
                use_container_width=True
            )
            if projection and 'slope' in projection:
                st.metric("Trend Slope", f"{projection['slope']:.3f} / month", help="Linear regression slope of the stability trend.")

    with col2:
        assay_impurity = 'Main Impurity (%)'
        if assay_impurity in stability_config.spec_limits:
            use_pooled_impurity = poolability_results.get(assay_impurity, {}).get('poolable', False)
            title = f"Main Impurity (%) Trend {'(Pooled Data)' if use_pooled_impurity else ''}"
            projection = analytics.calculate_stability_projection(filtered_df, assay_impurity, use_pooled_impurity)
            st.plotly_chart(
                plotting.plot_stability_trend(filtered_df, assay_impurity, title, stability_config.spec_limits[assay_impurity], projection),
                use_container_width=True
            )
            if projection and 'slope' in projection:
                 st.metric("Trend Slope", f"+{projection['slope']:.3f} / month", help="Linear regression slope of the stability trend.")

    st.subheader("Raw Stability Data", anchor=False)
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
else:
    st.warning("No stability data available for the selected product and lot combination.")

# --- 6. COMPLIANCE FOOTER ---
auth.display_compliance_footer()
