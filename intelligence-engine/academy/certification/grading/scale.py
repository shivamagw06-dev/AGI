"""ACS grading scale — institutional bands."""

from __future__ import annotations

from typing import Any

# (min_inclusive, max_inclusive, letter, label)
BANDS: list[tuple[float, float, str, str]] = [
    (95.0, 100.0, "A+", "Institutional Excellence"),
    (90.0, 94.99, "A", "Institutional Ready"),
    (85.0, 89.99, "B+", "Professional"),
    (80.0, 84.99, "B", "Competent"),
    (70.0, 79.99, "C", "Developing"),
    (60.0, 69.99, "D", "Weak"),
    (0.0, 59.99, "F", "Fail"),
]


def band_for(score: float) -> dict[str, Any]:
    s = max(0.0, min(100.0, float(score)))
    if s >= 95.0:
        return {"letter": "A+", "label": "Institutional Excellence", "score": round(s, 2)}
    if s >= 90.0:
        return {"letter": "A", "label": "Institutional Ready", "score": round(s, 2)}
    if s >= 85.0:
        return {"letter": "B+", "label": "Professional", "score": round(s, 2)}
    if s >= 80.0:
        return {"letter": "B", "label": "Competent", "score": round(s, 2)}
    if s >= 70.0:
        return {"letter": "C", "label": "Developing", "score": round(s, 2)}
    if s >= 60.0:
        return {"letter": "D", "label": "Weak", "score": round(s, 2)}
    return {"letter": "F", "label": "Fail", "score": round(s, 2)}


def is_pass(score: float, *, floor: float = 80.0) -> bool:
    return float(score) >= floor
