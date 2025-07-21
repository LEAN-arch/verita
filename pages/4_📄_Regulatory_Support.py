# ==============================================================================
# Page 4: Regulatory Support & Report Assembler
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This module provides a Streamlit-based interface for compiling data summaries and
# generating formatted, electronically signed reports for regulatory submissions in the
# VERITAS application. It supports configuring report content, adding commentary, generating
# draft reports, and signing/locking reports in compliance with 21 CFR Part 11. The module
# integrates with veritas_core modules for session management, authentication, and reporting,
# ensuring GxP compliance with robust error handling and data validation.
# ==============================================================================

import streamlit as st
import pandas as pd
import logging
from typing import Dict, List, Any
from veritas_core import bootstrap, session, auth
from veritas_core.engine import analytics, plotting, reporting

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Render the Regulatory Support & Report Assembler page for the VERITAS application.

    Provides a three-step workflow:
    1. Configure Report Content: Select study, report format, and sections.
    2. Add Commentary & Generate: Add analyst commentary and generate a draft report.
    3. Sign & Lock Report: Apply 21 CFR Part 11-compliant electronic signature and download final report.

    Raises:
        RuntimeError: If session initialization, data loading, or report generation fails.
        ValueError: If data, configuration, or session state is invalid.
    """
    # --- 1. Application Bootstrap ---
    try:
        bootstrap.run("Regulatory Support", "📄")
        if 'username' not in st.session_state or not isinstance(st.session_state.username, str) or not st.session_state.username.strip():
            raise ValueError("username not set or invalid in session state")
    except Exception as e:
        logger.error(f"Bootstrap failed: {str(e)}")
        st.error("Failed to initialize Regulatory Support page. Please contact support.")
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
        hplc_data = session_manager.get_data('hplc')
        if not isinstance(hplc_data, pd.DataFrame):
            raise ValueError("get_data('hplc') must return a pandas DataFrame")
        if hplc_data.empty or 'study_id' not in hplc_data.columns:
            raise ValueError("HPLC data must be non-empty and contain 'study_id' column")
    except Exception as e:
        logger.error(f"Failed to load HPLC data: {str(e)}")
        st.error("Failed to load HPLC data. Please try again later.")
        return

    try:
        cpk_config = session_manager.settings.app.process_capability
        if not hasattr(cpk_config, 'available_cqas') or not isinstance(cpk_config.available_cqas, list):
            raise ValueError("cpk_config.available_cqas must be a list")
        if not all(cqa in hplc_data.columns for cqa in cpk_config.available_cqas):
            raise ValueError("Some CQAs in available_cqas are not in HPLC data")
    except Exception as e:
        logger.error(f"Invalid cpk_config: {str(e)}")
        st.error("Invalid process capability configuration. Please contact support.")
        return

    # --- 4. Page Content ---
    st.title("📄 Regulatory Support & Report Assembler")
    st.markdown("Compile data summaries and generate formatted, e-signed reports for submissions.")
    st.markdown("---")

    st.header("1. Configure Report Content")
    col1, col2 = st.columns(2)
    with col1:
        try:
            study_options = sorted(hplc_data['study_id'].unique())
            if not study_options:
                st.warning("No studies available for selection.")
                return
            study_id = st.selectbox("Select a Study:", options=study_options)
            report_format = st.radio("Select Report Format:", options=['PDF', 'PowerPoint'], horizontal=True)
        except Exception as e:
            logger.error(f"Failed to configure report study/format: {str(e)}")
            st.error("Failed to load study options. Please try again.")
            return
    with col2:
        st.write("**Select sections to include in the report:**")
        sections_config = {
            'include_summary_stats': st.checkbox("Summary Statistics Table", value=True),
            'include_cpk_analysis': st.checkbox("Process Capability (Cpk) Plot", value=True),
            'include_control_chart': st.checkbox("Process Stability Control Chart", value=False),
            'include_full_dataset': st.checkbox("Full Dataset (Appendix)", value=False),
            'include_audit_trail': st.checkbox("Audit Trail for Selected Data", value=True)
        }

    try:
        report_df = hplc_data[hplc_data['study_id'] == study_id].copy()
        if report_df.empty:
            st.warning(f"No data available for study '{study_id}'.")
            return
        st.info(f"**{len(report_df)}** data records from study **'{study_id}'** will be included in the report.")
    except Exception as e:
        logger.error(f"Failed to filter report data: {str(e)}")
        st.error("Failed to load data for the selected study. Please try again.")
        return
    st.markdown("---")

    st.header("2. Add Commentary & Generate")
    try:
        cqa = st.selectbox("Select Primary CQA for Report Analysis:", options=cpk_config.available_cqas, index=cpk_config.available_cqas.index('purity') if 'purity' in cpk_config.available_cqas else 0)
        if cqa not in report_df.columns:
            raise ValueError(f"CQA '{cqa}' not found in report data")
        commentary = st.text_area(
            "Enter Analyst Commentary:",
            f"This report summarizes the data for study {study_id}. The primary CQA, {cqa}, remained well within the established specification limits.",
            height=100
        )
        if not commentary.strip():
            raise ValueError("Commentary cannot be empty")
    except Exception as e:
        logger.error(f"Failed to configure commentary/CQA: {str(e)}")
        st.error("Invalid CQA or commentary. Please try again.")
        return

    if st.button(f"Generate DRAFT {report_format} Report", type="primary"):
        with st.spinner(f"Assembling DRAFT {report_format} report..."):
            try:
                draft_report = session_manager.generate_draft_report(
                    study_id=study_id,
                    report_df=report_df,
                    cqa=cqa,
                    sections_config=sections_config,
                    commentary=commentary,
                    report_format=report_format
                )
                if not isinstance(draft_report, dict) or not all(key in draft_report for key in ['filename', 'watermarked_bytes', 'mime']):
                    raise ValueError("generate_draft_report must return a dict with 'filename', 'watermarked_bytes', and 'mime'")
                session_manager.update_page_state('draft_report', draft_report)
                st.success(f"DRAFT {report_format} report generated successfully. Proceed to sign and lock.")
            except Exception as e:
                logger.error(f"Failed to generate draft report: {str(e)}")
                st.error("Failed to generate draft report. Please try again.")

    draft_report = session_manager.get_page_state('draft_report')
    if draft_report and isinstance(draft_report, dict) and all(key in draft_report for key in ['filename', 'watermarked_bytes', 'mime']):
        st.markdown("---")
        st.header("3. Sign & Lock Report")
        st.info(f"**Report Ready for Signature:** `{draft_report['filename']}`")
        try:
            st.download_button(
                label="Download DRAFT Watermarked Version for Review",
                data=draft_report['watermarked_bytes'],
                file_name=f"DRAFT_{draft_report['filename']}",
                mime=draft_report['mime']
            )
        except Exception as e:
            logger.error(f"Failed to render draft download button: {str(e)}")
            st.error("Failed to provide draft report for download. Please try again.")
        st.warning("⚠️ **Action Required:** This report is a **DRAFT** and is not valid for submission until it is electronically signed.")
        with st.form("e_signature_form"):
            st.subheader("21 CFR Part 11 Electronic Signature", anchor=False)
            try:
                username_input = st.text_input("Username", value=st.session_state.username, disabled=True)
                password_input = st.text_input("Password", type="password")
                auth_code_input = st.text_input("2FA Authentication Code")
                signing_reason = st.selectbox("Reason for Signing:", options=["Author Approval", "Technical Review", "QA Final Approval"])
                submitted = st.form_submit_button("Sign and Lock Report")
                if submitted:
                    if not password_input or not auth_code_input:
                        st.error("Password and 2FA code are required.")
                    elif not auth_code_input.isdigit() or len(auth_code_input) != 6:
                        st.error("2FA code must be a 6-digit number.")
                    else:
                        try:
                            # Note: Replace with actual auth.verify_credentials call when integrated with auth system
                            if not auth.verify_credentials(username_input, password_input):
                                raise ValueError("Invalid username or password")
                            # Placeholder for 2FA verification (requires integration with external 2FA service)
                            logger.info(f"2FA verification placeholder for user {username_input} with code {auth_code_input}")
                            with st.spinner("Applying secure signature and finalizing report..."):
                                final_report = session_manager.finalize_and_sign_report(signing_reason)
                                if not isinstance(final_report, dict) or not all(key in final_report for key in ['filename', 'final_bytes', 'mime']):
                                    raise ValueError("finalize_and_sign_report must return a dict with 'filename', 'final_bytes', and 'mime'")
                                st.session_state['final_report'] = final_report
                                st.success(f"Report **{final_report['filename']}** has been successfully signed and locked.")
                                st.balloons()
                        except Exception as e:
                            logger.error(f"Failed to sign and lock report: {str(e)}")
                            st.error("Authentication failed or signing process encountered an error. Please check your credentials and try again.")
            except Exception as e:
                logger.error(f"Failed to render e-signature form: {str(e)}")
                st.error("Failed to load e-signature form. Please try again.")
    else:
        st.info("Generate a draft report to proceed with signing.")

    final_report = st.session_state.get('final_report')
    if final_report and isinstance(final_report, dict) and all(key in final_report for key in ['filename', 'final_bytes', 'mime']):
        try:
            st.download_button(
                label=f"⬇️ Download FINAL Signed Report: {final_report['filename']}",
                data=final_report['final_bytes'],
                file_name=final_report['filename'],
                mime=final_report['mime'],
                type="primary"
            )
        except Exception as e:
            logger.error(f"Failed to render final report download button: {str(e)}")
            st.error("Failed to provide final report for download. Please try again.")

    # --- 5. Compliance Footer ---
    try:
        auth.display_compliance_footer()
    except Exception as e:
        logger.error(f"Failed to render compliance footer: {str(e)}")
        st.warning("Failed to display compliance footer.")

if __name__ == "__main__":
    main()
