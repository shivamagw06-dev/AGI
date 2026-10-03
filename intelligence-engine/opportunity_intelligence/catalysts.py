"""Catalyst detection from compiled memory / events — no raw calendar APIs."""

from __future__ import annotations

import re
from typing import Any

from opportunity_intelligence.util import dim_result


_CATALYST_PATTERNS: tuple[tuple[str, str, str, float], ...] = (
    (r"result|earnings|q[1-4]\b", "Quarterly results", "near_term", 0.85),
    (r"investor\s*day|capital\s*markets\s*day", "Investor Day", "medium_term", 0.75),
    (r"board|agm|egm", "Board / shareholder meeting", "near_term", 0.7),
    (r"commission|capacity|plant|capex", "Capacity / project commissioning", "medium_term", 0.7),
    (r"product\s*launch|new\s*product", "Product launch", "medium_term", 0.65),
    (r"policy|regulation|approval|fda|cdsco", "Policy / regulatory event", "medium_term", 0.7),
    (r"rating|credit", "Credit rating review", "medium_term", 0.6),
    (r"buyback|dividend|bonus|split", "Capital allocation event", "near_term", 0.75),
    (r"acquisition|merger|stake", "M&A / stake event", "medium_term", 0.7),
    (r"guidance", "Guidance update", "near_term", 0.8),
)


def detect_catalysts(memory: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events = list((memory.get("event_timeline") or {}).get("events") or [])
    corp = memory.get("corporate_history") or {}
    obs = [str(o) for o in (corp.get("observations") or [])]

    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(name: str, window: str, importance: str, confidence: float, evidence: dict[str, Any]) -> None:
        key = name.lower()
        if key in seen:
            return
        seen.add(key)
        found.append(
            {
                "name": name,
                "expected_window": window,
                "importance": importance,
                "confidence": round(float(confidence), 2),
                "evidence": evidence,
            }
        )

    for e in events[-30:]:
        title = str(e.get("title") or "")
        low = title.lower()
        for pat, name, window, conf in _CATALYST_PATTERNS:
            if re.search(pat, low):
                imp = "High" if conf >= 0.8 else ("Medium" if conf >= 0.7 else "Low")
                add(
                    name if name.lower() not in low else title[:80],
                    window,
                    imp,
                    conf,
                    {"source": "event_timeline", "date": e.get("date"), "title": title},
                )
                break

    for o in obs:
        low = o.lower()
        for pat, name, window, conf in _CATALYST_PATTERNS:
            if re.search(pat, low):
                add(
                    name,
                    window,
                    "Medium" if conf >= 0.7 else "Low",
                    conf * 0.9,
                    {"source": "corporate_history.observations", "text": o[:160]},
                )
                break

    # Always surface results cadence as research-relevant if financial memory exists
    if (memory.get("financial_history") or {}).get("available") and "quarterly results" not in seen:
        add(
            "Quarterly results cadence",
            "near_term",
            "Medium",
            0.6,
            {"source": "financial_history", "note": "recurring_earnings_catalyst"},
        )

    # Deterministic order: importance then name
    imp_rank = {"High": 0, "Medium": 1, "Low": 2}
    found.sort(key=lambda c: (imp_rank.get(c.get("importance") or "", 9), c.get("name") or ""))

    # Dimension score from catalyst density / importance
    score = 40.0 + min(40.0, 8.0 * len(found))
    if any(c.get("importance") == "High" for c in found):
        score += 10
    signals = [f"{c['name']} ({c['importance']})" for c in found[:6]]
    evidence = [{"path": "catalysts", "value": c["name"], "note": c.get("expected_window")} for c in found[:8]]
    dim = dim_result(
        score=score,
        signals=signals,
        evidence=evidence,
        available=bool(found),
        coverage=90.0 if found else 0.0,
    )
    return found, dim
