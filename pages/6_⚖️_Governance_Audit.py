# ==============================================================================
# Page 6: Governance & Audit Hub (Ultimate Version)
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
#
# Description:
# This module is the central command center for all GxP compliance, data
# integrity, and system governance activities. It provides the tools necessary
# to demonstrate control and traceability to auditors and stakeholders.
# ==============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime

# Import the core backend components.
from veritas_core import session, auth
from veritas_core.engine import plotting

# --- 1. PAGE SETUP AND AUTHENTICATION ---
session_manager = session.SessionManager()
session_manager.initialize_page("Governance & Audit", "⚖️")

# --- 2. DATA LOADING ---
audit_data = session_manager.get_data('audit')

# --- 3. PAGE HEADER ---
st.title("⚖️ Governance & Audit Hub")
st.markdown("Central hub for 21 CFR Part 11 compliance, data lineage, and system audit trails.")
st.markdown("---")

# --- 4. UI TABS FOR DIFFERENT GOVERNANCE VIEWS ---
tab1, tab2, tab3 = st.tabs(["🔍 **Audit Trail Explorer**", "🧬 **Visual Data Lineage**", "✍️ **E-Signature Log**"])

with tab1:
    st.header("Interactive Audit Trail Explorer")
    st.info("Search, filter, and export the immutable, 21 CFR Part 11-compliant audit trail for all system activities.")
    
    with st.expander("Show Filter Options", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            users_to_filter = st.multiselect("Filter by User:", options=sorted(audit_data['User'].unique()))
        with col2:
            actions_to_filter = st.multiselect("Filter by Action:", options=sorted(audit_data['Action'].unique()))
        with col3:
            record_id_filter = st.text_input("Filter by Record ID (contains):")
    
    # Apply Filters
    filtered_df = audit_data.copy()
    if users_to_filter:
        filtered_df = filtered_df[filtered_df['User'].isin(users_to_filter)]
    if actions_to_filter:
        filtered_df = filtered_df[filtered_df['Action'].isin(actions_to_filter)]
    if record_id_filter:
        filtered_df = filtered_df[filtered_df['Record ID'].str.contains(record_id_filter, case=False, na=False)]
        
    st.metric("Total Records Found", f"{len(filtered_df)} of {len(audit_data)}")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    st.download_button(
        "Export Filtered Results to CSV", 
        filtered_df.to_csv(index=False).encode('utf-8'), 
        f"VERITAS_Audit_Export_{datetime.now().strftime('%Y%m%d')}.csv", 
        "text/csv",
        type="primary"
    )

with tab2:
    st.header("Visual Data Lineage Tracer")
    st.info("Trace the complete history of any data record from creation to final state. This provides an end-to-end, auditable map of a record's lifecycle.")
    
    valid_ids = sorted([str(i) for i in audit_data['Record ID'].unique() if i and i != 'N/A' and not i.startswith("system")])
    
    if valid_ids:
        record_counts = audit_data['Record ID'].value_counts()
        if not record_counts.empty:
            good_example_id = record_counts.idxmax()
            default_index = valid_ids.index(good_example_id) if good_example_id in valid_ids else 0
        else:
            default_index = 0

        record_id = st.selectbox(
            "Select a Record ID to Trace:", 
            options=valid_ids,
            index=default_index,
        )
        
        if record_id:
            with st.spinner("Generating lineage graph..."):
                lineage_fig = plotting.plot_data_lineage_graph(audit_data, record_id)
                st.graphviz_chart(lineage_fig)
    else:
        st.warning("No traceable records found in the audit log.")
        
with tab3:
    st.header("Electronic Signature Log")
    st.info("A live, filtered view of all electronic signature events, demonstrating compliance with 21 CFR Part 11.")
    
    sig_df = session_manager.get_signatures_log()
    
    if not sig_df.empty:
        st.dataframe(
            sig_df[['Timestamp', 'User', 'Action', 'Record ID', 'Details']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("No electronic signature events have been recorded in the audit trail yet.")

# --- 5. COMPLIANCE FOOTER ---
auth.display_compliance_footer()
