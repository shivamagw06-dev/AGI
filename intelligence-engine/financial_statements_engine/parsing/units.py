"""Unit / scale detection and normalization helpers."""

from __future__ import annotations

import re
from typing import Any

from financial_statements_engine.metric_registry.service import to_normalized_value, validate_scale

_SCALE_PATTERNS = (
    (r"\bcrores?\b", "crores"),
    (r"\blakhs?\b", "lakhs"),
    (r"\bmillions?\b", "millions"),
    (r"\bbillions?\b", "billions"),
    (r"\bthousands?\b", "thousands"),
    (r"\babsolute\b", "ones"),
)


def detect_scale(text: str | None, default: str = "crores") -> str:
    if not text:
        return default
    s = str(text).lower().replace("₹", "inr ").replace("rs.", "inr ")
    if s.startswith("inr_") or s.startswith("inr "):
        s = s.split("_")[-1] if "_" in s else s
    for pat, scale in _SCALE_PATTERNS:
        if re.search(pat, s):
            return scale
    if validate_scale(s.strip()):
        return s.strip().lower()
    return default


def normalize_unit_fields(fields: dict[str, Any], *, default_scale: str = "crores") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, payload in (fields or {}).items():
        if isinstance(payload, dict):
            reported = payload.get("value")
            scale = detect_scale(str(payload.get("unit_scale") or payload.get("unit") or default_scale), default_scale)
            row = dict(payload)
            row["unit_scale"] = scale
            row["scale"] = scale
            row["reported_value"] = reported
            row["normalized_value"] = (
                None
                if reported is None
                else to_normalized_value(reported if isinstance(reported, (int, float)) else None, scale)
            )
            out[name] = row
        else:
            out[name] = {
                "value": payload,
                "reported_value": payload,
                "unit_scale": default_scale,
                "scale": default_scale,
                "normalized_value": to_normalized_value(
                    payload if isinstance(payload, (int, float)) else None, default_scale
                ),
            }
    return {"fields": out, "layer": "unit_detection"}
