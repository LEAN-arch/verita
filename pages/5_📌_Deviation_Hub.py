# ==============================================================================
# Page 5: Deviation Management Hub
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This module provides a Streamlit-based interface for managing quality deviations in the
# VERITAS application. It offers a Kanban board view for tracking deviation statuses and a
# detailed investigation view for individual deviations, supporting root cause analysis (RCA)
# and corrective/preventive actions (CAPA). The module integrates with veritas_core modules
# for session management and authentication, ensuring GxP compliance with robust error handling
# and data validation.
# ==============================================================================

import streamlit as st
import pandas as pd
import logging
from typing import Dict, List, Any
from datetime import date
from veritas_core import bootstrap, session, auth

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Render the Deviation Management Hub page for the VERITAS application.

    Provides two views:
    1. Master View (Kanban Board): Displays deviations by status with options to advance or open investigations.
    2. Detail View (Investigation Pane): Allows detailed analysis, RCA, and CAPA planning for a selected deviation.

    Raises:
        RuntimeError: If session initialization, data loading, or deviation operations fail.
        ValueError: If data, configuration, or session state is invalid.
    """
    # --- 1. Application Bootstrap ---
    try:
        bootstrap.run("Deviation Hub", "📌")
    except Exception as e:
        logger.error(f"Bootstrap failed: {str(e)}")
        st.error("Failed to initialize Deviation Hub. Please contact support.")
        raise RuntimeError(f"Bootstrap failed: {str(e)}")

    # --- 2. Session Manager Access ---
    try:
        session_manager = session.SessionManager()
    except Exception as e:
        logger.error(f"SessionManager initialization failed: {str(e)}")
        st.error("Failed to initialize session. Please contact support.")
        raise RuntimeError(f"SessionManager initialization failed: {str(e)}")

    # --- 3. Data Loading & Configuration ---
    try:
        deviations_df = session_manager.get_data('deviations')
        hplc_data = session_manager.get_data('hplc')
        if not isinstance(deviations_df, pd.DataFrame) or not isinstance(hplc_data, pd.DataFrame):
            raise ValueError("get_data('deviations') and get_data('hplc') must return pandas DataFrames")
        required_dev_cols = ['id', 'status', 'title', 'priority', 'linked_record']
        if deviations_df.empty or not all(col in deviations_df.columns for col in required_dev_cols):
            raise ValueError("Deviations data must be non-empty and contain required columns: id, status, title, priority, linked_record")
        if hplc_data.empty or not all(col in hplc_data.columns for col in ['sample_id', 'instrument_id']):
            raise ValueError("HPLC data must be non-empty and contain 'sample_id' and 'instrument_id' columns")
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        st.error("Failed to load deviations or HPLC data. Please try again later.")
        return

    try:
        dev_config = session_manager.settings.app.deviation_management
        if not hasattr(dev_config, 'kanban_states') or not isinstance(dev_config.kanban_states, list) or not dev_config.kanban_states:
            raise ValueError("dev_config.kanban_states must be a non-empty list")
    except Exception as e:
        logger.error(f"Invalid dev_config: {str(e)}")
        st.error("Invalid deviation management configuration. Please contact support.")
        return

    # --- 4. Page Logic: Determine View (Master vs Detail) ---
    if 'selected_dev_id' in st.session_state and st.session_state.selected_dev_id:
        # --- Detail View: Investigation Pane ---
        selected_dev_id = st.session_state.selected_dev_id
        try:
            dev_data = session_manager.get_deviation_details(selected_dev_id)
            if not isinstance(dev_data, pd.DataFrame):
                raise ValueError("get_deviation_details must return a pandas DataFrame")
            if dev_data.empty:
                raise ValueError(f"Deviation ID {selected_dev_id} not found")
        except Exception as e:
            logger.error(f"Failed to load deviation details for {selected_dev_id}: {str(e)}")
            st.error(f"Failed to load deviation ID {selected_dev_id}. Please try again.")
            if st.button("⬅️ Back to Kanban Board"):
                del st.session_state.selected_dev_id
                st.rerun()
            return

        st.title(f"📌 Investigation: {selected_dev_id}")
        if st.button("⬅️ Back to Kanban Board"):
            try:
                del st.session_state.selected_dev_id
                st.rerun()
            except Exception as e:
                logger.error(f"Failed to rerun after back button: {str(e)}")
                st.error("Failed to return to Kanban board. Please try again.")

        try:
            dev = dev_data.iloc[0]
            required_dev_cols = ['status', 'title', 'priority', 'linked_record']
            if not all(col in dev_data.columns for col in required_dev_cols):
                raise ValueError("Deviation data must contain required columns: status, title, priority, linked_record")
            detail_tab, data_tab, rca_tab, capa_tab = st.tabs(["📝 Details", "🔗 Linked Data", "🔎 RCA", "🛠️ CAPA"])
            with detail_tab:
                st.metric("Status", dev['status'])
                st.write(f"**Title:** {dev['title']}")
                st.write(f"**Priority:** {dev['priority']}")
                st.write(f"**Linked Record:** `{dev['linked_record']}`")
            with data_tab:
                st.subheader("Data Associated with this Deviation", anchor=False)
                linked_record = dev['linked_record']
                try:
                    if linked_record in hplc_data['sample_id'].values:
                        st.dataframe(hplc_data[hplc_data['sample_id'] == linked_record], use_container_width=True, hide_index=True)
                    elif linked_record in hplc_data['instrument_id'].values:
                        linked_data = hplc_data[hplc_data['instrument_id'] == linked_record].head()
                        if linked_data.empty:
                            st.info(f"No data found for instrument {linked_record}.")
                        else:
                            st.dataframe(linked_data, use_container_width=True, hide_index=True)
                            st.info(f"Showing first 5 records related to instrument {linked_record}.")
                    else:
                        st.info("No structured data is directly linked to this record ID.")
                except Exception as e:
                    logger.error(f"Failed to render linked data for {linked_record}: {str(e)}")
                    st.error("Failed to display linked data. Please try again.")
            with rca_tab:
                st.subheader("Root Cause Analysis Documentation", anchor=False)
                rca_problem = st.text_area("Problem Statement:", key=f"rca_problem_{selected_dev_id}", value=dev.get('rca_problem', ''), height=100)
                rca_5whys = st.text_area("5 Whys Analysis:", key=f"rca_5whys_{selected_dev_id}", height=150, value=dev.get('rca_5whys', ''))
            with capa_tab:
                st.subheader("Corrective and Preventive Action (CAPA) Plan", anchor=False)
                capa_corrective = st.text_area("Corrective Action(s):", key=f"capa_corrective_{selected_dev_id}", value=dev.get('capa_corrective', ''))
                capa_preventive = st.text_area("Preventive Action(s):", key=f"capa_preventive_{selected_dev_id}", value=dev.get('capa_preventive', ''))
                capa_date = st.date_input("Target Completion Date:", key=f"capa_date_{selected_dev_id}", value=date.today())
            
            if st.button("💾 Save Investigation", type="primary"):
                try:
                    # Placeholder for authentication check (requires integration with auth system)
                    if 'username' not in st.session_state or not auth.verify_credentials(st.session_state.username, None):
                        raise ValueError("User authentication required for saving investigation details")
                    session_manager.update_deviation_details(
                        deviation_id=selected_dev_id,
                        updates={
                            'rca_problem': rca_problem,
                            'rca_5whys': rca_5whys,
                            'capa_corrective': capa_corrective,
                            'capa_preventive': capa_preventive,
                            'capa_date': capa_date
                        }
                    )
                    st.success(f"Investigation details for {selected_dev_id} saved successfully.")
                except Exception as e:
                    logger.error(f"Failed to save investigation details for {selected_dev_id}: {str(e)}")
                    st.error("Failed to save investigation details. Please try again.")
        except Exception as e:
            logger.error(f"Failed to render deviation details for {selected_dev_id}: {str(e)}")
            st.error(f"Failed to display deviation details for {selected_dev_id}. Please try again.")
    else:
        # --- Master View: Kanban Board ---
        st.title("📌 Deviation Management Hub")
        st.markdown("An interactive Kanban board to manage the lifecycle of quality events.")
        st.markdown("---")
        try:
            kanban_cols = st.columns(len(dev_config.kanban_states))
            for i, status in enumerate(dev_config.kanban_states):
                with kanban_cols[i]:
                    cards_in_column = deviations_df[deviations_df['status'] == status]
                    st.subheader(f"{status} ({len(cards_in_column)})", anchor=False)
                    st.markdown("---")
                    if cards_in_column.empty:
                        st.info(f"No deviations in {status} status.")
                    for index, card_data in cards_in_column.iterrows():
                        try:
                            card_id = card_data['id']
                            required_card_cols = ['title', 'priority', 'linked_record']
                            if not all(col in card_data for col in required_card_cols):
                                raise ValueError(f"Card {card_id} missing required columns")
                            with st.popover(f"**{card_id}**: {card_data['title']}", use_container_width=True):
                                st.markdown(f"**Priority:** {card_data['priority']}")
                                st.markdown(f"**Linked Record:** `{card_data['linked_record']}`")
                                if st.button("Open Full Investigation...", key=f"open_{card_id}"):
                                    try:
                                        st.session_state.selected_dev_id = card_id
                                        st.rerun()
                                    except Exception as e:
                                        logger.error(f"Failed to open investigation for {card_id}: {str(e)}")
                                        st.error(f"Failed to open investigation for {card_id}. Please try again.")
                            if status != dev_config.kanban_states[-1]:
                                if st.button("▶️ Advance", key=f"advance_{card_id}", help=f"Move from {status} to next stage"):
                                    try:
                                        # Placeholder for authentication check
                                        if 'username' not in st.session_state or not auth.verify_credentials(st.session_state.username, None):
                                            raise ValueError("User authentication required for advancing deviation status")
                                        session_manager.advance_deviation_status(card_id, status)
                                        st.rerun()
                                    except Exception as e:
                                        logger.error(f"Failed to advance deviation {card_id}: {str(e)}")
                                        st.error(f"Failed to advance deviation {card_id}. Please try again.")
                            st.markdown("<hr style='margin-top: 5px; margin-bottom: 5px;'/>", unsafe_allow_html=True)
                        except Exception as e:
                            logger.error(f"Failed to render card {card_id}: {str(e)}")
                            st.error(f"Failed to display deviation {card_id}. Please try again.")
        except Exception as e:
            logger.error(f"Failed to render Kanban board: {str(e)}")
            st.error("Failed to display Kanban board. Please try again.")

    # --- 5. Compliance Footer ---
    try:
        auth.display_compliance_footer()
    except Exception as e:
        logger.error(f"Failed to render compliance footer: {str(e)}")
        st.warning("Failed to display compliance footer.")

if __name__ == "__main__":
    main()

