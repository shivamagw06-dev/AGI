"""Shared band helpers for IDS-01 (no dependency cycles with IRE when possible)."""

from __future__ import annotations

from typing import Any


def business_quality_band_safe(value: Any) -> str:
    if isinstance(value, (int, float)):
        score = float(value)
        if score >= 85:
            return "Excellent"
        if score >= 70:
            return "Strong"
        if score >= 55:
            return "Adequate"
        return "Weak"
    text = str(value or "").strip().title()
    if text in {"Excellent", "Strong", "Adequate", "Weak"}:
        return text
    return text or "Unclear"
