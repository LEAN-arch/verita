# ==============================================================================
# Core Module: Abstracted Data Repository
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# This module implements the Repository Pattern to abstract the data source from
# the application logic. It defines a contract (ABC) for required data operations
# and provides a concrete implementation for mock data and a placeholder for
# a production database. This ensures scalability, testability, and maintainability
# for enterprise applications.
# ==============================================================================

from abc import ABC, abstractmethod
from threading import Lock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
try:
    import streamlit as st
except ImportError:
    st = None  # Fallback for non-Streamlit environments
from . import settings

# --- 1. Abstract Base Class (The "Contract") ---

class DataRepository(ABC):
    """
    Abstract Base Class defining the contract for all data repositories.
    Any class providing data to the application must implement these methods.
    """
    @abstractmethod
    def get_hplc_data(self) -> pd.DataFrame:
        """Retrieve HPLC data as a DataFrame."""
        pass

    @abstractmethod
    def get_deviations_data(self) -> pd.DataFrame:
        """Retrieve deviations data as a DataFrame."""
        pass

    @abstractmethod
    def get_stability_data(self) -> pd.DataFrame:
        """Retrieve stability data as a DataFrame."""
        pass

    @abstractmethod
    def get_audit_log(self) -> pd.DataFrame:
        """Retrieve audit log as a DataFrame."""
        pass
    
    @abstractmethod
    def write_audit_log(self, user: str, action: str, details: str, record_id: str = 'N/A') -> None:
        """
        Log an audit trail entry.

        Args:
            user (str): User performing the action.
            action (str): Action being logged.
            details (str): Details of the action.
            record_id (str, optional): Associated record ID. Defaults to 'N/A'.
        """
        pass
        
    @abstractmethod
    def update_deviation_status(self, dev_id: str, new_status: str) -> None:
        """
        Update the status of a deviation.

        Args:
            dev_id (str): Deviation ID.
            new_status (str): New status for the deviation.
        """
        pass

    @abstractmethod
    def create_deviation(self, title: str, linked_record: str, priority: str = "Medium") -> str:
        """
        Create a new deviation and return its ID.

        Args:
            title (str): Title of the deviation.
            linked_record (str): Associated record ID.
            priority (str, optional): Priority level. Defaults to "Medium".

        Returns:
            str: ID of the new deviation.
        """
        pass

# --- 2. Concrete Implementation: Mock Data Factory ---

class MockDataRepository(DataRepository):
    """
    A concrete implementation of DataRepository that generates and serves
    cohesive, realistic mock data for development, testing, and demonstration.
    """
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the mock repository with optional seed for reproducibility.

        Args:
            seed (int, optional): Random seed for data generation. Defaults to None.

        Raises:
            RuntimeError: If data generation fails.
        """
        self.rng = np.random.default_rng(seed)
        self._lock = Lock()  # For thread-safe data mutation
        self._load_all_data()

    def _load_all_data(self) -> None:
        """Generate all datasets in a dependent sequence for cohesion."""
        try:
            self.hplc_df = self._generate_hplc_data(num_samples=500)
            self.deviations_df = self._generate_deviations_data()
            self.stability_df = self._generate_stability_data()
            self.audit_df = self._generate_audit_trail(num_entries=300)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize mock data: {str(e)}")

    # --- Data Generation Methods ---
    def _generate_hplc_data(self, num_samples: int = 500) -> pd.DataFrame:
        """
        Generate mock HPLC data.

        Args:
            num_samples (int): Number of samples to generate. Must be positive.

        Returns:
            pd.DataFrame: Generated HPLC data.

        Raises:
            ValueError: If num_samples is not positive.
        """
        if num_samples <= 0:
            raise ValueError("num_samples must be positive")
        
        start_time = datetime(2024, 4, 1)
        data = {
            'sample_id': [f'SMP-{1000+i}' for i in range(num_samples)],
            'batch_id': self.rng.choice(['B01-A', 'B01-B', 'B02-A', 'B02-B', 'B03-A'], size=num_samples),
            'study_id': self.rng.choice(
                ['VX-809-PK-01', 'VX-561-Tox-03', 'VX-121-Stab-02', 'VX-984-Form-05'],
                size=num_samples,
                p=[0.3, 0.3, 0.2, 0.2]
            ),
            'injection_time': pd.to_datetime([start_time + timedelta(hours=1.5*i) for i in range(num_samples)]),
            'purity': self.rng.normal(loc=99.5, scale=0.2, size=num_samples),
            'aggregate_content': self.rng.normal(loc=0.5, scale=0.1, size=num_samples),
            'main_impurity': self.rng.normal(loc=0.2, scale=0.05, size=num_samples),
            'bio_activity': self.rng.normal(loc=105, scale=5, size=num_samples),
            'instrument_id': self.rng.choice(
                ['HPLC-01', 'HPLC-02', 'HPLC-03', 'UPLC-01'],
                size=num_samples,
                p=[0.4, 0.3, 0.15, 0.15]
            ),
            'analyst': self.rng.choice(['A. Turing', 'M. Curie', 'R. Franklin', 'L. Meitner'], size=num_samples)
        }
        df = pd.DataFrame(data)
        # Apply clipping before outliers to respect bounds
        df['purity'] = df['purity'].clip(97.0, 100.0)
        df['aggregate_content'] = df['aggregate_content'].clip(0.0, 1.0)
        df['main_impurity'] = df['main_impurity'].clip(0.0, 1.0)
        # Set outliers only if sufficient samples
        if num_samples > 50:
            df.loc[10, 'purity'] = 97.8  # Outlier within bounds
            df.loc[50, 'bio_activity'] = 205.0
        return df

    def _generate_deviations_data(self) -> pd.DataFrame:
        """
        Generate mock deviations data tied to HPLC data.

        Returns:
            pd.DataFrame: Generated deviations data.

        Raises:
            AttributeError: If hplc_df is not initialized.
        """
        if not hasattr(self, 'hplc_df'):
            raise AttributeError("HPLC data must be initialized before generating deviations")
        
        sample_ids = self.hplc_df['sample_id'].tolist()[:10] if len(self.hplc_df) > 0 else ['SMP-1000']
        deviations = [
            {
                'id': f'DEV-{i:03d}',
                'title': f'OOS Result {i}',
                'status': self.rng.choice(['New', 'In Progress', 'Pending QA']),
                'priority': self.rng.choice(['High', 'Medium', 'Low']),
                'linked_record': self.rng.choice(sample_ids)
            }
            for i in range(1, 5)
        ]
        return pd.DataFrame(deviations)

    def _generate_stability_data(self) -> pd.DataFrame:
        """
        Generate mock stability data.

        Returns:
            pd.DataFrame: Generated stability data.
        """
        data = []
        products = {'VX-561': (99.5, 0.1), 'VX-809': (99.8, 0.05)}
        lots = ['A202301', 'A202302', 'B202301', 'B202302']
        timepoints = [0, 3, 6, 9, 12, 18, 24]
        for product, (p_start, i_start) in products.items():
            for lot in lots:
                seed = hash(f"{product}{lot}") % (2**32 - 1)
                lot_rng = np.random.default_rng(seed)
                for t in timepoints:
                    purity = max(0, min(100, p_start - (t * lot_rng.uniform(0.05, 0.08)) - lot_rng.uniform(0, 0.1)))
                    impurity = max(0, min(5, i_start + (t * lot_rng.uniform(0.01, 0.02)) + lot_rng.uniform(0, 0.05)))
                    data.append({
                        'product_id': product,
                        'lot_id': lot,
                        'timepoint_months': t,
                        'purity': purity,
                        'main_impurity': impurity
                    })
        return pd.DataFrame(data)

    def _generate_audit_trail(self, num_entries: int = 300) -> pd.DataFrame:
        """
        Generate mock audit trail data.

        Args:
            num_entries (int): Number of audit entries to generate. Must be positive.

        Returns:
            pd.DataFrame: Generated audit trail data.

        Raises:
            ValueError: If num_entries is not positive.
            AttributeError: If required dependencies are not initialized or settings are invalid.
        """
        if num_entries <= 0:
            raise ValueError("num_entries must be positive")
        
        try:
            actions = list(settings.app.audit_trail.action_icons.keys())
        except AttributeError:
            raise AttributeError("settings.app.audit_trail.action_icons is not properly defined")
        
        users = ['DTE-System', 'A. Turing', 'R. Franklin', 'QA.Bot', 'M. Curie']
        record_ids = (
            (self.hplc_df['sample_id'].tolist() + self.deviations_df['id'].tolist())
            if (hasattr(self, 'hplc_df') and hasattr(self, 'deviations_df'))
            else ['N/A']
        )
        start_time = datetime(2024, 4, 1)
        log = []
        for i in range(num_entries):
            details = self.rng.choice([
                "Routine system operation.",
                "User updated record.",
                "System error detected."
            ])
            log.append({
                'timestamp': start_time - timedelta(hours=i * 1.3, minutes=int(self.rng.integers(0, 59))),
                'user': self.rng.choice(users),
                'action': self.rng.choice(actions),
                'record_id': self.rng.choice(record_ids),
                'details': details
            })
        return pd.DataFrame(log).sort_values('timestamp', ascending=False).reset_index(drop=True)

    # --- Data Access Methods ---
    def get_hplc_data(self) -> pd.DataFrame:
        """
        Retrieve HPLC data.

        Returns:
            pd.DataFrame: Copy of HPLC data.

        Raises:
            AttributeError: If hplc_df is not initialized.
        """
        if not hasattr(self, 'hplc_df'):
            raise AttributeError("HPLC data not initialized")
        return self.hplc_df.copy()

    def get_deviations_data(self) -> pd.DataFrame:
        """
        Retrieve deviations data.

        Returns:
            pd.DataFrame: Copy of deviations data.

        Raises:
            AttributeError: If deviations_df is not initialized.
        """
        if not hasattr(self, 'deviations_df'):
            raise AttributeError("Deviations data not initialized")
        return self.deviations_df.copy()

    def get_stability_data(self) -> pd.DataFrame:
        """
        Retrieve stability data.

        Returns:
            pd.DataFrame: Copy of stability data.

        Raises:
            AttributeError: If stability_df is not initialized.
        """
        if not hasattr(self, 'stability_df'):
            raise AttributeError("Stability data not initialized")
        return self.stability_df.copy()

    def get_audit_log(self) -> pd.DataFrame:
        """
        Retrieve audit log.

        Returns:
            pd.DataFrame: Copy of audit log.

        Raises:
            AttributeError: If audit_df is not initialized.
        """
        if not hasattr(self, 'audit_df'):
            raise AttributeError("Audit log not initialized")
        return self.audit_df.copy()

    # --- Data Mutation Methods ---
    def write_audit_log(self, user: str, action: str, details: str, record_id: str = 'N/A') -> None:
        """
        Log an audit trail entry.

        Args:
            user (str): User performing the action.
            action (str): Action being logged.
            details (str): Details of the action.
            record_id (str, optional): Associated record ID. Defaults to 'N/A'.

        Raises:
            ValueError: If user, action, or details is empty.
            AttributeError: If audit_df is not initialized.
        """
        if not all([user, action, details]):
            raise ValueError("User, action, and details must not be empty")
        if not hasattr(self, 'audit_df'):
            raise AttributeError("Audit log not initialized")

        log_entry = {
            'timestamp': pd.to_datetime(datetime.now()),
            'user': user,
            'action': action,
            'record_id': record_id,
            'details': details
        }
        with self._lock:
            new_row_df = pd.DataFrame([log_entry])
            self.audit_df = pd.concat([new_row_df, self.audit_df], ignore_index=True)
        
        if st is not None:
            st.toast(f"Action Logged: {action}", icon="📝")
        else:
            print(f"Action Logged: {action}")

    def update_deviation_status(self, dev_id: str, new_status: str) -> None:
        """
        Update the status of a deviation.

        Args:
            dev_id (str): Deviation ID.
            new_status (str): New status for the deviation.

        Raises:
            ValueError: If dev_id is not found or new_status is invalid.
            AttributeError: If deviations_df is not initialized.
        """
        if not hasattr(self, 'deviations_df'):
            raise AttributeError("Deviations data not initialized")
        if dev_id not in self.deviations_df['id'].values:
            raise ValueError(f"Deviation ID {dev_id} not found")
        valid_statuses = ["New", "In Progress", "Pending QA", "Closed"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
        
        with self._lock:
            self.deviations_df.loc[self.deviations_df['id'] == dev_id, 'status'] = new_status

    def create_deviation(self, title: str, linked_record: str, priority: str = "Medium") -> str:
        """
        Create a new deviation and return its ID.

        Args:
            title (str): Title of the deviation.
            linked_record (str): Associated record ID.
            priority (str, optional): Priority level. Defaults to "Medium".

        Returns:
            str: ID of the new deviation.

        Raises:
            ValueError: If title or linked_record is empty, or priority is invalid.
            AttributeError: If deviations_df is not initialized.
        """
        if not all([title, linked_record]):
            raise ValueError("Title and linked_record must not be empty")
        valid_priorities = ["High", "Medium", "Low"]
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority: {priority}. Must be one of {valid_priorities}")
        if not hasattr(self, 'deviations_df'):
            raise AttributeError("Deviations data not initialized")

        import uuid
        new_id = f"DEV-{str(uuid.uuid4())[:8]}"
        new_dev = {
            'id': new_id,
            'title': title,
            'status': 'New',
            'priority': priority,
            'linked_record': linked_record
        }
        with self._lock:
            new_row_df = pd.DataFrame([new_dev])
            self.deviations_df = pd.concat([self.deviations_df, new_row_df], ignore_index=True)
        return new_id

# --- 3. Concrete Implementation: Production Database ---

class ProdDataRepository(DataRepository):
    """
    A placeholder implementation of DataRepository for the production data warehouse.
    Currently delegates to MockDataRepository as the production connector is not implemented.
    """
    def __init__(self, conn_params: Dict[str, str]):
        """
        Initialize the production repository.

        Args:
            conn_params (Dict[str, str]): Database connection parameters.

        Raises:
            NotImplementedError: Always raised as this is a placeholder.
        """
        if st is not None:
            st.info("NOTE: Using Mock Repository. Production database connector is not yet implemented.")
        else:
            print("NOTE: Using Mock Repository. Production database connector is not yet implemented.")
        raise NotImplementedError("Production repository is not yet implemented. Use MockDataRepository for testing.")

    def get_hplc_data(self) -> pd.DataFrame:
        raise NotImplementedError("Production repository is not implemented")

    def get_deviations_data(self) -> pd.DataFrame:
        raise NotImplementedError("Production repository is not implemented")

    def get_stability_data(self) -> pd.DataFrame:
        raise NotImplementedError("Production repository is not implemented")

    def get_audit_log(self) -> pd.DataFrame:
        raise NotImplementedError("Production repository is not implemented")
    
    def write_audit_log(self, user: str, action: str, details: str, record_id: str = 'N/A') -> None:
        raise NotImplementedError("Production repository is not implemented")

    def update_deviation_status(self, dev_id: str, new_status: str) -> None:
        raise NotImplementedError("Production repository is not implemented")

    def create_deviation(self, title: str, linked_record: str, priority: str = "Medium") -> str:
        raise NotImplementedError("Production repository is not implemented")
