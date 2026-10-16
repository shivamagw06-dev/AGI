"""Accounting Policy Engine — track material policy changes."""

from __future__ import annotations

from typing import Any


def policy_score(policies: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = list(policies or [])
    material = [p for p in rows if str(p.get("materiality") or "").lower() == "material"]
    score = 90.0 - 25.0 * len(material) - 3.0 * max(0, len(rows) - len(material))
    score = max(0.0, min(100.0, score))
    return {
        "accounting_consistency": round(score, 1),
        "policy_changes": rows,
        "material_changes": material,
        "material_count": len(material),
        "non_material_count": len(rows) - len(material),
        "flag": "Material" if material else ("Non-material" if rows else "None disclosed"),
    }
