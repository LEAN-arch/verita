import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
try:
    import streamlit as st
except ImportError:
    st = None  # Fallback for non-Streamlit environments
from . import settings, repository, auth
from .engine import analytics, plotting, reporting


class SessionManager:
    """
    Manages session state and business logic for the VERITAS Streamlit application.
    Provides access to settings, repository data, and methods for handling deviations,
    reports, KPIs, and searches.
    """
    def __init__(self):
        """Initialize session state with default values if not already set."""
        if st is not None:
            if 'settings' not in st.session_state:
                st.session_state.settings = settings
            if 'repo' not in st.session_state:
                st.session_state.repo = repository.MockDataRepository()
            if 'page_states' not in st.session_state:
                st.session_state.page_states = {}
            if 'deviations_data' not in st.session_state:
                st.session_state.deviations_data = pd.DataFrame()
            if 'hplc_data' not in st.session_state:
                st.session_state.hplc_data = pd.DataFrame()
            if 'stability_data' not in st.session_state:
                st.session_state.stability_data = pd.DataFrame()
            if 'audit_data' not in st.session_state:
                st.session_state.audit_data = pd.DataFrame()
            if 'username' not in st.session_state:
                st.session_state.username = 'Unknown'
            if 'user_role' not in st.session_state:
                st.session_state.user_role = 'Guest'

    @property
    def settings(self) -> Any:
        """Retrieve application settings from session state.

        Raises:
            KeyError: If settings are not initialized in session state.
        """
        if st is None or 'settings' not in st.session_state:
            raise KeyError("Settings not initialized in session state")
        return st.session_state.settings

    @property
    def repo(self asph: repository.DataRepository:
        """Retrieve the data repository from session state.

        Raises:
            KeyError: If repo is not initialized in session state.
        """
        if st is None or 'repo' not in st.session_state:
            raise KeyError("Repository not initialized in session state")
        return st.session_state.repo

    def get_data(self, key: str) -> pd.DataFrame:
        """
        Retrieve data from session state by key.

        Args:
            key (str): Data key (e.g., 'hplc', 'deviations', 'stability', 'audit').

        Returns:
            pd.DataFrame: DataFrame for the given key, or empty DataFrame if not found.

        Raises:
            ValueError: If key is empty or invalid.
        """
        if not key:
            raise ValueError("Data key must not be empty")
        return st.session_state.get(f"{key}_data", pd.DataFrame())

    def get_page_state(self, key: str, default: Any = None) -> Any:
        """
        Retrieve page state value by key.

        Args:
            key (str): State key.
            default (Any, optional): Default value if key is not found. Defaults to None.

        Returns:
            Any: Value for the given key, or default if not found.

        Raises:
            ValueError: If key is empty.
        """
        if not key:
            raise ValueError("Page state key must not be empty")
        return st.session_state.page_states.get(key, default)

    def update_page_state(self, key: str, value: Any) -> None:
        """
        Update page state with a key-value pair.

        Args:
            key (str): State key.
            value (Any): Value to store.

        Raises:
            ValueError: If key is empty.
        """
        if not key:
            raise ValueError("Page state key must not be empty")
        st.session_state.page_states[key] = value

    def clear_page_state(self, key: str) -> None:
        """
        Clear a page state key.

        Args:
            key (str): State key to clear.

        Raises:
            ValueError: If key is empty.
        """
        if not key:
            raise ValueError("Page state key must not be empty")
        if key in st.session_state.page_states:
            del st.session_state.page_states[key]

    def get_user_action_items(self) -> List[Dict]:
        """
        Retrieve action items for the current user based on their role.

        Returns:
            List[Dict]: List of action item dictionaries with title, details, icon, and page_link.

        Raises:
            KeyError: If user_role or deviations_data is not in session state.
        """
        if st is None or 'user_role' not in st.session_state:
            raise KeyError("User role not initialized in session state")
        items = []
        if st.session_state.user_role == "QC Analyst":
            new_devs = self.get_data('deviations')
            if not new_devs.empty:
                new_dev_count = len(new_devs[new_devs['status'] == 'New'])
                if new_dev_count > 0:
                    items.append({
                        "title": "New Deviations",
                        "details": f"{new_dev_count} require review.",
                        "icon": "📌",
                        "page_link": "pages/5_📌_Deviation_Hub.py"
                    })
        return items

    def create_deviation_from_qc(self, report_df: pd.DataFrame, study_id: str) -> str:
        """
        Create a deviation from QC data.

        Args:
            report_df (pd.DataFrame): Report DataFrame.
            study_id (str): Study ID for the deviation.

        Returns:
            str: ID of the new deviation.

        Raises:
            ValueError: If study_id is empty or report_df is empty.
            KeyError: If username or deviations_data is not in session state.
        """
        if not study_id:
            raise ValueError("Study ID must not be empty")
        if report_df.empty:
            raise ValueError("Report DataFrame must not be empty")
        if st is None or 'username' not in st.session_state:
            raise KeyError("Username not initialized in session state")

        title = f"QC Discrepancies found in Study {study_id}"
        linked_record = f"QC_REPORT_{pd.Timestamp.now(tz='UTC').strftime('%Y%m%d%H%M%S')}"
        new_dev_id = self.repo.create_deviation(title, linked_record, "High")
        st.session_state.deviations_data = self.repo.get_deviations_data()
        self.repo.write_audit_log(
            user=st.session_state.username,
            action="Deviation Created",
            details=f"Created {new_dev_id} from QC Integrity Center for {study_id}.",
            record_id=new_dev_id
        )
        return new_dev_id

    def advance_deviation_status(self, dev_id: str, current_status: str) -> None:
        """
        Advance the status of a deviation to the next state.

        Args:
            dev_id (str): Deviation ID.
            current_status (str): Current status of the deviation.

        Raises:
            ValueError: If dev_id or current_status is empty, or if current_status is invalid or final.
            KeyError: If username, deviations_data, or settings.app.deviation_management.kanban_states is not available.
        """
        if not dev_id or not current_status:
            raise ValueError("Deviation ID and current status must not be empty")
        if st is None or 'username' not in st.session_state:
            raise KeyError("Username not initialized in session state")
        try:
            states = self.settings.app.deviation_management.kanban_states
        except AttributeError:
            raise KeyError("Kanban states not defined in settings")

        if current_status not in states:
            raise ValueError(f"Invalid current status: {current_status}. Must be one of {states}")
        current_index = states.index(current_status)
        if current_index + 1 >= len(states):
            raise ValueError(f"Cannot advance status: {current_status} is the final state")

        new_status = states[current_index + 1]
        self.repo.update_deviation_status(dev_id, new_status)
        st.session_state.deviations_data = self.repo.get_deviations_data()
        self.repo.write_audit_log(
            user=st.session_state.username,
            action="Deviation Status Changed",
            details=f"Status for {dev_id} changed from '{current_status}' to '{new_status}'.",
            record_id=dev_id
        )

    def get_deviation_details(self, dev_id: str) -> pd.DataFrame:
        """
        Retrieve details for a specific deviation.

        Args:
            dev_id (str): Deviation ID.

        Returns:
            pd.DataFrame: DataFrame containing the deviation details, or empty DataFrame with columns if not found.

        Raises:
            ValueError: If dev_id is empty.
            KeyError: If deviations_data is not in session state.
        """
        if not dev_id:
            raise ValueError("Deviation ID must not be empty")
        deviations = self.get_data('deviations')
        if deviations.empty:
            return pd.DataFrame(columns=['id', 'title', 'status', 'priority', 'linked_record'])
        result = deviations[deviations['id'] == dev_id]
        return result if not result.empty else pd.DataFrame(columns=deviations.columns)

    def get_signatures_log(self) -> pd.DataFrame:
        """
        Retrieve audit log entries related to signatures.

        Returns:
            pd.DataFrame: DataFrame of signature-related audit log entries.

        Raises:
            KeyError: If audit_data is not in session state.
        """
        audit_log = self.get_data('audit')
        if audit_log.empty:
            return pd.DataFrame(columns=['timestamp', 'user', 'action', 'record_id', 'details'])
        sig_keywords = ['Signature', 'Signed', 'E-Sign']
        mask = audit_log['action'].str.contains('|'.join(sig_keywords), case=False, na=False)
        return audit_log[mask]

    def generate_draft_report(self, **kwargs: Any) -> None:
        """
        Generate a draft report in PDF or PPT format.

        Args:
            **kwargs: Report parameters including report_df, study_id, report_format, cqa.

        Raises:
            ValueError: If required kwargs are missing or invalid.
            KeyError: If required settings or session state keys are missing.
        """
        required_keys = ['report_df', 'study_id', 'report_format']
        if not all(key in kwargs for key in required_keys):
            raise ValueError(f"Missing required kwargs: {required_keys}")
        if kwargs['report_df'].empty:
            raise ValueError("Report DataFrame must not be empty")
        if kwargs['report_format'] not in ['PDF', 'PPT']:
            raise ValueError("Report format must be 'PDF' or 'PPT'")
        try:
            specs = self.settings.app.process_capability.spec_limits
            cpk_target = self.settings.app.process_capability.cpk_target
        except AttributeError:
            raise KeyError("Process capability settings not defined")

        report_data = kwargs
        cqa = report_data.get('cqa', 'purity')
        if cqa not in specs:
            raise ValueError(f"Invalid CQA: {cqa}. Must be one of {list(specs.keys())}")
        report_data['cqa'] = cqa
        report_data['data'] = report_data['report_df']
        report_data['plot_fig'] = plotting.plot_process_capability(
            report_data['report_df'], cqa, specs[cqa].lsl, specs[cqa].usl,
            analytics.calculate_cpk(report_data['report_df'][cqa], specs[cqa].lsl, specs[cqa].usl), cpk_target
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
            'filename': filename,
            'mime': mime,
            'watermarked_bytes': bytes_,
            'report_data': report_data
        })

    def finalize_and_sign_report(self, signing_reason: str) -> Dict:
        """
        Finalize and sign a draft report.

        Args:
            signing_reason (str): Reason for signing the report.

        Returns:
            Dict: Dictionary with filename, final_bytes, and mime type of the signed report.

        Raises:
            ValueError: If signing_reason is empty.
            KeyError: If draft_report or username is not in session state.
        """
        if not signing_reason:
            raise ValueError("Signing reason must not be empty")
        if st is None or 'username' not in st.session_state:
            raise KeyError("Username not initialized in session state")
        draft_report = self.get_page_state('draft_report')
        if not draft_report:
            return {}

        final_filename = draft_report['filename'].replace("DRAFT_", "")
        signature_details = {
            'user': st.session_state.username,
            'timestamp': pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M:%S UTC'),
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
        """
        Retrieve KPI data by name.

        Args:
            kpi_name (str): Name of the KPI (e.g., 'active_deviations', 'data_quality_score').

        Returns:
            Dict: Dictionary with value, delta, and SME info for the KPI.

        Raises:
            ValueError: If kpi_name is empty or invalid.
            KeyError: If required data or settings are not in session state.
        """
        valid_kpis = ['active_deviations', 'data_quality_score', 'first_pass_yield', 'mean_time_to_resolution']
        if not kpi_name:
            raise ValueError("KPI name must not be empty")
        if kpi_name not in valid_kpis:
            raise ValueError(f"Invalid KPI name: {kpi_name}. Must be one of {valid_kpis}")

        if kpi_name == 'active_deviations':
            df = self.get_data('deviations')
            return {'value': len(df[df['status'] != 'Closed']) if not df.empty else 0,
                    'sme_info': "Total open quality events."}
        if kpi_name == 'data_quality_score':
            try:
                lsl = self.settings.app.process_capability.spec_limits['purity'].lsl
            except AttributeError:
                raise KeyError("Process capability settings not defined")
            df = self.get_data('hplc')
            score = 100 * (df['purity'] >= lsl).mean() if not df.empty else 0
            return {'value': score, 'delta': score - 98.5, 'sme_info': "Percentage of results passing automated integrity checks. Target: 98.5%"}
        if kpi_name == 'first_pass_yield':
            return {'value': 92.1, 'delta': 2.1, 'sme_info': "Percentage of processes completing without deviations. Target: 90%"}
        if kpi_name == 'mean_time_to_resolution':
            return {'value': 4.5, 'delta': -0.5, 'sme_info': "Average business days to close a deviation. Target: 5 days"}
        return {'value': 0, 'delta': 0, 'sme_info': 'KPI not implemented.'}

    def get_risk_matrix_data(self) -> pd.DataFrame:
        """
        Retrieve risk matrix data (temporary hardcoded implementation).

        Returns:
            pd.DataFrame: DataFrame with program risk data.
        """
        # TODO: Replace with dynamic data from repository
        return pd.DataFrame({
            "program_id": ["VX-561", "VX-121", "VX-809", "VX-984"],
            "days_to_milestone": [50, 80, 200, 150],
            "dqs": [92, 98, 99, 96],
            "active_deviations": [8, 2, 1, 4],
            "risk_quadrant": ["High Priority", "On Track", "On Track", "Data Risk"]
        })

    def get_pareto_data(self) -> pd.DataFrame:
        """
        Retrieve Pareto data for deviation error types.

        Returns:
            pd.DataFrame: DataFrame with error type frequencies.

        Raises:
            KeyError: If deviations_data is not in session state.
        """
        df = self.get_data('deviations')
        if df.empty:
            return pd.DataFrame(columns=['Error Type', 'Frequency'])
        error_data = pd.DataFrame(
            df['title'].str.extract(r'(OOS|Drift|Breach|Contamination|Missing)')[0]
            .value_counts()
            .reset_index()
        )
        error_data.columns = ['Error Type', 'Frequency']
        error_data = error_data.dropna()  # Remove NaN error types
        return error_data

    def perform_global_search(self, search_term: str) -> List[Dict]:
        """
        Perform a global search across stability and deviations data.

        Args:
            search_term (str): Term to search for.

        Returns:
            List[Dict]: List of search result dictionaries with module, id, icon, and page_link.

        Raises:
            ValueError: If search_term is empty.
        """
        if not search_term:
            raise ValueError("Search term must not be empty")
        results = []
        stability_data = self.get_data('stability')
        if not stability_data.empty and stability_data['lot_id'].str.contains(search_term, case=False, na=False).any():
            results.append({
                'module': 'Stability',
                'id': search_term,
                'icon': '⏳',
                'page_link': 'pages/3_⏳_Stability_Program.py'
            })
        deviations_data = self.get_data('deviations')
        if not deviations_data.empty and deviations_data['id'].str.contains(search_term, case=False, na=False).any():
            results.append({
                'module': 'Deviations',
                'id': search_term,
                'icon': '📌',
                'page_link': 'pages/5_📌_Deviation_Hub.py'
            })
        return results

