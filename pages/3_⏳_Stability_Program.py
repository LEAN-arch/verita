# ==============================================================================
# Page 3: Stability Program Dashboard
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This module provides a Streamlit-based interface for analyzing drug stability data
# in the VERITAS application, supporting shelf-life determination and regulatory filings.
# It includes multi-lot poolability analysis (ANCOVA) and stability trend projections,
# integrating with veritas_core modules for session management, analytics, and plotting.
# The module ensures GxP compliance with robust error handling and data validation.
# ==============================================================================

import streamlit as st
import pandas as pd
import logging
from typing import Dict, List, Any
from veritas_core import bootstrap, session, auth
from veritas_core.engine import analytics, plotting

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Render the Stability Program Dashboard page for the VERITAS application.

    Provides a comprehensive suite for:
    1. Multi-Lot Poolability Assessment: Uses ANCOVA to determine if lots can be pooled per ICH Q1E.
    2. Stability Profile: Displays trend projections for purity and main impurity with shelf-life estimates.

    Raises:
        RuntimeError: If session initialization, data loading, or analytics fail.
        ValueError: If data, configuration, or session state is invalid.
    """
    # --- 1. Application Bootstrap ---
    try:
        bootstrap.run("Stability Dashboard", "⏳")
    except Exception as e:
        logger.error(f"Bootstrap failed: {str(e)}")
        st.error("Failed to initialize Stability Dashboard. Please contact support.")
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
        stability_data = session_manager.get_data('stability')
        if not isinstance(stability_data, pd.DataFrame):
            raise ValueError("get_data('stability') must return a pandas DataFrame")
        if stability_data.empty or not all(col in stability_data.columns for col in ['product_id', 'lot_id']):
            raise ValueError("Stability data must be non-empty and contain 'product_id' and 'lot_id' columns")
    except Exception as e:
        logger.error(f"Failed to load stability data: {str(e)}")
        st.error("Failed to load stability data. Please try again later.")
        return

    try:
        stability_config = session_manager.settings.app.stability_specs
        if not hasattr(stability_config, 'spec_limits') or not isinstance(stability_config.spec_limits, dict):
            raise ValueError("stability_config.spec_limits must be a dictionary")
        if not stability_config.spec_limits:
            raise ValueError("stability_config.spec_limits cannot be empty")
        for assay in stability_config.spec_limits:
            if not hasattr(stability_config.spec_limits[assay], 'lsl') or not hasattr(stability_config.spec_limits[assay], 'usl'):
                raise ValueError(f"spec_limits for assay '{assay}' must have 'lsl' and 'usl' attributes")
    except Exception as e:
        logger.error(f"Invalid stability_config: {str(e)}")
        st.error("Invalid stability configuration. Please contact support.")
        return

    st.sidebar.subheader("Select Stability Study", divider='blue')
    try:
        product_options = sorted(stability_data['product_id'].unique())
        if not product_options:
            st.sidebar.warning("No products available for selection.")
            st.warning("No stability data available for analysis.")
            return
        product_filter = st.sidebar.selectbox("Select Product:", options=product_options)

        lot_options = sorted(stability_data[stability_data['product_id'] == product_filter]['lot_id'].unique())
        if not lot_options:
            st.sidebar.warning(f"No lots available for product '{product_filter}'.")
            st.warning("No lots available for analysis.")
            return
        lot_filter = st.sidebar.multiselect(
            "Select Lot(s):",
            options=lot_options,
            default=[lot_options[0]] if lot_options else [],
            help="Select multiple lots to perform a poolability analysis (per ICH Q1E guidelines)."
        )

        if not lot_filter:
            st.warning("Please select at least one lot to begin analysis.")
            return
        filtered_df = stability_data[(stability_data['product_id'] == product_filter) & (stability_data['lot_id'].isin(lot_filter))].copy()
        if filtered_df.empty:
            st.warning("No stability data available for the selected product and lot combination.")
            return
    except Exception as e:
        logger.error(f"Failed to filter data: {str(e)}")
        st.error("Failed to filter stability data. Please try again.")
        return

    # --- 4. Page Content ---
    st.title("⏳ Stability Program Dashboard")
    st.markdown("Monitor stability data, project shelf-life with statistical confidence, and perform multi-lot poolability analysis for regulatory submissions.")
    st.markdown("---")

    poolability_results = {}
    if len(lot_filter) > 1:
        st.header("Multi-Lot Poolability Assessment (ANCOVA)")
        assays_to_test = [assay for assay in stability_config.spec_limits.keys() if assay in filtered_df.columns]
        if not assays_to_test:
            st.warning("No valid assays available for poolability analysis.")
        else:
            with st.spinner("Performing ANCOVA tests for lot poolability..."):
                try:
                    for assay in assays_to_test:
                        poolability_results[assay] = analytics.test_stability_poolability(filtered_df, assay)
                        if not isinstance(poolability_results[assay], dict) or not all(key in poolability_results[assay] for key in ['p_value', 'poolable']):
                            raise ValueError(f"test_stability_poolability for assay '{assay}' must return a dict with 'p_value' and 'poolable'")
                except Exception as e:
                    logger.error(f"ANCOVA poolability analysis failed: {str(e)}")
                    st.error("Failed to perform poolability analysis. Please try again.")

            col1, col2 = st.columns(2)
            with col1:
                try:
                    purity_result = poolability_results.get('purity', {})
                    if purity_result:
                        st.metric("Purity Poolability p-value", f"{purity_result['p_value']:.3f}")
                        if purity_result['poolable']:
                            st.success("Purity data from these lots can be pooled.", icon="✅")
                        else:
                            st.warning("Purity data from these lots should NOT be pooled.", icon="⚠️")
                    else:
                        st.info("No poolability results available for purity.")
                except Exception as e:
                    logger.error(f"Failed to render purity poolability results: {str(e)}")
                    st.error("Failed to display purity poolability results.")
            with col2:
                try:
                    impurity_result = poolability_results.get('main_impurity', {})
                    if impurity_result:
                        st.metric("Main Impurity Poolability p-value", f"{impurity_result['p_value']:.3f}")
                        if impurity_result['poolable']:
                            st.success("Main Impurity data from these lots can be pooled.", icon="✅")
                        else:
                            st.warning("Main Impurity data from these lots should NOT be pooled.", icon="⚠️")
                    else:
                        st.info("No poolability results available for main impurity.")
                except Exception as e:
                    logger.error(f"Failed to render main impurity poolability results: {str(e)}")
                    st.error("Failed to display main impurity poolability results.")
            st.markdown("---")

    st.header(f"Stability Profile for {product_filter} - Lot(s): {', '.join(lot_filter)}")
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            assay_purity = 'purity'
            if assay_purity in stability_config.spec_limits and assay_purity in filtered_df.columns:
                try:
                    use_pooled_purity = poolability_results.get(assay_purity, {}).get('poolable', False)
                    title = f"Purity Trend {'(Pooled Data)' if use_pooled_purity else ''}"
                    projection = analytics.calculate_stability_projection(filtered_df, assay_purity, use_pooled_purity)
                    if not isinstance(projection, dict) or 'slope' not in projection:
                        raise ValueError("calculate_stability_projection for purity must return a dict with 'slope'")
                    st.plotly_chart(
                        plotting.plot_stability_trend(filtered_df, assay_purity, title, stability_config.spec_limits[assay_purity], projection),
                        use_container_width=True
                    )
                    if projection and 'slope' in projection and projection['slope'] is not None:
                        st.metric("Trend Slope", f"{projection['slope']:.3f} / month", help="Linear regression slope.")
                except Exception as e:
                    logger.error(f"Failed to render purity stability trend: {str(e)}")
                    st.error("Failed to display purity stability trend. Please try again.")
            else:
                st.info("Purity data or specification limits not available.")
        with col2:
            assay_impurity = 'main_impurity'
            if assay_impurity in stability_config.spec_limits and assay_impurity in filtered_df.columns:
                try:
                    use_pooled_impurity = poolability_results.get(assay_impurity, {}).get('poolable', False)
                    title = f"Main Impurity Trend {'(Pooled Data)' if use_pooled_impurity else ''}"
                    projection = analytics.calculate_stability_projection(filtered_df, assay_impurity, use_pooled_impurity)
                    if not isinstance(projection, dict) or 'slope' not in projection:
                        raise ValueError("calculate_stability_projection for main impurity must return a dict with 'slope'")
                    st.plotly_chart(
                        plotting.plot_stability_trend(filtered_df, assay_impurity, title, stability_config.spec_limits[assay_impurity], projection),
                        use_container_width=True
                    )
                    if projection and 'slope' in projection and projection['slope'] is not None:
                        st.metric("Trend Slope", f"+{projection['slope']:.3f} / month", help="Linear regression slope.")
                except Exception as e:
                    logger.error(f"Failed to render main impurity stability trend: {str(e)}")
                    st.error("Failed to display main impurity stability trend. Please try again.")
            else:
                st.info("Main Impurity data or specification limits not available.")

        st.subheader("Raw Stability Data", anchor=False)
        try:
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        except Exception as e:
            logger.error(f"Failed to render raw stability data: {str(e)}")
            st.error("Failed to display raw stability data. Please try again.")
    else:
        st.warning("No stability data available for the selected product and lot combination.")

    # --- 5. Compliance Footer ---
    try:
        auth.display_compliance_footer()
    except Exception as e:
        logger.error(f"Failed to render compliance footer: {str(e)}")
        st.warning("Failed to display compliance footer.")

if __name__ == "__main__":
    main()
