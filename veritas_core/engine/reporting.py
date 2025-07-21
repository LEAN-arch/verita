# ==============================================================================
# Core Engine: Compliant Report Generation
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Ultimate Version)
#
# Description:
# This module is the centralized engine for generating GxP-compliant,
# submission-ready reports in various formats (PDF, PowerPoint). It is designed
# for robustness, flexibility, and adherence to data integrity principles.
#
# Key Features:
# - Dynamic Content Assembly: Reports are built based on a configuration dict,
#   allowing for bespoke data packages.
# - GxP Watermarking: The PDF engine supports a "DRAFT" watermark for review
#   copies, a critical feature for document control.
# - E-Signature Placeholder: The final PDF includes a dedicated, formatted
#   section to record electronic signature details.
# ==============================================================================

import io
import pandas as pd
from datetime import datetime
from fpdf import FPDF
from pptx import Presentation
from pptx.util import Inches, Pt
import plotly.graph_objects as go
from typing import Dict, Any

# --- PDF Generation Engine ---

class VeritasPDF(FPDF):
    """Custom FPDF class with VERITAS branding, headers, footers, and watermarking."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.watermark_text = ""

    def set_watermark(self, text):
        self.watermark_text = text

    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'VERITAS - Automated Data Summary Report', 0, 1, 'C')
        self.set_font('Helvetica', '', 8)
        self.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        self.set_x(-50)
        self.cell(0, 10, 'VERTEX CONFIDENTIAL', 0, 0, 'R')

    def _add_watermark(self):
        if self.watermark_text:
            self.set_font('Helvetica', 'B', 50)
            self.set_text_color(220, 220, 220)
            self.rotate(45)
            self.text(35, 190, self.watermark_text)
            self.rotate(0)
            self.set_text_color(0, 0, 0)

    def add_page(self, orientation=''):
        super().add_page(orientation)
        self._add_watermark()

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, title, 0, 1, 'L', fill=True)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Helvetica', '', 10)
        self.multi_cell(0, 5, body)
        self.ln()

    def add_dataframe(self, df: pd.DataFrame, title: str):
        if df.empty: return
        self.set_font('Helvetica', 'B', 9)
        # Dynamic column width calculation
        effective_width = self.w - 2 * self.l_margin
        num_cols = len(df.columns)
        
        # Heuristic for width: give more space to wider columns
        col_widths = {col: (df[col].astype(str).str.len().max()) for col in df.columns}
        total_chars = sum(col_widths.values())
        col_width_props = {col: (width / total_chars) * effective_width for col, width in col_widths.items()}

        for col in df.columns:
            self.cell(col_width_props[col], 7, col, 1, 0, 'C')
        self.ln()
        
        self.set_font('Helvetica', '', 8)
        for _, row in df.iterrows():
            for col in df.columns:
                self.cell(col_width_props[col], 6, str(row[col]), 1, 0, 'L')
            self.ln()
        self.ln(5)
        
    def add_signature_section(self, signature_details: Dict):
        self.chapter_title("4.0 Electronic Signature")
        sig_body = (f"This document was electronically signed and locked in the VERITAS system, "
                    f"in accordance with 21 CFR Part 11 requirements.\n\n"
                    f"**Signed By:** {signature_details['user']}\n"
                    f"**Signature Timestamp:** {signature_details['timestamp']}\n"
                    f"**Meaning of Signature:** {signature_details['reason']}")
        self.chapter_body(sig_body)


def generate_pdf_report(report_data: Dict[str, Any], watermark: str = "") -> bytes:
    """Creates a formatted PDF report from the provided data."""
    pdf = VeritasPDF()
    if watermark:
        pdf.set_watermark(watermark)
    pdf.add_page()
    
    # Section 1: Metadata
    pdf.chapter_title(f"1.0 Summary for Study: {report_data['study_id']}")
    pdf.chapter_body(f"**Analyst Commentary:** {report_data['commentary']}")
    
    # Section 2: Dynamically add content based on config
    pdf.chapter_title("2.0 Data & Analysis")
    if report_data['sections_config']['include_summary_stats']:
        summary_stats = report_data['data'][report_data['cqa']].describe().round(3).reset_index()
        summary_stats.columns = ['Statistic', 'Value']
        pdf.add_dataframe(summary_stats, "Summary Statistics")
    
    # Placeholder for adding plots (requires saving to temp file, more complex)
    # if report_data['sections_config']['include_cpk_analysis']:
    #     pdf.chapter_body("Process Capability Plot would be embedded here.")

    if report_data['sections_config']['include_full_dataset']:
        pdf.add_page()
        pdf.chapter_title("3.0 Appendix: Full Dataset")
        pdf.add_dataframe(report_data['data'], "Full Dataset")

    # Final section: Signature (if provided)
    if report_data.get('signature_details'):
        pdf.add_signature_section(report_data['signature_details'])

    return pdf.output(dest='S').encode('latin-1')


# --- PowerPoint Generation Engine ---
def _add_table_to_slide(slide, df: pd.DataFrame, left, top, width, height):
    """Helper to add a pandas DataFrame to a PowerPoint slide."""
    rows, cols = df.shape
    rows += 1
    table = slide.shapes.add_table(rows, cols, left, top, width, height).table
    for i in range(cols): table.columns[i].width = Inches(width.inches / cols)
    for c, col in enumerate(df.columns):
        table.cell(0, c).text = str(col)
    for r, row in enumerate(df.itertuples(index=False)):
        for c, val in enumerate(row):
            table.cell(r + 1, c).text = str(val) if pd.notna(val) else ""

def generate_ppt_report(report_data: Dict[str, Any]) -> bytes:
    """Generates a PowerPoint report with data and plots."""
    prs = Presentation()
    
    # Slide 1: Title
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "VERITAS Automated Study Report"
    slide.placeholders[1].text = f"Study: {report_data['study_id']}\nGenerated: {datetime.now().strftime('%Y-%m-%d')}"
    
    # Slide 2: Data Summary
    if report_data['sections_config']['include_summary_stats']:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = "Summary Statistics"
        summary_stats = report_data['data'][report_data['cqa']].describe().round(3).reset_index()
        _add_table_to_slide(slide, summary_stats, Inches(1), Inches(1.5), Inches(8), Inches(3))

    # Slide 3: Plot
    if report_data['plot_fig']:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = report_data['plot_fig'].layout.title.text or "Analysis Chart"
        img_stream = io.BytesIO()
        report_data['plot_fig'].write_image(img_stream, format="png", width=800, height=450, scale=2)
        img_stream.seek(0)
        slide.shapes.add_picture(img_stream, Inches(1), Inches(1.5), width=Inches(8))

    pptx_io = io.BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io.getvalue()
