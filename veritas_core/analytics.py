
# ==============================================================================
# Analytics Module for VERITAS Application
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# Provides analytical functions for the VERITAS application, including rule-based
# quality control (QC) checks for data integrity and compliance.
# Ensures GxP compliance with robust error handling and logging.
# ==============================================================================

import pandas as pd
import logging
from typing import Dict, List, Any
from .. import config

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_qc_rules(df: pd.DataFrame, rules_config: Dict[str, Any], app_config: Any) -> Dict[str, Any]:
    """
    Apply deterministic QC rules to a dataframe and return a report of violations.

    Args:
        df (pd.DataFrame): The input dataframe to check.
        rules_config (Dict[str, Any]): Configuration for QC rules (e.g., thresholds, conditions).
        app_config (Any): Application configuration (from config.AppConfig.app).

    Returns:
        Dict[str, Any]: A report containing QC violations and summary statistics.

    Raises:
        ValueError: If input dataframe or configurations are invalid.
    """
    try:
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Input 'df' must be a pandas DataFrame")
        if not isinstance(rules_config, dict):
            raise ValueError("rules_config must be a dictionary")
        if not hasattr(app_config, 'process_capability'):
            raise ValueError("app_config must have process_capability attribute")

        report = {"violations": [], "summary": {}}
        for cqa in app_config.process_capability.available_cqas:
            if cqa not in df.columns:
                continue
            spec = app_config.process_capability.spec_limits.get(cqa, None)
            if not spec:
                continue
            lsl, usl = spec.lsl, spec.usl
            rule = rules_config.get(cqa, {})
            violations = df[
                (df[cqa] < lsl) | (df[cqa] > usl) | df[cqa].isna()
            ][['sample_id', cqa]].to_dict('records')
            report["violations"].extend([
                {"sample_id": v["sample_id"], "cqa": cqa, "value": v[cqa], "reason": "Out of spec"}
                for v in violations
            ])
        report["summary"] = {"total_violations": len(report["violations"])}
        logger.info(f"QC rules applied to dataframe with {len(df)} rows: {report['summary']}")
        return report
    except Exception as e:
        logger.error(f"Failed to apply QC rules: {str(e)}")
        raise ValueError(f"QC rule application failed: {str(e)}")
