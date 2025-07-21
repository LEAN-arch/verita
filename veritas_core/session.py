# ==============================================================================
# Core Module: Centralized Session State Management
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Ultimate Version)
#
# Description:
# This module provides a SessionManager class that acts as a centralized
# controller for the entire application. It encapsulates all interactions with
# Streamlit's `st.session_state`, providing a clean, predictable, and robust
# interface for the UI pages to use.
#
# Architectural Pattern:
# This class implements a form of the Controller pattern from MVC, orchestrating
# the flow of data from the repository (Model) to the Streamlit pages (View).
# ==============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

# Import other core components using relative imports
from . import settings, repository, auth
from .engine import analytics, plotting, reporting

class SessionManager:
    """A singleton-like class to manage the application's session state."""

    def __init__(self):
        # The key '_singleton_instance' ensures that the expensive parts
        # of initialization happen only once per session.
        if '_singleton_instance' not in st.session_state:
            st.session_state._singleton_instance = self
            self._initialize_backend()

    def _initialize_backend(self):
        """Initializes backend components like settings and data repository once per session."""
        st.session_state.settings = settings
        
        # This is the key switch between mock and production data.
        # In a real deployment, an environment variable would set this to 'PROD'.
        repo_mode = "MOCK" # or "PROD"
        
        if repo_mode == "PROD":
            # This would pull credentials from st.secrets
            # conn_params = st.secrets['database']
            # st.session_state.repo = repository.ProdDataRepository(conn_params)
            # For now, we fall back to mock if prod isn't fully set up.
            st.session_state.repo = repository.MockDataRepository()
        else:
            st.session_state.repo = repository.MockDataRepository()
        
        # Load all data into the session state once
        st.session_state.data_loaded = True
        st.session_state.hplc_data = st.session_state.repo.get_hplc_data()
        st.session_state.deviations_data = st.session_state.repo.get_deviations_data()
        st.session_state.stability_data = st.session_state.repo.get_stability_data()
        st.session_state.audit_data = st.session_state.repo.get_audit_log()
        
    @property
    def settings(self):
        return st.session_state.settings

    @property
    def repo(self) -> repository.DataRepository:
        return st.session_state.repo
    
    # --- Page Initialization & Setup ---
    def initialize_app(self, page_title: str, page_icon: str):
        """Main initializer for the home page."""
        st.set_page_config(
            page_title=f"{page_title} - VERITAS", page_icon=page_icon, layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': self.settings.APP.help_url,
                'About': f"VERITAS, Version {self.settings.APP.version}"
            }
        )
        auth.initialize_session_state()
        auth.render_sidebar()
        self._audit_login()

    def initialize_page(self, page_title: str, page_icon: str):
        """Single call to set up any sub-page, encapsulating boilerplate code."""
        auth.page_setup(page_title, page_icon)

    # --- Data Accessors ---
    def get_data(self, data_key: str) -> pd.DataFrame:
        """Safely retrieves a dataframe from the session state."""
        return st.session_state.get(f"{data_key}_data", pd.DataFrame())

    # --- State Management for Individual Pages ---
    def get_page_state(self, key: str, default: Any = None) -> Any:
        """Gets a value from the page-specific state dictionary."""
        return st.session_state.get('page_states', {}).get(key, default)
    
    def update_page_state(self, key: str, value: Any):
        """Updates a value in the page-specific state dictionary."""
        if 'page_states' not in st.session_state:
            st.session_state.page_states = {}
        st.session_state.page_states[key] = value

    def clear_page_state(self, key: str):
        """Removes a key from the page-specific state dictionary."""
        if 'page_states' in st.session_state and key in st.session_state.page_states:
            del st.session_state.page_states[key]

    # --- Business Logic & Workflow Methods ---
    def _audit_login(self):
        """Writes a login event to the audit log once per session."""
        if not st.session_state.get('login_audited', False):
            self.repo.write_audit_log(
                user=st.session_state.username, action="User Login",
                details=f"User logged in with '{st.session_state.user_role}' role."
            )
            st.session_state.login_audited = True

    def get_user_action_items(self) -> List[Dict]:
        """Gets a personalized list of action items for the user."""
        items = []
        # In a real app, this would query a database for items assigned to the user.
        # Here we simulate it based on their role.
        if st.session_state.user_role == "QC Analyst":
            new_devs = self.get_data('deviations')
            new_dev_count = len(new_devs[new_devs['status'] == 'New'])
            if new_dev_count > 0:
                items.append({
                    "title": "New Deviations", "details": f"{new_dev_count} require review.",
                    "icon": "📌", "page_link": "pages/5_📌_Deviation_Hub.py"
                })
        # Add more logic for other roles...
        return items

    def create_deviation_from_qc(self, report_df: pd.DataFrame, study_id: str) -> str:
        """Orchestrates creating a deviation from a QC report."""
        title = f"QC Discrepancies found in Study {study_id}"
        linked_record = f"QC_REPORT_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
        new_dev_id = self.repo.create_deviation(title, linked_record, "High")
        st.session_state.deviations_data = self.repo.get_deviations_data() # Refresh data
        self.repo.write_audit_log(
            user=st.session_state.username, action="Deviation Created",
            details=f"Created {new_dev_id} from QC Integrity Center for {study_id}.",
            record_id=new_dev_id
        )
        return new_dev_id
    
    def advance_deviation_status(self, dev_id: str, current_status: str):
        """Orchestrates advancing a deviation's status."""
        current_index = self.settings.APP.deviation_management.kanban_states.index(current_status)
        new_status = self.settings.APP.deviation_management.kanban_states[current_index + 1]
        self.repo.update_deviation_status(dev_id, new_status)
        st.session_state.deviations_data = self.repo.get_deviations_data() # Refresh data
        self.repo.write_audit_log(
            user=st.session_state.username, action="Deviation Status Changed",
            details=f"Status for {dev_id} changed from '{current_status}' to '{new_status}'.",
            record_id=dev_id
        )

    def get_deviation_details(self, dev_id: str) -> pd.DataFrame:
        """Retrieves details for a single deviation."""
        return self.get_data('deviations')[self.get_data('deviations')['id'] == dev_id]

    def get_signatures_log(self) -> pd.DataFrame:
        """Gets a filtered view of the audit log for e-signature events."""
        audit_log = self.get_data('audit')
        sig_keywords = ['Signature', 'Signed', 'E-Sign']
        sig_mask = audit_log['Action'].str.contains('|'.join(sig_keywords), case=False, na=False)
        return audit_log[sig_mask]
        
    def generate_draft_report(self, **kwargs):
        """Orchestrates generating a DRAFT report and storing it in state."""
        report_data = kwargs
        cqa = report_data.get('cqa', 'Purity')
        report_data['cqa'] = cqa # Ensure it's in the dict
        
        # Add necessary plot figure to the data payload
        report_data['plot_fig'] = plotting.plot_spc_chart(report_data['report_df'], cqa)

        if report_data['report_format'] == 'PDF':
            watermarked_bytes = reporting.generate_pdf_report(report_data, watermark="DRAFT")
            final_bytes = reporting.generate_pdf_report(report_data) # Clean version for later
            filename = f"VERITAS_Summary_{report_data['study_id']}_{cqa}.pdf"
            mime = "application/pdf"
        else: # PowerPoint
            # PPTX generation doesn't have an easy watermark, so we'll use the same bytes
            ppt_bytes = reporting.generate_ppt_report(report_data)
            watermarked_bytes = ppt_bytes
            final_bytes = ppt_bytes
            filename = f"VERITAS_PPT_{report_data['study_id']}_{cqa}.pptx"
            mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

        self.update_page_state('draft_report', {
            'filename': filename, 'mime': mime,
            'watermarked_bytes': watermarked_bytes,
            'final_bytes': final_bytes,
            'report_data': report_data # Store the data payload for finalization
        })

    def finalize_and_sign_report(self, signing_reason: str) -> Dict:
        """Finalizes a report after successful e-signature."""
        draft_report = self.get_page_state('draft_report')
        if not draft_report: return {}
        
        # In a real system, you'd add a signature page or metadata to the final bytes.
        # For now, we'll just use the clean version we already generated.
        
        final_filename = draft_report['filename'].replace("DRAFT_", "")
        
        signature_details = {
            'user': st.session_state.username,
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'reason': signing_reason
        }
        
        # Add signature details to the report data payload before logging
        draft_report['report_data']['signature_details'] = signature_details

        self.repo.write_audit_log(
            user=st.session_state.username,
            action="E-Signature Applied",
            details=f"Signed report '{final_filename}' for reason: '{signing_reason}'.",
            record_id=draft_report['report_data']['study_id']
        )
        
        # Clear the draft and return the final payload for download
        self.clear_page_state('draft_report')
        return {
            'filename': final_filename,
            'final_bytes': draft_report['final_bytes'],
            'mime': draft_report['mime']
        }
    
    # Placeholder methods for other business logic to be added later
    def get_kpi(self, kpi_name: str) -> Dict:
        # This would contain the business logic for calculating KPIs
        if kpi_name == 'active_deviations':
            df = self.get_data('deviations')
            return {
                'value': len(df[df['status'] != 'Closed']),
                'sme_info': "Total number of open quality events. A direct measure of the current problem-solving burden."
            }
        # Add other KPIs here...
        return {'value': 0, 'delta': 0, 'sme_info': 'KPI not implemented.'}
        
    def get_risk_matrix_data(self) -> pd.DataFrame:
        # In a real app, this would come from a project management system
        return pd.DataFrame()

    def get_pareto_data(self) -> pd.DataFrame:
        return pd.DataFrame()
        
    def perform_global_search(self, search_term: str) -> List[Dict]:
        return []
