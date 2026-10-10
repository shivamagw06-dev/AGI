"""Accrual Engine — Sloan-style accrual pressure."""

from __future__ import annotations

from typing import Any


def accruals_score(block: dict[str, Any] | None) -> dict[str, Any]:
    b = block or {}
    ratio = b.get("accrual_ratio")
    try:
        ratio_f = float(ratio) if ratio is not None else 0.05
    except Exception:
        ratio_f = 0.05

    prior = str(b.get("label_prior") or "")
    if prior in {"Healthy", "Watch", "Aggressive"}:
        label = prior
    elif ratio_f <= 0.05:
        label = "Healthy"
    elif ratio_f <= 0.12:
        label = "Watch"
    else:
        label = "Aggressive"

    # Higher score = better (lower accruals)
    score = max(0.0, min(100.0, 100.0 - abs(ratio_f) * 400.0))
    if label == "Healthy":
        score = max(score, 75.0)
    elif label == "Aggressive":
        score = min(score, 40.0)

    recv = b.get("receivable_growth")
    inv = b.get("inventory_growth")
    return {
        "accruals": round(score, 1),
        "accrual_ratio": ratio_f,
        "label": label,
        "receivable_growth": recv,
        "inventory_growth": inv,
        "deferred_revenue": b.get("deferred_revenue"),
        "notes": b.get("notes"),
        "evidence_doc": b.get("evidence_doc"),
        "sloan_signal": label,
    }
