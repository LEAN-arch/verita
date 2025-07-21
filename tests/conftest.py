# ==============================================================================
# Pytest Configuration and Fixtures
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29
#
# Description:
# This file defines shared fixtures for the Pytest testing framework. Fixtures
# are reusable objects that set up a consistent state for tests to run against.
#
# Key Feature:
# The `mock_repo` fixture provides a clean, pre-populated instance of the
# MockDataRepository to any test function that requests it. This allows us to
# test our backend analytics engine against a known, predictable dataset
# without any dependency on the Streamlit UI or a live database.
# ==============================================================================

import pytest
import pandas as pd

# To allow pytest to find the veritas_core package, we add the root directory
# to the Python path. This is a standard practice for testing local packages.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from veritas_core.repository import MockDataRepository

@pytest.fixture(scope="session")
def mock_repo() -> MockDataRepository:
    """
    A session-scoped fixture that initializes the MockDataRepository once
    and makes it available to all tests. Scope='session' means it's created
    only once for the entire test run, which is efficient.
    """
    return MockDataRepository(seed=42)

@pytest.fixture
def hplc_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """Provides a fresh copy of the HPLC data for a test."""
    return mock_repo.get_hplc_data()

@pytest.fixture
def stability_data(mock_repo: MockDataRepository) -> pd.DataFrame:
    """Provides a fresh copy of the stability data for a test."""
    return mock_repo.get_stability_data()
