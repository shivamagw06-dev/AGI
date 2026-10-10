"""CCI-01 — Cross-Company Intelligence (relationship reasoning over KG-01)."""

from institutional_cross_company.models import InstitutionalRelationship
from institutional_cross_company.relationship_registry import register_relationship_provider
from institutional_cross_company.schema import CCI_VERSION, CCI_WORKSTREAM_ID

__all__ = [
    "InstitutionalRelationship",
    "register_relationship_provider",
    "CCI_VERSION",
    "CCI_WORKSTREAM_ID",
]
