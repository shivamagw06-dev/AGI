"""Schema Evolution resolve — as-of + reporting-standard aware label mapping."""

from __future__ import annotations

from datetime import date
from typing import Any

from financial_statements_engine.metric_registry.service import resolve as registry_resolve
from financial_statements_engine.schema_evolution.seed import seed_mappings
from financial_statements_engine.schema_evolution.schema import VERSION


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


class SchemaEvolutionService:
    def __init__(self, mappings: list[dict[str, Any]] | None = None) -> None:
        self._mappings = list(mappings if mappings is not None else seed_mappings())

    def list_mappings(self) -> list[dict[str, Any]]:
        return [dict(m) for m in self._mappings]

    def resolve_label(
        self,
        label: str,
        *,
        as_of: str | None = None,
        reporting_standard: str | None = "IND_AS",
        taxonomy: str | None = None,
    ) -> dict[str, Any]:
        """Resolve a filing label to a canonical metric using evolution rules, then Metric Registry."""
        as_of_d = _parse_date(as_of) or date.today()
        standard = (reporting_standard or "IND_AS").upper()
        candidates: list[dict[str, Any]] = []
        for m in self._mappings:
            if m.get("status") != "active":
                continue
            labels = {str(m.get("label") or ""), *[str(s) for s in (m.get("synonyms") or [])]}
            if label not in labels and label.lower() not in {x.lower() for x in labels}:
                continue
            standards = [str(s).upper() for s in (m.get("reporting_standards") or [])]
            if standard not in standards and "OTHER" not in standards:
                continue
            if taxonomy and m.get("taxonomy") and taxonomy != m.get("taxonomy"):
                continue
            eff_from = _parse_date(m.get("effective_from"))
            eff_to = _parse_date(m.get("effective_to"))
            if eff_from and as_of_d < eff_from:
                continue
            if eff_to and as_of_d > eff_to:
                continue
            candidates.append(m)

        if candidates:
            # Prefer exact taxonomy match, then latest effective_from
            candidates.sort(
                key=lambda r: (
                    0 if taxonomy and r.get("taxonomy") == taxonomy else 1,
                    r.get("effective_from") or "",
                ),
                reverse=True,
            )
            chosen = candidates[0]
            return {
                "ok": True,
                "input": label,
                "canonical": chosen.get("canonical_metric"),
                "via": "schema_evolution",
                "mapping": chosen,
                "schema_evolution_version": VERSION,
            }

        # Fallback: Metric Registry (still no parser-local maps)
        canon = registry_resolve(label)
        return {
            "ok": canon is not None,
            "input": label,
            "canonical": canon,
            "via": "metric_registry" if canon else None,
            "mapping": None,
            "schema_evolution_version": VERSION,
        }


_SERVICE = SchemaEvolutionService()


def get_service() -> SchemaEvolutionService:
    return _SERVICE


def resolve_label(label: str, **kwargs: Any) -> dict[str, Any]:
    return _SERVICE.resolve_label(label, **kwargs)
