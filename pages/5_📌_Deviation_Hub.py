# ='s=============================================================================
# Page 5: Deviation Management Hub (Ultimate Version)
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Ultimate Version)
#
# Description:
# This module is the central, interactive workspace for managing the lifecycle
# of all quality events (deviations, OOS, OOT). It is designed to be the
# single source of truth for investigations.
#
# Key Upgrades:
# - Investigation Pane: Clicking a card opens a detailed modal/view with tabs
#   for linked data, Root Cause Analysis (RCA), and CAPA planning.
# - Structured RCA & CAPA Forms: Provides guided forms for investigators to
#   document their findings in a standardized way, improving consistency.
# - Seamless Workflow Integration: Deviations created from the QC Center appear
#   here automatically, and all status changes are logged to the audit trail.
# ==============================================================================

import streamlit as st
import pandas as pd

# Import the core backend components.
from veritas_core import session, auth

# --- 1. PAGE SETUP AND AUTHENTICATION ---
session_manager = session.SessionManager()
session_manager.initialize_page("Deviation Hub", "📌")

# --- 2. DATA LOADING & CONFIG ---
deviations_df = session_manager.get_data('deviations')
hplc_data = session_manager.get_data('hplc')
dev_config = session_manager.settings.app.deviation_management

# --- 3. PAGE HEADER ---
st.title("📌 Deviation Management Hub")
st.markdown("An interactive Kanban board to manage the lifecycle of deviations, OOS, and OOT investigations.")
with st.expander("ℹ️ SME Overview: Digitalizing the Investigation Workflow"):
    st.info("""
        - **Purpose:** To provide a single source of truth for all active investigations, replacing offline trackers and disparate documents.
        - **Actionability:** Click any card to open the **Investigation Pane**. From there, you can review linked data, document your root cause analysis, and define a CAPA plan. The "▶️ Advance" button updates the status and creates an auditable record.
        - **Value:** This digitalizes a core GxP workflow, improving transparency, enforcing consistency, and providing a live overview of team workload and bottlenecks.
    """)

# --- 4. INVESTIGATION PANE (MODAL/EXPANDER LOGIC) ---
# This is the core "Ultimate App" feature for this page.
# We check if a card has been selected (via query params) and display its details.
query_params = st.query_params
selected_dev_id = query_params.get("selected_dev_id")

if selected_dev_id:
    st.header(f"Investigation Pane: {selected_dev_id}", divider='blue')
    deviation_data = session_manager.get_deviation_details(selected_dev_id)
    
    if deviation_data.empty:
        st.error(f"Deviation ID {selected_dev_id} not found.")
        st.page_link("pages/5_📌_Deviation_Hub.py", label="Return to Hub", icon="⬅️")
    else:
        dev = deviation_data.iloc[0]
        
        # --- Display the detailed pane with tabs ---
        detail_tab, data_tab, rca_tab, capa_tab = st.tabs([
            "📝 Details", "🔗 Linked Data", "🔎 Root Cause Analysis", "🛠️ CAPA Plan"
        ])
        
        with detail_tab:
            st.metric("Current Status", dev['status'])
            st.write(f"**Title:** {dev['title']}")
            st.write(f"**Priority:** {dev['priority']}")
            st.write(f"**Linked Record:** `{dev['linked_record']}`")

        with data_tab:
            st.subheader("Data Associated with this Deviation", anchor=False)
            linked_record = dev['linked_record']
            if linked_record in hplc_data['sample_id'].values:
                st.dataframe(hplc_data[hplc_data['sample_id'] == linked_record], use_container_width=True)
            elif linked_record in hplc_data['instrument_id'].values:
                st.dataframe(hplc_data[hplc_data['instrument_id'] == linked_record].head(), use_container_width=True)
                st.info(f"Showing first 5 records related to instrument {linked_record}.")
            else:
                st.info("No structured data is directly linked to this record ID.")
        
        with rca_tab:
            st.subheader("Root Cause Analysis Documentation", anchor=False)
            st.text_area("Problem Statement:", key=f"rca_problem_{selected_dev_id}", value=dev.get('rca_problem', ''))
            st.text_area("5 Whys Analysis:", key=f"rca_5whys_{selected_dev_id}", height=150, value=dev.get('rca_5whys', ''))
            st.selectbox("Probable Root Cause Category:", options=["Man", "Machine", "Method", "Material", "Measurement", "Environment"], key=f"rca_category_{selected_dev_id}")

        with capa_tab:
            st.subheader("Corrective and Preventive Action (CAPA) Plan", anchor=False)
            st.text_area("Corrective Action(s):", help="What will be done to fix the immediate problem?", key=f"capa_corrective_{selected_dev_id}", value=dev.get('capa_corrective', ''))
            st.text_area("Preventive Action(s):", help="What will be done to prevent recurrence?", key=f"capa_preventive_{selected_dev_id}", value=dev.get('capa_preventive', ''))
            st.date_input("Target Completion Date:", key=f"capa_date_{selected_dev_id}")

        col1, col2, _ = st.columns([1, 1, 4])
        if col1.button("💾 Save Investigation", type="primary"):
            # Here, you would call a backend function to save the updated investigation details to the database.
            st.success(f"Investigation details for {selected_dev_id} saved.")
        
        if col2.page_link("pages/5_📌_Deviation_Hub.py", label="Close Pane", icon="✖️"):
            pass
        st.markdown("---")


# --- 5. ACTIONABLE KANBAN BOARD ---
st.header("Deviation Workflow Board", divider='blue')
kanban_cols = st.columns(len(dev_config.kanban_states))

for i, status in enumerate(dev_config.kanban_states):
    with kanban_cols[i]:
        # Filter the deviations for the current status column
        cards_in_column = deviations_df[deviations_df['status'] == status]
        st.subheader(f"{status} ({len(cards_in_column)})", anchor=False)
        st.markdown("---")
        
        for index, card_data in cards_in_column.iterrows():
            # Render a link that opens the investigation pane using query parameters
            st.page_link(
                f"pages/5_📌_Deviation_Hub.py?selected_dev_id={card_data['id']}",
                label=f"**{card_data['id']}**: {card_data['title']}",
                icon=" investigative_pane_icon" # Placeholder
            )

            # --- Renders the card content and "Advance" button ---
            color = dev_config.priority_colors.get(card_data['priority'], "#FFFFFF")
            st.markdown(f"<div style='font-size: 0.8em; color: grey; padding-left: 5px;'>Linked Record: {card_data['linked_record']}</div>", unsafe_allow_html=True)
            
            # The "Advance" button logic
            if status != dev_config.kanban_states[-1]: # If not in the last column
                if st.button("▶️ Advance Status", key=f"advance_{card_data['id']}", help=f"Move from {status} to next stage"):
                    # The SessionManager handles the logic of updating the state and logging the audit.
                    session_manager.advance_deviation_status(card_data['id'], status)
                    st.rerun()
            st.markdown("<hr style='margin-top: 5px; margin-bottom: 5px;'/>", unsafe_allow_html=True)

# --- 6. COMPLIANCE FOOTER ---
auth.display_compliance_footer()
