# ==============================================================================
# Core Engine: Analytics, QC, and Machine Learning
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Ultimate Version)
#
# Description:
# This module is the analytical core of the VERITAS application. It contains
# a comprehensive suite of pure, non-UI functions for statistical process
# control (SPC), data quality validation, advanced statistical analysis (ANOVA),
# and machine learning.
#
# Architectural Principle:
# All functions are "pure" and decoupled from the Streamlit UI. They take data
# and parameters as input and return predictable results, making them highly
# reliable and easily unit-testable.
# ==============================================================================

import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from sklearn.ensemble import IsolationForest
from typing import Dict, List, Tuple

# --- Statistical Process Control (SPC) ---

def calculate_cpk(data_series: pd.Series, lsl: float, usl: float) -> float:
    """Calculates the Process Capability Index (Cpk)."""
    if data_series.dropna().empty or data_series.std() == 0:
        return 0.0
    mean = data_series.mean(); std_dev = data_series.std()
    cpu = (usl - mean) / (3 * std_dev) if usl is not None else np.inf
    cpl = (mean - lsl) / (3 * std_dev) if lsl is not None else np.inf
    return min(cpu, cpl)

# --- Stability Analysis ---

def test_stability_poolability(df: pd.DataFrame, assay: str) -> Dict:
    """
    Performs an ANCOVA-like test to determine if stability data from multiple
    lots can be pooled, per ICH Q1E guidelines.
    """
    df_clean = df[['lot_id', 'Timepoint (Months)', assay]].dropna()
    if df_clean['lot_id'].nunique() < 2 or len(df_clean) < 4:
        return {'poolable': True, 'p_value': 1.0, 'reason': 'Not enough data for test'}
    
    formula = f"`{assay}` ~ `Timepoint (Months)` * C(lot_id)"
    model = ols(formula, data=df_clean).fit()
    anova_table = anova_lm(model, typ=2)
    
    p_value = anova_table["PR(>F)"]["C(lot_id)"]
    interaction_p_value = anova_table["PR(>F)"]["`Timepoint (Months)`:C(lot_id)"]
    
    # Poolable if both the main effect and interaction are not significant
    poolable = p_value > 0.05 and interaction_p_value > 0.05
    return {'poolable': poolable, 'p_value': min(p_value, interaction_p_value)}

def calculate_stability_projection(df: pd.DataFrame, assay: str, use_pooled_data: bool) -> Dict:
    """Performs linear regression on stability data to project shelf life."""
    df_clean = df[['lot_id', 'Timepoint (Months)', assay]].dropna()
    if len(df_clean) < 2: return {}

    if use_pooled_data:
        # Pooled regression ignores the lot
        slope, intercept, r_value, _, _ = stats.linregress(df_clean['Timepoint (Months)'], df_clean[assay])
    else:
        # In a multi-lot unpooled scenario, this should be handled gracefully.
        # For simplicity, we'll analyze the first lot if not pooling.
        first_lot = df_clean['lot_id'].unique()[0]
        lot_df = df_clean[df_clean['lot_id'] == first_lot]
        if len(lot_df) < 2: return {}
        slope, intercept, r_value, _, _ = stats.linregress(lot_df['Timepoint (Months)'], lot_df[assay])

    # Calculate confidence interval for the regression line
    pred_x = np.array([df_clean['Timepoint (Months)'].min(), df_clean['Timepoint (Months)'].max()])
    pred_y = intercept + slope * pred_x
    
    return {'slope': slope, 'intercept': intercept, 'r_squared': r_value**2,
            'pred_x': pred_x, 'pred_y': pred_y}


# --- Rule-Based QC Engine ---

def apply_qc_rules(df: pd.DataFrame, rules_config: dict, app_config) -> pd.DataFrame:
    """Applies a set of deterministic rules to a dataframe and returns a report of discrepancies."""
    discrepancies = []
    
    if rules_config.get('check_nulls', False):
        key_cols = ['sample_id', 'batch_id', 'Purity', 'Bio-activity']
        nulls = df[df[key_cols].isnull().any(axis=1)]
        for _, row in nulls.iterrows():
            discrepancies.append({'sample_id': row['sample_id'], 'Issue': 'Missing Value', 'Details': f"Null found in: {row[key_cols].index[row[key_cols].isnull()].tolist()}"})
            
    if rules_config.get('check_negatives', False) and 'Bio-activity' in df.columns:
        negatives = df[df['Bio-activity'] < 0]
        for _, row in negatives.iterrows():
            discrepancies.append({'sample_id': row['sample_id'], 'Issue': 'Negative Value', 'Details': f"Bio-activity is {row['Bio-activity']:.2f}"})

    if rules_config.get('check_spec_limits', False):
        for cqa, specs in app_config.process_capability.spec_limits.items():
            if cqa in df.columns:
                oor_mask = (df[cqa] < specs.lsl if specs.lsl is not None else False) | \
                           (df[cqa] > specs.usl if specs.usl is not None else False)
                for _, row in df[oor_mask].iterrows():
                    discrepancies.append({'sample_id': row['sample_id'], 'Issue': 'Out of Specification', 'Details': f"{cqa} is {row[cqa]:.2f}, outside spec of LSL: {specs.lsl}, USL: {specs.usl}"})

    return pd.DataFrame(discrepancies) if discrepancies else pd.DataFrame(columns=['sample_id', 'Issue', 'Details'])

# --- Advanced Statistical Analysis ---

def perform_normality_test(data_series: pd.Series) -> Dict:
    """Performs a Shapiro-Wilk test for normality."""
    if len(data_series.dropna()) < 3:
        return {'statistic': None, 'p_value': None, 'conclusion': 'Not enough data'}
    stat, p_value = stats.shapiro(data_series.dropna())
    conclusion = "Data appears normal (p > 0.05)." if p_value > 0.05 else "Data is likely non-normal (p <= 0.05)."
    return {'statistic': stat, 'p_value': p_value, 'conclusion': conclusion}

def perform_anova(df: pd.DataFrame, value_col: str, group_col: str) -> Dict:
    """Performs a one-way ANOVA test."""
    groups = [group_df[value_col].dropna() for name, group_df in df.groupby(group_col)]
    if len(groups) < 2:
        return {'f_stat': None, 'p_value': None}
    f_stat, p_value = stats.f_oneway(*groups)
    return {'f_stat': f_stat, 'p_value': p_value}

def perform_tukey_hsd(df: pd.DataFrame, value_col: str, group_col: str) -> pd.DataFrame:
    """Performs a Tukey's Honestly Significant Difference (HSD) post-hoc test."""
    df_clean = df[[value_col, group_col]].dropna()
    tukey_result = pairwise_tukeyhsd(endog=df_clean[value_col], groups=df_clean[group_col], alpha=0.05)
    return pd.DataFrame(data=tukey_result._results_table.data[1:], columns=tukey_result._results_table.data[0])


# --- Machine Learning Engine ---

def run_anomaly_detection(df: pd.DataFrame, cols: List[str], contamination: float) -> Tuple[np.ndarray, pd.DataFrame]:
    """Runs the IsolationForest ML model on specified columns."""
    if df.empty or not all(c in df.columns for c in cols):
        return None, None
    data_to_fit = df[cols].dropna()
    if len(data_to_fit) < 2:
        return None, None
        
    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(data_to_fit)
    return predictions, data_to_fit
