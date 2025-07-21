# ==============================================================================
# Core Module: Centralized Session State Management (Ultimate Version)
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
#
# Description:
# This module provides a fail-safe functional initializer and a lightweight
# SessionManager class to act as the central controller for the application.
# This revised architecture eliminates all previously identified race conditions
# and ensures a robust, predictable state for all UI pages.
# ==============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

# Import other core components using relative imports
from . import settings, repository, auth
from .engine import analytics, plotting, reporting


def initialize_session():
    """
    Definitive, fail-safe session state initializer.
    This function is called ONCE from the home page and guarantees that all
    backend components and data are loaded into st.session_state before any
    other page or module can access them. This resolves all race conditions.
    """
    if 'veritas_initialized' in st.session_state:
        return

    st.session_state.settings = settings
    st.session_state.repo = repository.MockDataRepository()
    
    st.session_state.hplc_data = st.session_state.repo.get_hplc_data()
    st.session_state.deviations_data = st.session_state.repo.get_deviations_data()
    st.session_state.stability_data = st.session_state.repo.get_stability_data()
    st.session_state.audit_data = st.session_state.repo.get_audit_log()
    
    st.session_state.page_states = {}
    auth.initialize_auth_state()

    if not st.session_state.get('login_audited', False):
        st.session_state.repo.write_audit_log(
            user=st.session_state.username, action="User Login",
            details=f"User logged in with '{st.session_state.user_role}' role."
        )
        st.session_state.login_audited = True

    st.session_state.veritas_initialized = True
    print("VERITAS Session Initialized Successfully.")


class SessionManager:
    """
    A lightweight accessor and controller class for the now-robust session state.
    It provides a clean, consistent interface for UI pages to interact with
    the application's state and backend logic.
    """
    @property
    def settings(self): return st.session_state.settings
    @property
    def repo(self) -> repository.DataRepository: return st.session_state.repo
    
    def get_data(self, key: str) -> pd.DataFrame:
        return st.session_state.get(f"{key}_data", pd.DataFrame())

    def get_page_state(self, key: str, default: Any = None) -> Any:
        return st.session_state.page_states.get(key, default)
    
    def update_page_state(self, key: str, value: Any):
        st.session_state.page_states[key] = value

    def clear_page_state(self, key: str):
        if key in st.session_state.page_states:
            del st.session_state.page_states[key]

    # --- Business Logic & Workflow Methods ---
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
            details=f"Created {new_dev_id} from QC Integrity Center for {study_id}.", record_id=new_dev_id
        )
        return new_dev_id
    
    def advance_deviation_status(self, dev_id: str, current_status: str):
        states = self.settings.app.deviation_management.kanban_states
        current_index = states.index(current_status)
        new_status = states[current_index + 1]
        self.repo.update_deviation_status(dev_id, new_status)
        st.session_state.deviations_data = self.repo.get_deviations_data()
        self.repo.write_audit_log(
            user=st.session_state.username, action="Deviation Status Changed",
            details=f"Status for {dev_id} changed from '{current_status}' to '{new_status}'.", record_id=dev_id
        )

    def get_deviation_details(self, dev_id: str) -> pd.DataFrame:
        return self.get_data('deviations')[self.get_data('deviations')['id'] == dev_id]

    def get_signatures_log(self) -> pd.DataFrame:
        audit_log = self.get_data('audit')
        sig_keywords = ['Signature', 'Signed', 'E-Sign']
        mask = audit_log['Action'].str.contains('|'.join(sig_keywords), case=False, na=False)
        return audit_log[mask]
        
    def generate_draft_report(self, **kwargs):
        report_data = kwargs
        cqa = report_data.get('cqa', 'Purity')
        report_data['cqa'] = cqa
        report_data['data'] = report_data['report_df']
        
        specs = self.settings.app.process_capability.spec_limits[cqa]
        cpk_target = self.settings.app.process_capability.cpk_target
        
        report_data['plot_fig'] = plotting.plot_process_capability(
            report_data['report_df'], cqa, specs.lsl, specs.usl,
            analytics.calculate_cpk(report_data['report_df'][cqa], specs.lsl, specs.usl), cpk_target
        )
        if report_data['report_format'] == 'PDF':
            bytes_ = reporting.generate_pdf_report(report_data, watermark="DRAFT")
            filename = f"VERITAS_Summary_{report_data['study_id']}_{cqa}.pdf"
            mime = "application/pdf"
        else:
            bytes_ = reporting.generate_ppt_report(report_data)
            filename = f"VERITAS_PPT_{report_data['study_id']}_{cqa}.pptx"
            mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

        self.update_page_state('draft_report', {
            'filename': filename, 'mime': mime, 'watermarked_bytes': bytes_, 'report_data': report_data
        })

    def finalize_and_sign_report(self, signing_reason: str) -> Dict:
        draft_report = self.get_page_state('draft_report')
        if not draft_report: return {}
        
        final_filename = draft_report['filename'].replace("DRAFT_", "")
        signature_details = {'user': st.session_state.username, 'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S UTC'), 'reason': signing_reason}
        draft_report['report_data']['signature_details'] = signature_details
        final_bytes_with_sig = reporting.generate_pdf_report(draft_report['report_data'])

        self.repo.write_audit_log(
            user=st.session_state.username, action="E-Signature Applied",
            details=f"Signed report '{final_filename}' for reason: '{signing_reason}'.", record_id=draft_report['report_data']['study_id']
        )
        self.clear_page_state('draft_report')
        return {'filename': final_filename, 'final_bytes': final_bytes_with_sig, 'mime': draft_report['mime']}

    def get_kpi(self, kpi_name: str) -> Dict:
        if kpi_name == 'active_deviations':
            df = self.get_data('deviations')
            return {'value': len(df[df['status'] != 'Closed']), 'sme_info': "Total open quality events."}
        if kpi_name == 'data_quality_score':
            df = self.get_data('hplc')
            lsl = self.settings.app.process_capability.spec_limits['Purity'].lsl
            score = 100 * (df['Purity'] >= lsl).mean()
            return {'value': score, 'delta': (score-98.5), 'sme_info': "Percentage of results passing automated integrity checks. Target: 98.5%"}
        if kpi_name == 'first_pass_yield': return {'value': 92.1, 'delta': 2.1, 'sme_info': "Percentage of processes completing without deviations. Target: 90%"}
        if kpi_name == 'mean_time_to_resolution': return {'value': 4.5, 'delta': -0.5, 'sme_info': "Average business days to close a deviation. Target: 5 days"}
        return {'value': 0, 'delta': 0, 'sme_info': 'KPI not implemented.'}
        
    def get_risk_matrix_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            "program_id": ["VX-561", "VX-121", "VX-809", "VX-984"], "days_to_milestone": [50, 80, 200, 150],
            "dqs": [92, 98, 99, 96], "active_deviations": [8, 2, 1, 4],
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
        if self.get_data('deviations')['id'].str.contains(search_term, case=False).any():
            results.append({'module': 'Deviations', 'id': search_term, 'icon': '📌', 'page_link': 'pages/5_📌_Deviation_Hub.py'})
        return results
