"""
Privacy Module for The Inner Architect

This package provides privacy compliance tools and utilities,
including PIPEDA compliance for Canadian privacy requirements.
"""

from privacy.pipeda_compliance import (
    ConsentType,
    PurposeCategory,
    ConsentRecord,
    DataAccessRequest,
    PipedaCompliance,
    get_pipeda_consent_text,
    record_flask_consent
)

__all__ = [
    'ConsentType',
    'PurposeCategory',
    'ConsentRecord',
    'DataAccessRequest',
    'PipedaCompliance',
    'get_pipeda_consent_text',
    'record_flask_consent'
]