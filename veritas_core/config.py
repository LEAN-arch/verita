# ==============================================================================
# Configuration Module for VERITAS Application
#
# Author: Principal Engineer SME
# Last Updated: 2025-07-20
#
# Description:
# Centralizes application-wide settings for the VERITAS application, including
# database connections, session configurations, and module-specific settings.
# Replaces the missing 'settings' module to ensure compatibility across all modules.
# ==============================================================================

import logging
from typing import Any, Dict

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppConfig:
    """
    Application configuration class for VERITAS.

    Attributes:
        app (AppSettings): Application-specific settings for modules.
    """
    class AppSettings:
        """Nested class for module-specific settings."""
        def __init__(self):
            # Process Capability settings (for process_capability_dashboard.py, regulatory_support.py)
            self.process_capability = type('ProcessCapability', (), {
                'available_cqas': ['purity', 'main_impurity'],
                'spec_limits': {
                    'purity': type('Limits', (), {'lsl': 95.0, 'usl': 105.0}),
                    'main_impurity': type('Limits', (), {'lsl': 0.0, 'usl': 1.0})
                }
            })()

            # Stability settings (for stability_program_dashboard.py)
            self.stability_specs = type('StabilitySpecs', (), {
                'spec_limits': {
                    'purity': type('Limits', (), {'lsl': 95.0, 'usl': 105.0}),
                    'main_impurity': type('Limits', (), {'lsl': 0.0, 'usl': 1.0})
                }
            })()

            # Deviation Management settings (for deviation_hub.py)
            self.deviation_management = type('DeviationManagement', (), {
                'kanban_states': ['Open', 'In Progress', 'Under Review', 'Closed']
            })()

    def __init__(self):
        try:
            self.app = self.AppSettings()
        except Exception as e:
            logger.error(f"Failed to initialize AppConfig: {str(e)}")
            raise RuntimeError(f"AppConfig initialization failed: {str(e)}")

# Singleton instance of AppConfig
try:
    config = AppConfig()
except Exception as e:
    logger.error(f"Failed to create AppConfig instance: {str(e)}")
    raise RuntimeError(f"AppConfig creation failed: {str(e)}")
