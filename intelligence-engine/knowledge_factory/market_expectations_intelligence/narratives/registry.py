"""Market narrative registry — structured themes, not news summaries."""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence import store as imei_store
from knowledge_factory.market_expectations_intelligence.schema import IMEI_VERSION


def narrative_view(narrative_id: str | None = None) -> dict[str, Any]:
    if narrative_id:
        row = imei_store.get_narrative(narrative_id)
        return {
            "narrative": row,
            "version": IMEI_VERSION,
            "fabricated": False,
            "not_news_summary": True,
        }
    rows = imei_store.list_narratives()
    # Strengthening / weakening from last evolution status
    changes = []
    for r in rows:
        evo = r.get("evolution") or []
        if len(evo) >= 2:
            changes.append(
                {
                    "narrative_id": r.get("narrative_id"),
                    "name": r.get("name"),
                    "from": evo[-2].get("status"),
                    "to": evo[-1].get("status"),
                    "as_of": evo[-1].get("available_from"),
                }
            )
        elif evo:
            changes.append(
                {
                    "narrative_id": r.get("narrative_id"),
                    "name": r.get("name"),
                    "from": None,
                    "to": evo[-1].get("status"),
                    "as_of": evo[-1].get("available_from"),
                }
            )
    return {
        "n": len(rows),
        "narratives": rows,
        "narrative_changes": changes,
        "version": IMEI_VERSION,
        "fabricated": False,
        "not_news_summary": True,
    }
