
# ==============================================================================
# Page 6: Governance & Audit Hub
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This module provides a Streamlit-based interface for GxP compliance, data integrity,
# and system governance in the VERITAS application. It includes three tabs:
# 1. Audit Trail Explorer: Filter and export 21 CFR Part 11-compliant audit trails.
# 2. Visual Data Lineage: Trace the lifecycle of data records.
# 3. Electronic Signature Log: Display e-signature events.
# The module integrates with veritas_core modules for session management, authentication,
# and plotting, ensuring robust error handling and data validation.
# ==============================================================================

import streamlit as st
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Any
from veritas_core import session, auth
from veritas_core.engine import plotting

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Render the Governance & Audit Hub page for the VERITAS application.

    Provides three tabs for compliance and governance:
    1. Audit Trail Explorer: Search, filter, and export audit trails.
    2. Visual Data Lineage: Visualize the lifecycle of a selected record.
    3. Electronic Signature Log: Display e-signature events.

    Raises:
        RuntimeError: If session initialization, data loading, or plotting fails.
        ValueError: If data, configuration, or session state is invalid.
    """
    # --- 1. Page Setup and Authentication ---
    try:
        session_manager = session.SessionManager()
        if not hasattr(session_manager, 'settings') or not hasattr(session_manager.settings, 'app'):
            raise ValueError("session_manager.settings.app not found")
        session_manager.initialize_page("Governance & Audit", "⚖️")
        # Placeholder for authentication check (requires integration with auth system)
        if 'username' not in st.session_state or not auth.verify_credentials(st.session_state.username, None):
            raise ValueError("User authentication required for accessing Governance & Audit Hub")
    except Exception as e:
        logger.error(f"Page initialization failed: {str(e)}")
        st.error("Failed to initialize Governance & Audit Hub. Please contact support.")
        raise RuntimeError(f"Page initialization failed: {str(e)}")

    # --- 2. Data Loading ---
    try:
        audit_data = session_manager.get_data('audit')
        if not isinstance(audit_data, pd.DataFrame):
            raise ValueError("get_data('audit') must return a pandas DataFrame")
        required_cols = ['user', 'action', 'record_id']
        if audit_data.empty or not all(col in audit_data.columns for col in required_cols):
            raise ValueError("Audit data must be non-empty and contain 'user', 'action', 'record_id' columns")
    except Exception as e:
        logger.error(f"Failed to load audit data: {str(e)}")
        st.error("Failed to load audit data. Please try again later.")
        return

    # --- 3. Page Header ---
    st.title("⚖️ Governance & Audit Hub")
    st.markdown("Central hub for 21 CFR Part 11 compliance, data lineage, and system audit trails.")
    st.markdown("---")

    # --- 4. UI Tabs for Different Governance Views ---
    tab1, tab2, tab3 = st.tabs(["🔍 **Audit Trail Explorer**", "🧬 **Visual Data Lineage**", "✍️ **E-Signature Log**"])

    with tab1:
        st.header("Interactive Audit Trail Explorer")
        st.info("Search, filter, and export the immutable, 21 CFR Part 11-compliant audit trail for all system activities.")
        
        with st.expander("Show Filter Options", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                try:
                    users_to_filter = st.multiselect("Filter by User:", options=sorted(audit_data['user'].unique()))
                except Exception as e:
                    logger.error(f"Failed to load user filter options: {str(e)}")
                    st.error("Failed to load user filter options. Please try again.")
                    users_to_filter = []
            with col2:
                try:
                    actions_to_filter = st.multiselect("Filter by Action:", options=sorted(audit_data['action'].unique()))
                except Exception as e:
                    logger.error(f"Failed to load action filter options: {str(e)}")
                    st.error("Failed to load action filter options. Please try again.")
                    actions_to_filter = []
            with col3:
                record_id_filter = st.text_input("Filter by Record ID (contains):")
        
        # Apply Filters
        try:
            filtered_df = audit_data.copy()
            if users_to_filter:
                filtered_df = filtered_df[filtered_df['user'].isin(users_to_filter)]
            if actions_to_filter:
                filtered_df = filtered_df[filtered_df['action'].isin(actions_to_filter)]
            if record_id_filter:
                filtered_df = filtered_df[filtered_df['record_id'].str.contains(record_id_filter, case=False, na=False)]
            
            st.metric("Total Records Found", f"{len(filtered_df)} of {len(audit_data)}")
            if filtered_df.empty:
                st.info("No audit records match the selected filters.")
            else:
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            
            # Export Button with Authentication
            if st.button("Export Filtered Results to CSV", type="primary"):
                try:
                    # Placeholder for authentication check
                    if 'username' not in st.session_state or not auth.verify_credentials(st.session_state.username, None):
                        raise ValueError("User authentication required for exporting audit data")
                    st.download_button(
                        label="Download Filtered Results",
                        data=filtered_df.to_csv(index=False).encode('utf-8'),
                        file_name=f"VERITAS_Audit_Export_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                except Exception as e:
                    logger.error(f"Failed to export audit data: {str(e)}")
                    st.error("Failed to export audit data. Please try again.")
        except Exception as e:
            logger.error(f"Failed to render audit trail: {str(e)}")
            st.error("Failed to display audit trail. Please try again.")

    with tab2:
        st.header("Visual Data Lineage Tracer")
        st.info("Trace the complete history of any data record from creation to final state. This provides an end-to-end, auditable map of a record's lifecycle.")
        
        try:
            valid_ids = sorted([str(i) for i in audit_data['record_id'].unique() if pd.notna(i) and i.strip()])
            if not valid_ids:
                st.warning("No traceable records found in the audit log.")
            else:
                record_counts = audit_data['record_id'].value_counts()
                default_index = 0
                if not record_counts.empty:
                    good_example_id = record_counts.idxmax()
                    default_index = valid_ids.index(good_example_id) if good_example_id in valid_ids else 0
                
                record_id = st.selectbox(
                    "Select a Record ID to Trace:",
                    options=valid_ids,
                    index=default_index
                )
                
                if record_id:
                    with st.spinner("Generating lineage graph..."):
                        try:
                            lineage_fig = plotting.plot_data_lineage_graph(audit_data, record_id)
                            if not isinstance(lineage_fig, (str, object)):  # Assuming Graphviz object or str
                                raise ValueError("plot_data_lineage_graph must return a Graphviz-compatible object")
                            st.graphviz_chart(lineage_fig)
                        except Exception as e:
                            logger.error(f"Failed to generate lineage graph for {record_id}: {str(e)}")
                            st.error("Failed to display data lineage graph. Please try again.")
        except Exception as e:
            logger.error(f"Failed to render data lineage tab: {str(e)}")
            st.error("Failed to load data lineage options. Please try again.")

    with tab3:
        st.header("Electronic Signature Log")
        st.info("A live, filtered view of all electronic signature events, demonstrating compliance with 21 CFR Part 11.")
        
        try:
            sig_df = session_manager.get_signatures_log()
            required_sig_cols = ['timestamp', 'user', 'action', 'record_id', 'details']
            if not isinstance(sig_df, pd.DataFrame):
                raise ValueError("get_signatures_log must return a pandas DataFrame")
            if sig_df.empty:
                st.success("No electronic signature events have been recorded in the audit trail yet.")
            elif not all(col in sig_df.columns for col in required_sig_cols):
                raise ValueError("Signature log must contain required columns: timestamp, user, action, record_id, details")
            else:
                st.dataframe(
                    sig_df[required_sig_cols],
                    use_container_width=True,
                    hide_index=True
                )
        except Exception as e:
            logger.error(f"Failed to render signature log: {str(e)}")
            st.error("Failed to display electronic signature log. Please try again.")

    # --- 5. Compliance Footer ---
    try:
        auth.display_compliance_footer()
    except Exception as e:
        logger.error(f"Failed to render compliance footer: {str(e)}")
        st.warning("Failed to display compliance footer.")

if __name__ == "__main__":
    main()
