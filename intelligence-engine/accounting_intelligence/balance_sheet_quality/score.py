"""Balance Sheet Quality Engine."""

from __future__ import annotations

from typing import Any


def balance_sheet_quality(block: dict[str, Any] | None) -> dict[str, Any]:
    b = block or {}
    liquidity = str(b.get("liquidity") or "adequate").lower()
    leverage = str(b.get("leverage") or "moderate").lower()
    goodwill = str(b.get("goodwill_watch") or "").lower()

    score = 65.0
    if liquidity in {"strong", "high"}:
        score += 15
    elif liquidity in {"weak", "tight"}:
        score -= 20
    if leverage in {"low", "net_cash", "regulated_bank"}:
        score += 10
    elif leverage in {"high", "elevated"}:
        score -= 15
    if "monitor" in goodwill or "watch" in goodwill:
        score -= 5
    cet1 = b.get("cet1")
    if cet1 is not None:
        try:
            if float(cet1) >= 14:
                score += 5
        except Exception:
            pass
    gnpa = b.get("gnpa")
    if gnpa is not None:
        try:
            if float(gnpa) > 3:
                score -= 10
        except Exception:
            pass
    score = max(0.0, min(100.0, score))

    return {
        "balance_sheet_quality": round(score, 1),
        "liquidity": liquidity,
        "leverage": leverage,
        "cet1": cet1,
        "gnpa": gnpa,
        "goodwill_watch": b.get("goodwill_watch"),
        "contingent": b.get("contingent"),
        "notes": b.get("notes"),
        "evidence_doc": b.get("evidence_doc"),
    }
