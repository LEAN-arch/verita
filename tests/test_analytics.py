# ==============================================================================
# Unit Tests for the Analytics Engine
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29
#
# Description:
# This file contains unit tests for the core analytical functions in the
# veritas_core.engine.analytics module. These tests use the Pytest framework
# to ensure the logic is correct, robust, and reliable.
#
# How to Run:
# From the root project directory, simply run `pytest` in the terminal.
# ==============================================================================

import pandas as pd
import numpy as np
import pytest

# As in conftest, ensure the veritas_core package is discoverable
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veritas_core.engine import analytics

# --- Tests for calculate_cpk ---

def test_calculate_cpk_normal():
    """Test Cpk calculation with a capable, centered process."""
    data = pd.Series([9.9, 10.0, 10.1, 9.8, 10.2, 9.95, 10.05])
    lsl, usl = 9.5, 10.5
    # For this data, mean is ~10.0, std is ~0.13. Cpk should be > 1.33
    cpk = analytics.calculate_cpk(data, lsl, usl)
    assert cpk > 1.33
    assert isinstance(cpk, float)

def test_calculate_cpk_off_center():
    """Test Cpk calculation with a process shifted towards a spec limit."""
    data = pd.Series([9.6, 9.7, 9.55, 9.65, 9.75])
    lsl, usl = 9.5, 10.5
    # Process is close to LSL, so Cpk should be low
    cpk = analytics.calculate_cpk(data, lsl, usl)
    assert cpk < 1.0

def test_calculate_cpk_single_sided_usl():
    """Test Cpk with only an Upper Specification Limit."""
    data = pd.Series([10, 11, 12, 10.5, 11.5])
    lsl, usl = None, 15.0
    # Cpl should be infinite, so Cpk will equal Cpu
    cpu = (15.0 - data.mean()) / (3 * data.std())
    cpk = analytics.calculate_cpk(data, lsl, usl)
    assert cpk == pytest.approx(cpu)

def test_calculate_cpk_edge_cases():
    """Test edge cases like empty data or zero standard deviation."""
    assert analytics.calculate_cpk(pd.Series([]), 0, 10) == 0.0
    assert analytics.calculate_cpk(pd.Series([5, 5, 5]), 0, 10) == 0.0

# --- Tests for ANOVA and Post-Hoc ---

def test_perform_anova_significant_difference():
    """Test ANOVA where a significant difference between groups exists."""
    df = pd.DataFrame({
        'value': [10, 11, 10.5, 10.2,  20, 21, 20.5, 20.8],
        'group': ['A', 'A', 'A', 'A',   'B', 'B', 'B', 'B']
    })
    results = analytics.perform_anova(df, 'value', 'group')
    assert 'p_value' in results
    assert results['p_value'] < 0.05 # Expect a significant result

def test_perform_anova_no_difference():
    """Test ANOVA where there is no significant difference."""
    df = pd.DataFrame({
        'value': [10, 11, 10.5, 10.2,  10.1, 10.9, 10.6, 10.3],
        'group': ['A', 'A', 'A', 'A',   'B', 'B', 'B', 'B']
    })
    results = analytics.perform_anova(df, 'value', 'group')
    assert 'p_value' in results
    assert results['p_value'] > 0.05 # Expect a non-significant result

def test_perform_tukey_hsd(hplc_data):
    """
    Test the Tukey HSD function using mock data from the fixture.
    This is an integration test of the function with realistic data.
    """
    results = analytics.perform_tukey_hsd(hplc_data, 'Purity', 'instrument_id')
    assert isinstance(results, pd.DataFrame)
    assert 'reject' in results.columns
    # Check that it found a difference between HPLC-03 (drift injected) and others
    hplc03_vs_hplc01 = results[((results.group1 == 'HPLC-01') & (results.group2 == 'HPLC-03')) |
                               ((results.group1 == 'HPLC-03') & (results.group2 == 'HPLC-01'))]
    assert hplc03_vs_hplc01['reject'].iloc[0] == True


# --- Tests for Stability Poolability ---

def test_stability_poolability_can_be_pooled(stability_data):
    """Test the case where lots have similar slopes and should be poolable."""
    # Create two lots with very similar degradation profiles
    lot1 = pd.DataFrame({'lot_id': 'L1', 'Timepoint (Months)': [0, 6, 12], 'Purity (%)': [99.5, 99.2, 98.9]})
    lot2 = pd.DataFrame({'lot_id': 'L2', 'Timepoint (Months)': [0, 6, 12], 'Purity (%)': [99.4, 99.1, 98.8]})
    test_df = pd.concat([lot1, lot2])
    
    result = analytics.test_stability_poolability(test_df, 'Purity (%)')
    assert result['poolable'] == True
    assert result['p_value'] > 0.05

def test_stability_poolability_cannot_be_pooled(stability_data):
    """Test the case where lots have different slopes and should not be pooled."""
    # Create two lots with very different degradation profiles
    lot1 = pd.DataFrame({'lot_id': 'L1', 'Timepoint (Months)': [0, 6, 12], 'Purity (%)': [99.5, 99.2, 98.9]}) # Slow degrader
    lot2 = pd.DataFrame({'lot_id': 'L2', 'Timepoint (Months)': [0, 6, 12], 'Purity (%)': [99.5, 98.5, 97.5]}) # Fast degrader
    test_df = pd.concat([lot1, lot2])
    
    result = analytics.test_stability_poolability(test_df, 'Purity (%)')
    assert result['poolable'] == False
    assert result['p_value'] < 0.05
