# ==============================================================================
# Core Module: Abstracted Data Repository
#
# Author: Principal Engineer SME
# Last Updated: 2023-10-29 (Ultimate Version)
#
# Description:
# This module implements the Repository Pattern to completely abstract the
# data source from the application logic. It defines a contract (ABC) for what
# data operations are required and provides concrete implementations for both
# a mock data factory and a (template for a) production database.
#
# This is a critical architectural choice for building a scalable, testable,
# and maintainable enterprise application.
# ==============================================================================

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
from . import settings

# --- 1. Abstract Base Class (The "Contract") ---

class DataRepository(ABC):
    """
    Abstract Base Class defining the contract for all data repositories.
    Any class that provides data to the VERITAS app must implement these methods.
    """
    @abstractmethod
    def get_hplc_data(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_deviations_data(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_stability_data(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_audit_log(self) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def write_audit_log(self, user: str, action: str, details: str, record_id: str = 'N/A'):
        pass
        
    @abstractmethod
    def update_deviation_status(self, dev_id: str, new_status: str):
        pass

    @abstractmethod
    def create_deviation(self, title: str, linked_record: str, priority: str = "Medium") -> str:
        pass

# --- 2. Concrete Implementation: Mock Data Factory ---
# This class fulfills the DataRepository contract using in-memory mock data.
# It is used for development, testing, and demonstration purposes.

class MockDataRepository(DataRepository):
    """
    A concrete implementation of the DataRepository that generates and serves
    a cohesive, realistic set of mock data.
    """
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self._load_all_data()

    def _load_all_data(self):
        """Generates all datasets in a dependent sequence for cohesion."""
        self.hplc_df = self._generate_hplc_data(num_samples=500)
        self.deviations_df = self._generate_deviations_data()
        self.stability_df = self._generate_stability_data()
        self.audit_df = self._generate_audit_trail(num_entries=300)

    # --- Data Generation Methods (formerly the MockDataFactory class) ---
    def _generate_hplc_data(self, num_samples=500):
        start_time = datetime(2024, 4, 1)
        data = {
            'sample_id': [f'SMP-{1000+i}' for i in range(num_samples)],
            'batch_id': self.rng.choice(['B01-A', 'B01-B', 'B02-A', 'B02-B', 'B03-A'], size=num_samples),
            'study_id': self.rng.choice(['VX-809-PK-01', 'VX-561-Tox-03', 'VX-121-Stab-02', 'VX-984-Form-05'], size=num_samples, p=[0.3, 0.3, 0.2, 0.2]),
            'injection_time': pd.to_datetime([start_time + timedelta(hours=1.5*i) for i in range(num_samples)]),
            'Purity': self.rng.normal(loc=99.5, scale=0.2, size=num_samples),
            'Aggregate Content': self.rng.normal(loc=0.5, scale=0.1, size=num_samples),
            'Main Impurity': self.rng.normal(loc=0.2, scale=0.05, size=num_samples),
            'Bio-activity': self.rng.normal(loc=105, scale=5, size=num_samples),
            'instrument_id': self.rng.choice(['HPLC-01', 'HPLC-02', 'HPLC-03', 'UPLC-01'], size=num_samples, p=[0.4, 0.3, 0.15, 0.15]),
            'analyst': self.rng.choice(['A. Turing', 'M. Curie', 'R. Franklin', 'L. Meitner'], size=num_samples)
        }
        df = pd.DataFrame(data)
        # Inject anomalies and clip values...
        df.loc[10, 'Purity'] = 97.8 
        df.loc[50, 'Bio-activity'] = 205.0
        df['Purity'] = df['Purity'].clip(97.0, 100)
        df['Aggregate Content'] = df['Aggregate Content'].clip(0, 1)
        df['Main Impurity'] = df['Main Impurity'].clip(0, 1.0)
        return df

    def _generate_deviations_data(self):
        deviations = [
            {"id": "DEV-001", "title": "OOS Result in VX-809-PK-01", "status": "New", "priority": "High", "linked_record": "SMP-1010"},
            {"id": "DEV-002", "title": "HPLC-03 Calibration Drift", "status": "In Progress", "priority": "Medium", "linked_record": "HPLC-03"},
            {"id": "DEV-003", "title": "TAT Breach for Lot B02-A", "status": "In Progress", "priority": "Medium", "linked_record": "B02-A"},
            {"id": "DEV-004", "title": "Contamination in Stab Chamber", "status": "Pending QA", "priority": "High", "linked_record": "STAB-CH-03"},
        ]
        return pd.DataFrame(deviations)

    def _generate_stability_data(self):
        data = []
        products = {'VX-561': (99.5, 0.1), 'VX-809': (99.8, 0.05)}
        lots = ['A202301', 'A202302', 'B202301', 'B202302']
        timepoints = [0, 3, 6, 9, 12, 18, 24]
        for product, (p_start, i_start) in products.items():
            for lot in lots:
                seed = hash(f"{product}{lot}") % (2**32 - 1); lot_rng = np.random.default_rng(seed)
                for t in timepoints:
                    purity = p_start - (t * lot_rng.uniform(0.05, 0.08)) - lot_rng.uniform(0, 0.1)
                    impurity = i_start + (t * lot_rng.uniform(0.01, 0.02)) + lot_rng.uniform(0, 0.05)
                    data.append({'product_id': product, 'lot_id': lot, 'Timepoint (Months)': t, 'Purity (%)': purity, 'Main Impurity (%)': impurity})
        return pd.DataFrame(data)

    def _generate_audit_trail(self, num_entries=300):
        users = ['DTE-System', 'A. Turing', 'R. Franklin', 'QA.Bot', 'M. Curie']
        actions = list(settings.APP.audit_trail.action_icons.keys())
        record_ids = self.hplc_df['sample_id'].tolist() + self.deviations_df['id'].tolist()
        log = []
        for i in range(num_entries):
            log.append({
                'Timestamp': datetime.now() - timedelta(hours=i * 1.3, minutes=int(self.rng.integers(0, 59))),
                'User': self.rng.choice(users), 'Action': self.rng.choice(actions),
                'Record ID': self.rng.choice(record_ids), 'Details': "Routine system operation."
            })
        return pd.DataFrame(log).sort_values('Timestamp', ascending=False).reset_index(drop=True)

    # --- Data Access Methods (fulfilling the contract) ---
    def get_hplc_data(self) -> pd.DataFrame:
        return self.hplc_df.copy()

    def get_deviations_data(self) -> pd.DataFrame:
        return self.deviations_df.copy()

    def get_stability_data(self) -> pd.DataFrame:
        return self.stability_df.copy()

    def get_audit_log(self) -> pd.DataFrame:
        return self.audit_df.copy()

    # --- Data Mutation Methods (simulating database writes) ---
    def write_audit_log(self, user: str, action: str, details: str, record_id: str = 'N/A'):
        log_entry = {'Timestamp': pd.to_datetime(datetime.now()), 'User': user, 'Action': action, 'Record ID': record_id, 'Details': details}
        new_row_df = pd.DataFrame([log_entry])
        self.audit_df = pd.concat([new_row_df, self.audit_df], ignore_index=True)
        st.toast(f"Action Logged: {action}", icon="📝")

    def update_deviation_status(self, dev_id: str, new_status: str):
        self.deviations_df.loc[self.deviations_df['id'] == dev_id, 'status'] = new_status
    
    def create_deviation(self, title: str, linked_record: str, priority: str = "Medium") -> str:
        new_id = f"DEV-{len(self.deviations_df) + 1:03d}"
        new_dev = {'id': new_id, 'title': title, 'status': 'New', 'priority': priority, 'linked_record': linked_record}
        self.deviations_df = pd.concat([self.deviations_df, pd.DataFrame([new_dev])], ignore_index=True)
        return new_id


# --- 3. Concrete Implementation: Production Database ---
# This class is a template for what would be built to connect to a real database
# like Snowflake. It fulfills the same contract.

class ProdDataRepository(DataRepository):
    """
    A concrete implementation of the DataRepository that connects to and queries
    the production data warehouse (e.g., Snowflake).
    NOTE: This is a placeholder for the actual production implementation.
    """
    def __init__(self, conn_params: dict):
        # In a real app, this would use the params to create a live DB connection
        # self.connection = snowflake.connector.connect(**conn_params)
        st.info("NOTE: Using **Mock Repository**. Production database connector is not yet implemented.")
        self.mock_repo = MockDataRepository() # For demonstration, this class will just wrap the mock repo.

    # --- In a real implementation, these methods would execute SQL queries ---
    def get_hplc_data(self) -> pd.DataFrame:
        # sql = "SELECT * FROM PROD_DATA_WAREHOUSE.VERITAS_REPORTING.HPLC_RESULTS_VW;"
        # return pd.read_sql(sql, self.connection)
        return self.mock_repo.get_hplc_data()

    def get_deviations_data(self) -> pd.DataFrame:
        return self.mock_repo.get_deviations_data()

    def get_stability_data(self) -> pd.DataFrame:
        return self.mock_repo.get_stability_data()

    def get_audit_log(self) -> pd.DataFrame:
        return self.mock_repo.get_audit_log()
    
    def write_audit_log(self, user: str, action: str, details: str, record_id: str = 'N/A'):
        # In production, this would execute an INSERT statement.
        # with self.connection.cursor() as cursor:
        #     cursor.execute("INSERT INTO ...", (params))
        self.mock_repo.write_audit_log(user, action, details, record_id)

    def update_deviation_status(self, dev_id: str, new_status: str):
        self.mock_repo.update_deviation_status(dev_id, new_status)

    def create_deviation(self, title: str, linked_record: str, priority: str = "Medium") -> str:
        return self.mock_repo.create_deviation(title, linked_record, priority)
