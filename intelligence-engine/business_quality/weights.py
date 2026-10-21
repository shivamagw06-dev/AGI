"""Load configurable pillar weights from FKB (no hardcoded magic numbers in scoring)."""

from __future__ import annotations

from typing import Any

from business_quality.schema import PILLARS


def load_pillar_weights() -> dict[str, Any]:
    """Return {pillar_id: weight} from FKB; renormalization happens at score time."""
    try:
        from financial_knowledge import knowledge

        rows = knowledge.list_quality_weights()
        weights = {str(r["id"]): float(r["weight"]) for r in rows if r.get("id") is not None}
        source = "fkb"
        # Ensure all known pillars present if FKB partial
        for p in PILLARS:
            weights.setdefault(p, 0.0)
    except Exception:  # noqa: BLE001
        from financial_knowledge.quality_weights.catalog import weight_map

        weights = weight_map()
        source = "fkb_catalog_direct"

    total = sum(weights.values()) or 1.0
    return {
        "weights": weights,
        "sum": total,
        "source": source,
        "configurable": True,
        "hardcoded_magic_numbers": False,
    }
