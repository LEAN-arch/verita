# ==============================================================================
# Core Module: Application Settings & Configuration
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Definitively Corrected Version)
#
# Description:
# This module uses Pydantic to define a robust, type-safe, and self-documenting
# configuration for the entire VERITAS application. This is a best practice for
# building maintainable, enterprise-grade software. It centralizes all business
# rules, specifications, and UI constants.
# ==============================================================================

from pydantic import BaseModel, Field
from typing import Dict, List, Optional

# --- Color Palette & Plotly Theme (UI Constants) ---
class VertexColors(BaseModel):
    blue: str = '#003DA5'
    lightblue: str = '#00A3E0'
    green: str = '#00B140'
    orange: str = '#F37021'
    gray: str = '#6A737B'
    red: str = '#D4000F'
    lightred: str = '#FFDDE0'
    lightyellow: str = '#FEF9E3'
    lightcyan: str = '#E0FFFF'

COLORS = VertexColors()

# --- Authorization & Security Settings ---
class AuthSettings(BaseModel):
    role_options: List[str] = ['DTE Leadership', 'Study Director', 'QC Analyst', 'Scientist']
    default_role: str = "DTE Leadership"
    default_user: str = "Demo User"
    page_permissions: Dict[str, List[str]] = {
        "VERITAS_Home.py": ['DTE Leadership', 'Study Director', 'QC Analyst', 'Scientist'],
        "1_🧪_QC_Integrity_Center.py": ['Scientist', 'QC Analyst', 'DTE Leadership'],
        "2_📈_Process_Capability.py": ['Study Director', 'Scientist', 'QC Analyst', 'DTE Leadership'],
        "3_⏳_Stability_Program.py": ['Study Director', 'Scientist', 'DTE Leadership'],
        "4_📄_Regulatory_Support.py": ['Study Director', 'Scientist', 'DTE Leadership'],
        "5_📌_Deviation_Hub.py": ['QC Analyst', 'DTE Leadership'],
        "6_⚖️_Governance_Audit.py": ['Study Director', 'QC Analyst', 'DTE Leadership']
    }

# --- Specific Business Logic & Rule Settings ---
class SpecLimits(BaseModel):
    lsl: Optional[float] = Field(None, alias='LSL')
    usl: Optional[float] = Field(None, alias='USL')

class ProcessCapabilitySettings(BaseModel):
    cpk_target: float = 1.33
    available_cqas: List[str] = ["Purity", "Aggregate Content", "Main Impurity", "Bio-activity"]
    spec_limits: Dict[str, SpecLimits]

class StabilitySpecSettings(BaseModel):
    spec_limits: Dict[str, SpecLimits]
    poolability_alpha: float = 0.05

class DeviationManagementSettings(BaseModel):
    kanban_states: List[str] = ["New", "In Progress", "Pending QA", "Closed"]
    priority_colors: Dict[str, str] = {
        "High": COLORS.lightred, "Medium": COLORS.lightyellow, "Low": COLORS.lightcyan
    }

class AuditTrailSettings(BaseModel):
    action_icons: Dict[str, str] = {
        "User Login": "👤", "Data Fetched": "🔍", "Report Generated": "📄", 
        "Deviation Status Changed": "🔄", "Stability Plot Viewed": "📈", 
        "E-Signature Applied": "✍️", "Data Exported": "📤", "Configuration Changed": "⚙️",
        "File Ingested": "📥", "QC Rule Applied": "🔬", "Data Point Flagged": "🚩",
        "Discrepancy Resolved": "✅", "Permission Changed": "🔐", "Role View Changed": "🎭",
        "Deviation Created": "➕"
    }

# --- Top-Level Application Settings Model ---
class AppSettings(BaseModel):
    version: str
    description: str
    help_url: str
    process_capability: ProcessCapabilitySettings
    stability_specs: StabilitySpecSettings
    deviation_management: DeviationManagementSettings
    audit_trail: AuditTrailSettings
    
# --- Instantiate the Configuration Models with Concrete Values ---
AUTH = AuthSettings()

# --- ATTRIBUTE ERROR FIX ---
# The instantiated object must be lowercase `app` to match the attribute access
# pattern used throughout the application (e.g., `settings.app.version`).
app = AppSettings(
    version="10.3 (Definitively Corrected)",
    description="Vertex Ensured Reporting & Integrity Transformation Automation Suite",
    help_url="https://www.vertex.com/contact-us",
    process_capability=ProcessCapabilitySettings(
        spec_limits={
            "Purity": SpecLimits(LSL=98.0, USL=102.0),
            "Aggregate Content": SpecLimits(LSL=0.0, USL=1.0),
            "Main Impurity": SpecLimits(LSL=0.0, USL=0.5),
            "Bio-activity": SpecLimits(LSL=90.0, USL=110.0)
        }
    ),
    stability_specs=StabilitySpecSettings(
        spec_limits={
            "Purity (%)": SpecLimits(USL=None, LSL=98.0),
            "Main Impurity (%)": SpecLimits(USL=0.5, LSL=None)
        }
    ),
    deviation_management=DeviationManagementSettings(),
    audit_trail=AuditTrailSettings()
)
    ),
    deviation_management=DeviationManagementSettings(),
    audit_trail=AuditTrailSettings()
)
