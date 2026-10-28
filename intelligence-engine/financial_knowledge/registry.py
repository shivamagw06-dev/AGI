"""FKB registry API — knowledge.metric / ratio / relationship / threshold / glossary."""

from __future__ import annotations

from typing import Any

from financial_knowledge.confidence import all_modifiers, get_modifier
from financial_knowledge.glossary import all_glossary, get_glossary
from financial_knowledge.metrics import all_metrics, get_metric
from financial_knowledge.quality_weights import all_quality_weights, get_quality_weight
from financial_knowledge.ratios import all_ratios, get_ratio
from financial_knowledge.relationships import all_relationships, get_relationship
from financial_knowledge.schema import VERSION, WORKSTREAM_ID
from financial_knowledge.sectors import all_sectors, get_sector
from financial_knowledge.thresholds import all_thresholds, get_threshold


class KnowledgeRegistry:
    """Read-only façade for institutional financial knowledge."""

    version = VERSION
    workstream_id = WORKSTREAM_ID

    def metric(self, name: str) -> dict[str, Any] | None:
        return get_metric(name)

    def ratio(self, name: str) -> dict[str, Any] | None:
        return get_ratio(name)

    def relationship(self, name: str) -> dict[str, Any] | None:
        return get_relationship(name)

    def threshold(self, name: str, *, sector: str | None = None) -> dict[str, Any] | None:
        return get_threshold(name, sector=sector)

    def glossary(self, name: str) -> dict[str, Any] | None:
        return get_glossary(name)

    def sector(self, name: str) -> dict[str, Any] | None:
        return get_sector(name)

    def confidence(self, name: str) -> dict[str, Any] | None:
        return get_modifier(name)

    def quality_weight(self, name: str) -> dict[str, Any] | None:
        """Additive FIRE-06 pillar weight definitions (knowledge only)."""
        return get_quality_weight(name)

    def list_metrics(self) -> list[dict[str, Any]]:
        return all_metrics()

    def list_ratios(self) -> list[dict[str, Any]]:
        return all_ratios()

    def list_relationships(self) -> list[dict[str, Any]]:
        return all_relationships()

    def list_thresholds(self) -> list[dict[str, Any]]:
        return all_thresholds()

    def list_glossary(self) -> list[dict[str, Any]]:
        return all_glossary()

    def list_sectors(self) -> list[dict[str, Any]]:
        return all_sectors()

    def list_confidence_modifiers(self) -> list[dict[str, Any]]:
        return all_modifiers()

    def list_quality_weights(self) -> list[dict[str, Any]]:
        return all_quality_weights()

    def validate(self) -> dict[str, Any]:
        """Structural validation: unique IDs, formula presence, cross-refs."""
        errors: list[str] = []
        metric_ids = {m["id"] for m in all_metrics()}
        if len(metric_ids) != len(all_metrics()):
            errors.append("duplicate_metric_ids")
        ratio_ids = {r["id"] for r in all_ratios()}
        if len(ratio_ids) != len(all_ratios()):
            errors.append("duplicate_ratio_ids")
        for r in all_ratios():
            if not r.get("formula"):
                errors.append(f"ratio_missing_formula:{r['id']}")
            for dep in r.get("required_metrics") or []:
                if dep not in metric_ids:
                    errors.append(f"ratio_missing_metric_ref:{r['id']}:{dep}")
        for rel in all_relationships():
            for inp in rel.get("inputs") or []:
                if inp not in metric_ids:
                    errors.append(f"relationship_missing_input:{rel['id']}:{inp}")
        for m in all_metrics():
            for dep in m.get("dependencies") or []:
                if dep not in metric_ids:
                    errors.append(f"metric_missing_dependency:{m['id']}:{dep}")
        qw = all_quality_weights()
        wsum = sum(float(w.get("weight") or 0) for w in qw)
        if qw and abs(wsum - 1.0) > 1e-6:
            errors.append(f"quality_weights_sum_not_one:{wsum}")
        return {
            "ok": not errors,
            "errors": errors,
            "counts": {
                "metrics": len(metric_ids),
                "ratios": len(ratio_ids),
                "relationships": len(all_relationships()),
                "thresholds": len(all_thresholds()),
                "glossary": len(all_glossary()),
                "sectors": len(all_sectors()),
                "confidence_modifiers": len(all_modifiers()),
                "quality_weights": len(qw),
            },
            "version": VERSION,
        }


# Module-level singleton used as `knowledge`
knowledge = KnowledgeRegistry()
