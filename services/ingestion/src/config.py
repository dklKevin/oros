"""
Ingestion service configuration.

Extends shared config with ingestion-specific settings.
"""

from services.shared.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
