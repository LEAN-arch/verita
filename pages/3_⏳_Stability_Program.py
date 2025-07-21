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
from veritas_core import bootstrap, session
from veritas_core.engine import analytics, plotting

# --- 1. APPLICATION BOOTSTRAP ---
bootstrap.run("Stability Dashboard", "⏳")

# --- 2. SESSION MANAGER ACCESS ---
session_manager = session.SessionManager()

# --- 3. DATA LOADING & FILTERING ---
stability_data = session_manager.get_data('stability')
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

# --- 4. PAGE CONTENT ---
st.title("⏳ Stability Program Dashboard")
st.markdown("Monitor stability data, project shelf-life with statistical confidence, and perform multi-lot poolability analysis for regulatory submissions.")
st.markdown("---")

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
                st.warning(f"Purity data from these lots should NOT be pooled.", icon="⚠️")
    with col2:
        impurity_result = poolability_results.get('Main Impurity (%)', {})
        if impurity_result:
            st.metric("Main Impurity (%) Poolability p-value", f"{impurity_result['p_value']:.3f}")
            if impurity_result['poolable']:
                st.success(f"Impurity data from these lots can be pooled.", icon="✅")
            else:
                st.warning(f"Impurity data from these lots should NOT be pooled.", icon="⚠️")
    st.markdown("---")

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
                st.metric("Trend Slope", f"{projection['slope']:.3f} / month", help="Linear regression slope.")
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
                 st.metric("Trend Slope", f"+{projection['slope']:.3f} / month", help="Linear regression slope.")

    st.subheader("Raw Stability Data", anchor=False)
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
else:
    st.warning("No stability data available for the selected product and lot combination.")

auth.display_compliance_footer()
