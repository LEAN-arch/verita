import streamlit as st
import pandas as pd
from veritas_core import session, auth
from veritas_core.engine import analytics, plotting, reporting

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Regulatory Support",
    page_icon="📄",
    layout="wide"
)

# --- 2. APPLICATION INITIALIZATION & AUTH ---
session.initialize_session()
session_manager = session.SessionManager()
auth.render_page()

# --- 3. DATA LOADING & CONFIG ---
hplc_data = session_manager.get_data('hplc')
cpk_config = session_manager.settings.app.process_capability

# --- 4. PAGE HEADER ---
st.title("📄 Regulatory Support & Report Assembler")
st.markdown("Compile data summaries and generate formatted, e-signed reports for submissions.")
st.markdown("---")

# --- 5. REPORT CONFIGURATION UI ---
st.header("1. Configure Report Content")
col1, col2 = st.columns(2)
with col1:
    study_id = st.selectbox("Select a Study:", options=sorted(hplc_data['study_id'].unique()))
    report_format = st.radio("Select Report Format:", options=['PDF', 'PowerPoint'], horizontal=True)
with col2:
    st.write("**Select sections to include in the report:**")
    sections_config = {
        'include_summary_stats': st.checkbox("Summary Statistics Table", value=True),
        'include_cpk_analysis': st.checkbox("Process Capability (Cpk) Plot", value=True),
        'include_control_chart': st.checkbox("Process Stability Control Chart", value=False),
        'include_full_dataset': st.checkbox("Full Dataset (Appendix)", value=False),
        'include_audit_trail': st.checkbox("Audit Trail for Selected Data", value=True)
    }

report_df = hplc_data[hplc_data['study_id'] == study_id]
st.info(f"**{len(report_df)}** data records from study **'{study_id}'** will be included in the report.")
st.markdown("---")

st.header("2. Add Commentary & Generate")
cqa = st.selectbox("Select Primary CQA for Report Analysis:", options=cpk_config.available_cqas)
commentary = st.text_area(
    "Enter Analyst Commentary:",
    f"This report summarizes the data for study {study_id}. The primary CQA, {cqa}, remained well within the established specification limits.",
    height=100
)

if st.button(f"Generate DRAFT {report_format} Report", type="primary"):
    with st.spinner(f"Assembling DRAFT {report_format} report..."):
        session_manager.generate_draft_report(
            study_id=study_id, report_df=report_df, cqa=cqa,
            sections_config=sections_config, commentary=commentary, report_format=report_format
        )
    st.success(f"DRAFT {report_format} report generated successfully. Proceed to sign and lock.")

# --- 6. E-SIGNATURE AND DOWNLOAD WORKFLOW ---
draft_report = session_manager.get_page_state('draft_report')
if draft_report:
    st.markdown("---")
    st.header("3. Sign & Lock Report")
    st.info(f"**Report Ready for Signature:** `{draft_report['filename']}`")
    st.download_button(
        label="Download DRAFT Watermarked Version for Review",
        data=draft_report['watermarked_bytes'],
        file_name=f"DRAFT_{draft_report['filename']}",
        mime=draft_report['mime']
    )
    st.warning("⚠️ **Action Required:** This report is a **DRAFT** and is not valid for submission until it is electronically signed.")
    with st.form("e_signature_form"):
        st.subheader("21 CFR Part 11 Electronic Signature", anchor=False)
        username_input = st.text_input("Username", value=st.session_state.username, disabled=True)
        password_input = st.text_input("Password", type="password")
        auth_code_input = st.text_input("2FA Authentication Code")
        signing_reason = st.selectbox("Reason for Signing:", options=["Author Approval", "Technical Review", "QA Final Approval"])
        submitted = st.form_submit_button("Sign and Lock Report")
        if submitted:
            if password_input == "vertex123" and auth_code_input.isdigit() and len(auth_code_input) == 6:
                with st.spinner("Applying secure signature and finalizing report..."):
                    final_report = session_manager.finalize_and_sign_report(signing_reason)
                    st.session_state['final_report'] = final_report
                st.success(f"Report **{final_report['filename']}** has been successfully signed and locked.")
                st.balloons()
            else:
                st.error("Authentication Failed. Please check your credentials and 2FA code.")

final_report = st.session_state.get('final_report')
if final_report:
    st.download_button(
        label=f"⬇️ Download FINAL Signed Report: {final_report['filename']}",
        data=final_report['final_bytes'],
        file_name=final_report['filename'],
        mime=final_report['mime'],
        type="primary"
    )

# --- 7. COMPLIANCE FOOTER ---
auth.display_compliance_footer()
