# ==============================================================================
# Core Module: Centralized Session State Management
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
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
        if '_singleton_instance' not in st.session_state:
            st.session_state._singleton_instance = self
            self._initialize_backend()

    def _initialize_backend(self):
        """Initializes backend components like settings and data repository once per session."""
        st.session_state.settings = settings
        
        repo_mode = "MOCK"
        
        if repo_mode == "PROD":
            st.session_state.repo = repository.MockDataRepository() # Fallback for demo
        else:
            st.session_state.repo = repository.MockDataRepository()
        
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
        # --- ATTRIBUTE ERROR FIX ---
        # Changed self.settings.APP to self.settings.app to match the corrected settings file.
        st.set_page_config(
            page_title=f"{page_title} - VERITAS", page_icon=page_icon, layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'Get Help': self.settings.app.help_url,
                'About': f"VERITAS, Version {self.settings.app.version}"
            }
        )
        auth.initialize_session_state()
        self._audit_login()
        auth.render_sidebar()

    def initialize_page(self, page_title: str, page_icon: str):
        """Single call to set up any sub-page, encapsulating boilerplate code."""
        auth.page_setup(page_title, page_icon)

    # --- Data Accessors ---
    def get_data(self, data_key: str) -> pd.DataFrame:
        """Safely retrieves a dataframe from the session state."""
        full_key = f"{data_key}_data"
        if full_key not in st.session_state:
            self._initialize_backend()
        return st.session_state.get(full_key, pd.DataFrame())

    # --- State Management for Individual Pages ---
    def get_page_state(self, key: str, default: Any = None) -> Any:
        return st.session_state.get('page_states', {}).get(key, default)
    
    def update_page_state(self, key: str, value: Any):
        if 'page_states' not in st.session_state:
            st.session_state.page_states = {}
        st.session_state.page_states[key] = value

    def clear_page_state(self, key: str):
        if 'page_states' in st.session_state and key in st.session_state.page_states:
            del st.session_state.page_states[key]

    # --- Business Logic & Workflow Methods ---
    def _audit_login(self):
        if not st.session_state.get('login_audited', False):
            self.repo.write_audit_log(
                user=st.session_state.username, action="User Login",
                details=f"User logged in with '{st.session_state.user_role}' role."
            )
            st.session_state.login_audited = True

    def get_user_action_items(self) -> List[Dict]:
        items = []
        if st.session_state.user_role == "QC Analyst":
            new_devs = self.get_data('deviations')
            new_dev_count = len(new_devs[new_devs['status'] == 'New'])
            if new_dev_count > 0:
                items.append({
                    "title": "New Deviations", "details": f"{new_dev_count} require review.",
                    "icon": "📌", "page_link": "pages/5_📌_Deviation_Hub.py"
                })
        return items

    def create_deviation_from_qc(self, report_df: pd.DataFrame, study_id: str) -> str:
        title = f"QC Discrepancies found in Study {study_id}"
        linked_record = f"QC_REPORT_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
        new_dev_id = self.repo.create_deviation(title, linked_record, "High")
        st.session_state.deviations_data = self.repo.get_deviations_data()
        self.repo.write_audit_log(
            user=st.session_state.username, action="Deviation Created",
            details=f"Created {new_dev_id} from QC Integrity Center for {study_id}.",
            record_id=new_dev_id
        )
        return new_dev_id
    
    def advance_deviation_status(self, dev_id: str, current_status: str):
        # --- ATTRIBUTE ERROR FIX ---
        # Changed settings.APP to settings.app
        current_index = self.settings.app.deviation_management.kanban_states.index(current_status)
        new_status = self.settings.app.deviation_management.kanban_states[current_index + 1]
        self.repo.update_deviation_status(dev_id, new_status)
        st.session_state.deviations_data = self.repo.get_deviations_data()
        self.repo.write_audit_log(
            user=st.session_state.username, action="Deviation Status Changed",
            details=f"Status for {dev_id} changed from '{current_status}' to '{new_status}'.",
            record_id=dev_id
        )

    def get_deviation_details(self, dev_id: str) -> pd.DataFrame:
        return self.get_data('deviations')[self.get_data('deviations')['id'] == dev_id]

    def get_signatures_log(self) -> pd.DataFrame:
        audit_log = self.get_data('audit')
        sig_keywords = ['Signature', 'Signed', 'E-Sign']
        sig_mask = audit_log['Action'].str.contains('|'.join(sig_keywords), case=False, na=False)
        return audit_log[sig_mask]
        
    def generate_draft_report(self, **kwargs):
        report_data = kwargs
        cqa = report_data.get('cqa', 'Purity')
        report_data['cqa'] = cqa
        
        # --- ATTRIBUTE ERROR FIX ---
        # Changed settings.APP to settings.app
        spec_limits = self.settings.app.process_capability.spec_limits[cqa]
        cpk_target = self.settings.app.process_capability.cpk_target
        
        report_data['plot_fig'] = plotting.plot_process_capability(
            report_data['report_df'], cqa, 
            spec_limits.lsl, spec_limits.usl,
            analytics.calculate_cpk(report_data['report_df'][cqa], spec_limits.lsl, spec_limits.usl),
            cpk_target
        )

        if report_data['report_format'] == 'PDF':
            watermarked_bytes = reporting.generate_pdf_report(report_data, watermark="DRAFT")
            final_bytes = reporting.generate_pdf_report(report_data)
            filename = f"VERITAS_Summary_{report_data['study_id']}_{cqa}.pdf"
            mime = "application/pdf"
        else: # PowerPoint
            ppt_bytes = reporting.generate_ppt_report(report_data)
            watermarked_bytes = ppt_bytes
            final_bytes = ppt_bytes
            filename = f"VERITAS_PPT_{report_data['study_id']}_{cqa}.pptx"
            mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

        self.update_page_state('draft_report', {
            'filename': filename, 'mime': mime,
            'watermarked_bytes': watermarked_bytes,
            'final_bytes': final_bytes,
            'report_data': report_data
        })

    def finalize_and_sign_report(self, signing_reason: str) -> Dict:
        draft_report = self.get_page_state('draft_report')
        if not draft_report: return {}
        
        final_filename = draft_report['filename'].replace("DRAFT_", "")
        
        signature_details = {
            'user': st.session_state.username,
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'reason': signing_reason
        }
        
        draft_report['report_data']['signature_details'] = signature_details
        final_bytes_with_sig = reporting.generate_pdf_report(draft_report['report_data'])

        self.repo.write_audit_log(
            user=st.session_state.username,
            action="E-Signature Applied",
            details=f"Signed report '{final_filename}' for reason: '{signing_reason}'.",
            record_id=draft_report['report_data']['study_id']
        )
        
        self.clear_page_state('draft_report')
        return {
            'filename': final_filename,
            'final_bytes': final_bytes_with_sig,
            'mime': draft_report['mime']
        }
    
    def get_kpi(self, kpi_name: str) -> Dict:
        if kpi_name == 'active_deviations':
            df = self.get_data('deviations')
            return {'value': len(df[df['status'] != 'Closed']), 'sme_info': "Total open quality events."}
        if kpi_name == 'data_quality_score':
            df = self.get_data('hplc')
            # --- ATTRIBUTE ERROR FIX ---
            # Changed settings.APP to settings.app
            lsl = self.settings.app.process_capability.spec_limits['Purity'].lsl
            score = 100 * (df['Purity'] >= lsl).mean()
            return {'value': score, 'delta': (score-95), 'sme_info': "Percentage of results passing automated integrity checks."}
        if kpi_name == 'first_pass_yield':
            return {'value': 88.2, 'delta': -1.5, 'sme_info': "Percentage of processes completing without deviations."}
        if kpi_name == 'mean_time_to_resolution':
            return {'value': 4.5, 'delta': -0.5, 'sme_info': "Average time to close a deviation."}
        return {'value': 0, 'delta': 0, 'sme_info': 'KPI not implemented.'}
        
    def get_risk_matrix_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "program_id": ["VX-561", "VX-121", "VX-809", "VX-984"],
            "days_to_milestone": [50, 80, 200, 150],
            "dqs": [92, 98, 99, 96],
            "active_deviations": [8, 2, 1, 4],
            "risk_quadrant": ["High Priority", "On Track", "On Track", "Data Risk"]
        })
        
    def get_pareto_data(self) -> pd.DataFrame:
        df = self.get_data('deviations')
        error_data = pd.DataFrame(df['title'].str.extract(r'(OOS|Drift|Breach|Contamination|Missing)')[0].value_counts()).reset_index()
        error_data.columns = ['Error Type', 'Frequency']
        return error_data
        
    def perform_global_search(self, search_term: str) -> List[Dict]:
        results = []
        if self.get_data('stability')['lot_id'].str.contains(search_term, case=False).any():
            results.append({'module': 'Stability', 'id': search_term, 'icon': '⏳', 'page_link': 'pages/3_⏳_Stability_Program.py'})
        return results
