"""Explainability — Why does CompanyMemory say this?"""

from __future__ import annotations

from typing import Any

from knowledge_delta_engine.util import deep_get


def explain_observation(
    memory: dict[str, Any],
    *,
    topic: str = "management_confidence",
) -> dict[str, Any]:
    """
    Trace a high-level observation back to structured evidence with provenance.
    """
    topic = (topic or "").lower().strip()
    lineage = list(memory.get("lineage") or [])
    compiled_at = memory.get("compiled_at")

    if topic in {"management_confidence", "management", "confidence"}:
        corp = memory.get("corporate_history") or {}
        strategy = corp.get("strategy_evolution") or {}
        years = []
        for key, row in sorted(strategy.items()):
            themes = row.get("strategy_themes") or []
            tone = "Positive" if themes and "covid shock" not in " ".join(themes).lower() else "Mixed"
            if any("guidance" in t.lower() and "lower" in t.lower() for t in themes):
                tone = "Cautious"
            years.append({"period": key, "tone": tone, "themes": themes, "events": row.get("sample_events")})
        # Ownership stability as supporting signal
        own = ((memory.get("ownership_history") or {}).get("trends") or {}).get("promoter") or {}
        latest_cc = None
        events = (memory.get("event_timeline") or {}).get("events") or []
        for e in reversed(events):
            title = str(e.get("title") or "").lower()
            if "guidance" in title or "result" in title or "board" in title:
                latest_cc = e
                break
        positive_n = sum(1 for y in years[-3:] if y.get("tone") == "Positive")
        level = "HIGH" if positive_n >= 2 and own.get("direction") in {"stable", "rising", "unknown", None} else (
            "MODERATE" if years else "LOW"
        )
        because = [{"period": y["period"], "signal": y["tone"], "themes": y["themes"]} for y in years[-4:]]
        if latest_cc:
            because.append(
                {
                    "period": latest_cc.get("date"),
                    "signal": "Latest event",
                    "title": latest_cc.get("title"),
                    "source": latest_cc.get("source"),
                }
            )
        return {
            "topic": "management_confidence",
            "conclusion": level,
            "because": because,
            "supporting": {
                "promoter_trend": own,
                "corporate_observations": corp.get("observations") or [],
            },
            "provenance": {
                "compiled_at": compiled_at,
                "memory_version": memory.get("memory_version"),
                "lineage": lineage,
                "sources": ["corporate_history", "event_timeline", "ownership_history"],
            },
            "question": "Why does CompanyMemory say this?",
        }

    if topic in {"valuation", "valuation_stance", "premium"}:
        vh = memory.get("valuation_history") or {}
        rel = (vh.get("relative") or {}).get("pe") or {}
        band = ((vh.get("historical_bands") or {}).get("pe") or {})
        return {
            "topic": "valuation",
            "conclusion": vh.get("stance") or "unknown",
            "because": [
                {"signal": "current_pe", "value": (vh.get("current") or {}).get("pe")},
                {"signal": "peer_median_pe", "value": rel.get("peer_median") if isinstance(rel, dict) else None},
                {"signal": "premium_pct", "value": rel.get("premium_pct") if isinstance(rel, dict) else None},
                {"signal": "reasons", "value": rel.get("reasons") if isinstance(rel, dict) else None},
                {"signal": "historical_percentile", "value": band.get("percentile")},
                {"signal": "observations", "value": vh.get("observations") or []},
            ],
            "provenance": {
                "compiled_at": compiled_at,
                "memory_version": memory.get("memory_version"),
                "lineage": lineage,
                "sources": ["valuation_history", "valuation_intelligence"],
            },
            "question": "Why does CompanyMemory say this?",
        }

    if topic in {"ownership", "fii", "promoter"}:
        oh = memory.get("ownership_history") or {}
        return {
            "topic": "ownership",
            "conclusion": "; ".join(oh.get("observations") or []) or "ownership snapshot",
            "because": [
                {"signal": "latest", "value": oh.get("latest")},
                {"signal": "trends", "value": oh.get("trends")},
            ],
            "provenance": {
                "compiled_at": compiled_at,
                "memory_version": memory.get("memory_version"),
                "lineage": lineage,
                "sources": ["ownership_history", "ownership_intelligence"],
            },
            "question": "Why does CompanyMemory say this?",
        }

    # Generic path explain
    value = deep_get(memory, topic) if "." in topic else memory.get(topic)
    return {
        "topic": topic,
        "conclusion": value,
        "because": [{"signal": "direct_field", "path": topic, "value": value}],
        "provenance": {
            "compiled_at": compiled_at,
            "memory_version": memory.get("memory_version"),
            "lineage": lineage,
        },
        "question": "Why does CompanyMemory say this?",
    }
