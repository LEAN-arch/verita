import streamlit as st
import pandas as pd
from veritas_core import bootstrap, session, auth

# --- 1. APPLICATION BOOTSTRAP ---
bootstrap.run("Deviation Hub", "📌")

# --- 2. SESSION MANAGER ACCESS ---
session_manager = session.SessionManager()

# --- 3. DATA LOADING & CONFIG ---
deviations_df = session_manager.get_data('deviations')
hplc_data = session_manager.get_data('hplc')
dev_config = session_manager.settings.app.deviation_management

# --- 4. PAGE LOGIC: DETERMINE VIEW (MASTER VS DETAIL) ---
if 'selected_dev_id' in st.session_state and st.session_state.selected_dev_id:
    # --- RENDER DETAIL VIEW: INVESTIGATION PANE ---
    selected_dev_id = st.session_state.selected_dev_id
    dev_data = session_manager.get_deviation_details(selected_dev_id)
    
    st.title(f"📌 Investigation: {selected_dev_id}")
    if st.button("⬅️ Back to Kanban Board"):
        del st.session_state.selected_dev_id
        st.rerun()
        
    if not dev_data.empty:
        dev = dev_data.iloc[0]
        detail_tab, data_tab, rca_tab, capa_tab = st.tabs(["📝 Details", "🔗 Linked Data", "🔎 RCA", "🛠️ CAPA"])
        with detail_tab:
            st.metric("Status", dev['status'])
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
            st.text_area("Corrective Action(s):", key=f"capa_corrective_{selected_dev_id}", value=dev.get('capa_corrective', ''))
            st.text_area("Preventive Action(s):", key=f"capa_preventive_{selected_dev_id}", value=dev.get('capa_preventive', ''))
            st.date_input("Target Completion Date:", key=f"capa_date_{selected_dev_id}")
        
        if st.button("💾 Save Investigation", type="primary"):
            st.success(f"Investigation details for {selected_dev_id} saved.")
    else:
        st.error(f"Deviation ID {selected_dev_id} not found.")

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
                with st.popover(f"**{card_id}**: {card_data['title']}", use_container_width=True):
                    st.markdown(f"**Priority:** {card_data['priority']}")
                    st.markdown(f"**Linked Record:** `{card_data['linked_record']}`")
                    if st.button("Open Full Investigation...", key=f"open_{card_id}"):
                        st.session_state.selected_dev_id = card_id
                        st.rerun()
                if status != dev_config.kanban_states[-1]:
                    if st.button("▶️ Advance", key=f"advance_{card_id}", help=f"Move from {status} to next stage"):
                        session_manager.advance_deviation_status(card_id, status)
                        st.rerun()
                st.markdown("<hr style='margin-top: 5px; margin-bottom: 5px;'/>", unsafe_allow_html=True)

# --- 5. COMPLIANCE FOOTER ---
auth.display_compliance_footer()
