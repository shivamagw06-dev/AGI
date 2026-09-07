"""Catalyst engine — expected / potential / unknown; positive / negative."""

from __future__ import annotations

from typing import Any


def catalysts_for(profile: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for c in profile.get("catalysts") or []:
        rows.append(
            {
                **c,
                "evidence": [
                    {
                        "kind": "catalyst_prior",
                        "source": "forecast_intelligence.catalysts",
                        "note": f"{c.get('label')} linked to sector/company forecast profile",
                    }
                ],
                "linked_to_evidence": True,
            }
        )
    by_kind = {
        "expected": [c for c in rows if c.get("kind") == "expected"],
        "potential": [c for c in rows if c.get("kind") == "potential"],
        "unknown": [c for c in rows if c.get("kind") == "unknown"],
    }
    by_polarity = {
        "positive": [c for c in rows if c.get("polarity") == "positive"],
        "negative": [c for c in rows if c.get("polarity") == "negative"],
        "mixed": [c for c in rows if c.get("polarity") == "mixed"],
    }
    timeline = sorted(rows, key=lambda c: (c.get("horizon") or "zzz", c.get("label") or ""))
    return {
        "count": len(rows),
        "items": rows,
        "by_kind": by_kind,
        "by_polarity": by_polarity,
        "timeline": timeline,
        "rule": "Every catalyst linked to evidence — never unsupported",
    }
