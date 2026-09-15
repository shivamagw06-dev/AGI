"""Event schema registry — versioned, non-silent payload changes."""

from __future__ import annotations

from typing import Any

from app.ib.config import EVENT_TYPES, SCHEMA_VERSION
from app.ib.models import SchemaEntry
from app.ib.store import IbStore

# Minimal required payload keys per event type (additive validation).
_REQUIRED: dict[str, list[str]] = {
    "DocumentDiscovered": ["url"],
    "EvidenceVerified": ["evidence_id"],
    "InvestmentThesisUpdated": ["company_symbol"],
    "ForecastUpdated": ["company_symbol"],
    "ForecastResolved": ["company_symbol"],
    "CorporateEventDetected": ["event_title"],
    "CompanyUpdated": ["company_symbol"],
    "CacheInvalidated": ["scopes"],
}


class SchemaRegistry:
    def __init__(self, store: IbStore) -> None:
        self.store = store
        self._bootstrapped = False

    def bootstrap(self) -> int:
        if self._bootstrapped and self.store.schemas:
            return len(self.store.schemas)
        n = 0
        for event_type, category in EVENT_TYPES.items():
            key = f"{event_type}:{SCHEMA_VERSION}"
            if key not in self.store.schemas:
                self.store.put_schema(
                    SchemaEntry(
                        event_type=event_type,
                        schema_version=SCHEMA_VERSION,
                        category=category,
                        required_payload_keys=list(_REQUIRED.get(event_type, [])),
                    )
                )
                n += 1
        self._bootstrapped = True
        return n

    def list_schemas(self, event_type: str | None = None) -> list[dict[str, Any]]:
        rows = [s.to_dict() for s in self.store.schemas.values()]
        if event_type:
            rows = [r for r in rows if r["event_type"] == event_type]
        rows.sort(key=lambda r: (r["category"], r["event_type"], r["schema_version"]))
        return rows

    def get(self, event_type: str, schema_version: str = SCHEMA_VERSION) -> SchemaEntry | None:
        return self.store.schemas.get(f"{event_type}:{schema_version}")

    def validate(self, event_type: str, payload: dict[str, Any], schema_version: str = SCHEMA_VERSION) -> list[str]:
        """Return list of validation errors (empty = ok). Unknown types allowed with warning."""
        errors: list[str] = []
        entry = self.get(event_type, schema_version)
        if entry is None:
            if event_type not in EVENT_TYPES:
                errors.append(f"unknown_event_type:{event_type}")
            return errors
        if entry.deprecated:
            errors.append(f"deprecated_schema:{event_type}:{schema_version}")
        for key in entry.required_payload_keys:
            if key not in (payload or {}):
                errors.append(f"missing_payload_key:{key}")
        return errors
