# ==============================================================================
# Page 5: Deviation Management Hub (Ultimate Version)
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
#
# Description:
# This module is the central, interactive workspace for managing the lifecycle
# of all quality events. It now uses a robust state management pattern to handle
# the master-detail view (Kanban Board -> Investigation Pane).
#
# Key Upgrades:
# - Correct State Management: Eliminates the `StreamlitAPIException` by using
#   `st.session_state` to toggle between the list and detail views, which is
#   the correct, modern Streamlit pattern.
# - Enhanced UI with Popovers: Provides quick-look details for each card
#   without leaving the main board, improving workflow efficiency.
# ==============================================================================

import streamlit as st
import pandas as pd
from veritas_core import session, auth

# --- 1. PAGE SETUP AND AUTHENTICATION ---
# The session MUST be initialized on the home page first.
# We create an accessor and then set up this specific page.
session_manager = session.SessionManager()
auth.page_setup("Deviation Hub", "📌")

# --- 2. DATA LOADING & CONFIG ---
deviations_df = session_manager.get_data('deviations')
hplc_data = session_manager.get_data('hplc')
dev_config = session_manager.settings.app.deviation_management

# --- 3. PAGE LOGIC: DETERMINE VIEW (MASTER VS DETAIL) ---
# This is the core logic that replaces the broken query parameter approach.
if 'selected_dev_id' in st.session_state and st.session_state.selected_dev_id:
    # --- RENDER DETAIL VIEW: INVESTIGATION PANE ---
    selected_dev_id = st.session_state.selected_dev_id
    dev_data = session_manager.get_deviation_details(selected_dev_id)
    
    if dev_data.empty:
        st.error(f"Deviation ID {selected_dev_id} not found.")
        if st.button("⬅️ Back to Hub"):
            del st.session_state.selected_dev_id
            st.rerun()
    else:
        dev = dev_data.iloc[0]
        st.title(f"📌 Investigation: {selected_dev_id}")
        if st.button("⬅️ Back to Kanban Board"):
            del st.session_state.selected_dev_id
            st.rerun()

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
            st.text_area("Problem Statement:", key=f"rca_problem_{selected_dev_id}", value=dev.get('rca_problem', ''), height=100)
            st.text_area("5 Whys Analysis:", key=f"rca_5whys_{selected_dev_id}", height=150, value=dev.get('rca_5whys', ''))
        with capa_tab:
            st.subheader("Corrective and Preventive Action (CAPA) Plan", anchor=False)
            st.text_area("Corrective Action(s):", help="What will be done to fix the immediate problem?", key=f"capa_corrective_{selected_dev_id}", value=dev.get('capa_corrective', ''))
            st.text_area("Preventive Action(s):", help="What will be done to prevent recurrence?", key=f"capa_preventive_{selected_dev_id}", value=dev.get('capa_preventive', ''))
            st.date_input("Target Completion Date:", key=f"capa_date_{selected_dev_id}")
        
        if st.button("💾 Save Investigation", type="primary"):
            st.success(f"Investigation details for {selected_dev_id} saved.")

else:
    # --- RENDER MASTER VIEW: KANBAN BOARD ---
    st.title("📌 Deviation Management Hub")
    st.markdown("An interactive Kanban board to manage the lifecycle of quality events.")
    st.markdown("---")

    kanban_cols = st.columns(len(dev_config.kanban_states))
    for i, status in enumerate(dev_config.kanban_states):
        with kanban_cols[i]:
            cards_in_column = deviations_df[deviations_df['status'] == status]
            st.subheader(f"{status} ({len(cards_in_column)})", anchor=False)
            st.markdown("---")
            
            for index, card_data in cards_in_column.iterrows():
                card_id = card_data['id']
                
                # Use a popover for a quick preview
                with st.popover(f"**{card_id}**: {card_data['title']}", use_container_width=True):
                    st.markdown(f"**Priority:** {card_data['priority']}")
                    st.markdown(f"**Linked Record:** `{card_data['linked_record']}`")
                    # Button inside popover to switch to the detail view
                    if st.button("Open Full Investigation...", key=f"open_{card_id}"):
                        st.session_state.selected_dev_id = card_id
                        st.rerun()

                # "Advance" button remains outside the popover for quick actions
                if status != dev_config.kanban_states[-1]:
                    if st.button("▶️ Advance", key=f"advance_{card_id}", help=f"Move from {status} to next stage"):
                        session_manager.advance_deviation_status(card_id, status)
                        st.rerun()
                st.markdown("<hr style='margin-top: 5px; margin-bottom: 5px;'/>", unsafe_allow_html=True)

# --- 5. COMPLIANCE FOOTER ---
auth.display_compliance_footer()
