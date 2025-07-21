# ==============================================================================
# Core Engine: Analytics, QC, and Machine Learning
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This module is the analytical core of the VERITAS application, providing pure,
# non-UI functions for statistical process control (SPC), stability analysis,
# quality control (QC), advanced statistical analysis (ANOVA, Tukey's HSD), and
# machine learning-based anomaly detection. Functions are decoupled from the UI,
# taking data and parameters as input and returning predictable results for
# reliability and testability.
# ==============================================================================

import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from sklearn.ensemble import IsolationForest
from typing import Dict, List, Tuple, Optional

# --- Statistical Process Control (SPC) ---

def calculate_cpk(data_series: pd.Series, lsl: float, usl: float) -> float:
    """
    Calculate the Process Capability Index (Cpk).

    Args:
        data_series (pd.Series): Data series for Cpk calculation (e.g., purity values).
        lsl (float): Lower specification limit.
        usl (float): Upper specification limit.

    Returns:
        float: Cpk value, or 0.0 if calculation is not possible.

    Raises:
        ValueError: If data_series is empty, has zero standard deviation, or lsl >= usl.
        TypeError: If data_series, lsl, or usl is not numeric.
    """
    if not isinstance(data_series, pd.Series):
        raise TypeError("data_series must be a pandas Series")
    if not isinstance(lsl, (int, float)) or not isinstance(usl, (int, float)):
        raise TypeError("lsl and usl must be numeric")
    if lsl >= usl:
        raise ValueError("Lower specification limit must be less than upper specification limit")
    
    data_clean = data_series.dropna()
    if data_clean.empty:
        raise ValueError("Data series is empty after dropping NaN values")
    if data_clean.std() == 0:
        raise ValueError("Data series has zero standard deviation")
    
    mean = data_clean.mean()
    std_dev = data_clean.std()
    cpu = (usl - mean) / (3 * std_dev) if usl is not None else np.inf
    cpl = (mean - lsl) / (3 * std_dev) if lsl is not None else np.inf
    return min(cpu, cpl)

# --- Stability Analysis ---

def test_stability_poolability(df: pd.DataFrame, assay: str) -> Dict:
    """
    Perform an ANCOVA-like test to determine if stability data from multiple lots can be pooled.

    Args:
        df (pd.DataFrame): Stability data with 'lot_id', 'timepoint_months', and assay columns.
        assay (str): Column name of the assay to analyze (e.g., 'purity').

    Returns:
        Dict: Dictionary with 'poolable' (bool), 'p_value' (float), and 'reason' (str).

    Raises:
        ValueError: If required columns are missing or insufficient data.
        TypeError: If assay is not a string or df is not a DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(assay, str):
        raise TypeError("assay must be a string")
    required_cols = ['lot_id', 'timepoint_months', assay]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    df_clean = df[required_cols].dropna()
    if df_clean['lot_id'].nunique() < 2 or len(df_clean) < 4:
        return {'poolable': True, 'p_value': 1.0, 'reason': 'Insufficient data (need >= 2 lots and >= 4 rows)'}

    try:
        formula = f"`{assay}` ~ `timepoint_months` * C(lot_id)"
        model = ols(formula, data=df_clean).fit()
        anova_table = anova_lm(model, typ=2)

        p_value = anova_table["PR(>F)"]["C(lot_id)"]
        interaction_p_value = anova_table["PR(>F)"]["`timepoint_months`:C(lot_id)"]
        
        poolable = p_value > 0.05 and interaction_p_value > 0.05
        return {'poolable': poolable, 'p_value': min(p_value, interaction_p_value), 'reason': 'ANCOVA test completed'}
    except Exception as e:
        return {'poolable': True, 'p_value': 1.0, 'reason': f'ANCOVA test failed: {str(e)}'}

def calculate_stability_projection(df: pd.DataFrame, assay: str, use_pooled_data: bool) -> Dict:
    """
    Perform linear regression on stability data to project shelf life.

    Args:
        df (pd.DataFrame): Stability data with 'lot_id', 'timepoint_months', and assay columns.
        assay (str): Column name of the assay to analyze (e.g., 'purity').
        use_pooled_data (bool): Whether to pool data across lots or use the first lot.

    Returns:
        Dict: Dictionary with 'slope', 'intercept', 'r_squared', 'pred_x', and 'pred_y', or empty dict with keys if failed.

    Raises:
        ValueError: If required columns are missing or insufficient data.
        TypeError: If assay is not a string or df is not a DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(assay, str):
        raise TypeError("assay must be a string")
    required_cols = ['lot_id', 'timepoint_months', assay]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    df_clean = df[required_cols].dropna()
    if len(df_clean) < 2:
        return {'slope': 0.0, 'intercept': 0.0, 'r_squared': 0.0, 'pred_x': np.array([]), 'pred_y': np.array([])}

    try:
        if use_pooled_data:
            slope, intercept, r_value, _, _ = stats.linregress(df_clean['timepoint_months'], df_clean[assay])
        else:
            first_lot = df_clean['lot_id'].unique()[0]
            lot_df = df_clean[df_clean['lot_id'] == first_lot]
            if len(lot_df) < 2:
                return {'slope': 0.0, 'intercept': 0.0, 'r_squared': 0.0, 'pred_x': np.array([]), 'pred_y': np.array([])}
            slope, intercept, r_value, _, _ = stats.linregress(lot_df['timepoint_months'], lot_df[assay])

        pred_x = np.array([df_clean['timepoint_months'].min(), df_clean['timepoint_months'].max()])
        pred_y = intercept + slope * pred_x

        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value**2,
            'pred_x': pred_x,
            'pred_y': pred_y
        }
    except Exception as e:
        return {'slope': 0.0, 'intercept': 0.0, 'r_squared': 0.0, 'pred_x': np.array([]), 'pred_y': np.array([]), 'reason': f'Regression failed: {str(e)}'}

# --- Rule-Based QC Engine ---

def apply_qc_rules(df: pd.DataFrame, rules_config: dict, app_config: Any) -> pd.DataFrame:
    """
    Apply deterministic QC rules to a dataframe and return a report of discrepancies.

    Args:
        df (pd.DataFrame): DataFrame to check (e.g., HPLC data).
        rules_config (dict): Dictionary of rules to apply (e.g., {'check_nulls': True, 'check_negatives': True}).
        app_config (Any): Application configuration with process_capability.spec_limits.

    Returns:
        pd.DataFrame: DataFrame of discrepancies with 'sample_id', 'Issue', and 'Details' columns.

    Raises:
        ValueError: If required columns are missing or rules_config/app_config is invalid.
        TypeError: If df is not a DataFrame or rules_config is not a dict.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(rules_config, dict):
        raise TypeError("rules_config must be a dictionary")
    try:
        spec_limits = app_config.process_capability.spec_limits
    except AttributeError:
        raise ValueError("app_config must have process_capability.spec_limits")

    key_cols = ['sample_id', 'batch_id', 'purity', 'bio_activity']
    if not all(col in df.columns for col in key_cols):
        raise ValueError(f"DataFrame must contain columns: {key_cols}")

    discrepancies = []

    if rules_config.get('check_nulls', False):
        nulls = df[df[key_cols].isnull().any(axis=1)]
        for _, row in nulls.iterrows():
            discrepancies.append({
                'sample_id': row['sample_id'],
                'Issue': 'Missing Value',
                'Details': f"Null found in: {row[key_cols].index[row[key_cols].isnull()].tolist()}"
            })

    if rules_config.get('check_negatives', False):
        negatives = df[df['bio_activity'] < 0]
        for _, row in negatives.iterrows():
            discrepancies.append({
                'sample_id': row['sample_id'],
                'Issue': 'Negative Value',
                'Details': f"bio_activity is {row['bio_activity']:.2f}"
            })

    if rules_config.get('check_spec_limits', False):
        for cqa, specs in spec_limits.items():
            if cqa in df.columns:
                oor_mask = (df[cqa] < specs.lsl if specs.lsl is not None else False) | \
                           (df[cqa] > specs.usl if specs.usl is not None else False)
                for _, row in df[oor_mask].iterrows():
                    discrepancies.append({
                        'sample_id': row['sample_id'],
                        'Issue': 'Out of Specification',
                        'Details': f"{cqa} is {row[cqa]:.2f}, outside spec of LSL: {specs.lsl}, USL: {specs.usl}"
                    })

    return pd.DataFrame(discrepancies) if discrepancies else pd.DataFrame(columns=['sample_id', 'Issue', 'Details'])

# --- Advanced Statistical Analysis ---

def perform_normality_test(data_series: pd.Series) -> Dict:
    """
    Perform a Shapiro-Wilk test for normality.

    Args:
        data_series (pd.Series): Data series to test.

    Returns:
        Dict: Dictionary with 'statistic', 'p_value', and 'conclusion', or None values if test fails.

    Raises:
        ValueError: If data_series is empty or non-numeric.
        TypeError: If data_series is not a pandas Series.
    """
    if not isinstance(data_series, pd.Series):
        raise TypeError("data_series must be a pandas Series")
    data_clean = data_series.dropna()
    if data_clean.empty:
        raise ValueError("Data series is empty after dropping NaN values")
    if not np.issubdtype(data_clean.dtype, np.number):
        raise ValueError("Data series must be numeric")
    if len(data_clean) < 3:
        return {'statistic': None, 'p_value': None, 'conclusion': 'Insufficient data (need >= 3 non-NaN values)'}

    try:
        stat, p_value = stats.shapiro(data_clean)
        conclusion = "Data appears normal (p > 0.05)." if p_value > 0.05 else "Data is likely non-normal (p <= 0.05)."
        return {'statistic': stat, 'p_value': p_value, 'conclusion': conclusion}
    except Exception as e:
        return {'statistic': None, 'p_value': None, 'conclusion': f'Shapiro-Wilk test failed: {str(e)}'}

def perform_anova(df: pd.DataFrame, value_col: str, group_col: str) -> Dict:
    """
    Perform a one-way ANOVA test.

    Args:
        df (pd.DataFrame): DataFrame with data.
        value_col (str): Column name of the values to analyze.
        group_col (str): Column name of the grouping variable.

    Returns:
        Dict: Dictionary with 'f_stat' and 'p_value', or None if test fails.

    Raises:
        ValueError: If required columns are missing or insufficient data.
        TypeError: If df is not a DataFrame or columns are not strings.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(value_col, str) or not isinstance(group_col, str):
        raise TypeError("value_col and group_col must be strings")
    if not all(col in df.columns for col in [value_col, group_col]):
        raise ValueError(f"DataFrame must contain columns: {value_col}, {group_col}")

    groups = [group_df[value_col].dropna() for _, group_df in df.groupby(group_col)]
    if len(groups) < 2 or any(len(group) < 1 for group in groups):
        return {'f_stat': None, 'p_value': None, 'reason': 'Insufficient data (need >= 2 groups with non-empty data)'}

    try:
        f_stat, p_value = stats.f_oneway(*groups)
        return {'f_stat': f_stat, 'p_value': p_value}
    except Exception as e:
        return {'f_stat': None, 'p_value': None, 'reason': f'ANOVA test failed: {str(e)}'}

def perform_tukey_hsd(df: pd.DataFrame, value_col: str, group_col: str) -> pd.DataFrame:
    """
    Perform a Tukey's Honestly Significant Difference (HSD) post-hoc test.

    Args:
        df (pd.DataFrame): DataFrame with data.
        value_col (str): Column name of the values to analyze.
        group_col (str): Column name of the grouping variable.

    Returns:
        pd.DataFrame: DataFrame with Tukey's HSD results, or empty DataFrame if test fails.

    Raises:
        ValueError: If required columns are missing or insufficient data.
        TypeError: If df is not a DataFrame or columns are not strings.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(value_col, str) or not isinstance(group_col, str):
        raise TypeError("value_col and group_col must be strings")
    if not all(col in df.columns for col in [value_col, group_col]):
        raise ValueError(f"DataFrame must contain columns: {value_col}, {group_col}")

    df_clean = df[[value_col, group_col]].dropna()
    if df_clean[group_col].nunique() < 2 or len(df_clean) < 2:
        return pd.DataFrame(columns=['group1', 'group2', 'meandiff', 'p-adj', 'lower', 'upper', 'reject'])

    try:
        tukey_result = pairwise_tukeyhsd(endog=df_clean[value_col], groups=df_clean[group_col], alpha=0.05)
        return pd.DataFrame(data=tukey_result._results_table.data[1:], columns=tukey_result._results_table.data[0])
    except Exception as e:
        return pd.DataFrame(columns=['group1', 'group2', 'meandiff', 'p-adj', 'lower', 'upper', 'reject'], data=[{'reason': f'Tukey HSD test failed: {str(e)}'}])

# --- Machine Learning Engine ---

def run_anomaly_detection(df: pd.DataFrame, cols: List[str], contamination: float, random_state: Optional[int] = None) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Run IsolationForest model for anomaly detection on specified columns.

    Args:
        df (pd.DataFrame): DataFrame with data.
        cols (List[str]): List of column names for anomaly detection.
        contamination (float): Proportion of outliers (0 < contamination < 0.5).
        random_state (Optional[int]): Random seed for reproducibility. Defaults to None.

    Returns:
        Tuple[np.ndarray, pd.DataFrame]: Predictions (-1 for anomalies, 1 for inliers) and input data, or empty array and DataFrame if failed.

    Raises:
        ValueError: If cols are missing, contamination is invalid, or insufficient data.
        TypeError: If df is not a DataFrame or cols is not a list of strings.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not isinstance(cols, list) or not all(isinstance(c, str) for c in cols):
        raise TypeError("cols must be a list of strings")
    if not all(c in df.columns for c in cols):
        raise ValueError(f"DataFrame must contain columns: {cols}")
    if not isinstance(contamination, (int, float)) or not 0 < contamination < 0.5:
        raise ValueError("contamination must be between 0 and 0.5")

    data_to_fit = df[cols].dropna()
    if len(data_to_fit) < 2:
        return np.array([]), pd.DataFrame(columns=cols)

    try:
        model = IsolationForest(contamination=contamination, random_state=random_state)
        predictions = model.fit_predict(data_to_fit)
        return predictions, data_to_fit
    except Exception as e:
        return np.array([]), pd.DataFrame(columns=cols, data=[{'reason': f'Anomaly detection failed: {str(e)}'}])
