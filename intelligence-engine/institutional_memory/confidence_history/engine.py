"""Confidence history — changes, reasons, evidence improvements, missing evidence."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company


def confidence_evolution(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "history": []}
    hist = list(company.get("confidence_history") or [])
    deltas = []
    for i in range(1, len(hist)):
        prev, cur = hist[i - 1], hist[i]
        deltas.append(
            {
                "from_date": prev.get("date"),
                "to_date": cur.get("date"),
                "from": prev.get("confidence"),
                "to": cur.get("confidence"),
                "delta": round(float(cur.get("confidence") or 0) - float(prev.get("confidence") or 0), 3),
                "reason": cur.get("reason"),
            }
        )
    return {
        "found": True,
        "ticker": company["ticker"],
        "history": hist,
        "changes": deltas,
        "confidence_evolution_recorded": len(hist) >= 1,
        "rule": "Confidence evolution recorded with reasons and missing evidence",
    }
