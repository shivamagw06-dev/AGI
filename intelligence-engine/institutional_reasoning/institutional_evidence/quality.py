"""Module 10 — Evidence Quality Engine.

Every metric scored on coverage, freshness, consistency, entity match,
provenance, validation. Produces Evidence Score 0–100.
Frameworks reject score < 80.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

QUALITY_VERSION = "evidence-quality-v1.0.0"
MIN_FRAMEWORK_SCORE = 80


def _parse_ts(raw: Any) -> datetime | None:
    if not raw:
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def score_metric(
    *,
    value: Any,
    entity_id: str | None,
    metric_entity: str | None,
    provider: str | None,
    as_of: str | None,
    series_n: int = 0,
    expected_n: int = 5,
    data_class: str = "seed_panel",
    validated: bool = False,
    consistency_ok: bool = True,
) -> dict[str, Any]:
    """Score one metric observation 0–100 with component breakdown."""
    components: dict[str, float] = {}

    # Coverage (0–25): series depth
    if series_n <= 0:
        components["coverage"] = 8.0 if value is not None else 0.0
    else:
        components["coverage"] = round(min(25.0, 25.0 * series_n / max(expected_n, 1)), 2)

    # Freshness (0–20)
    ts = _parse_ts(as_of)
    now = datetime.now(timezone.utc)
    if ts is None:
        # Seed panels without live timestamps get partial freshness credit
        components["freshness"] = (
            12.0 if data_class in {"seed_panel", "institutional_seed", "derived"} else 0.0
        )
    else:
        age = now - ts
        if age <= timedelta(days=7):
            components["freshness"] = 20.0
        elif age <= timedelta(days=45):
            components["freshness"] = 16.0
        elif age <= timedelta(days=180):
            components["freshness"] = 10.0
        else:
            components["freshness"] = 4.0

    # Consistency (0–15)
    components["consistency"] = 15.0 if consistency_ok else 4.0

    # Entity match (0–15)
    if entity_id and metric_entity and str(entity_id).upper() == str(metric_entity).upper():
        components["entity_match"] = 15.0
    elif entity_id and not metric_entity:
        components["entity_match"] = 0.0
    elif not entity_id:
        components["entity_match"] = 8.0
    else:
        components["entity_match"] = 0.0

    # Provenance (0–15)
    if provider:
        components["provenance"] = 15.0 if data_class in {"filing", "dvc", "live"} else 12.0
    else:
        components["provenance"] = 0.0

    # Validation (0–10)
    if validated or data_class in {"filing", "dvc", "live"}:
        components["validation"] = 10.0
    elif data_class in {"seed_panel", "institutional_seed", "derived"}:
        components["validation"] = 8.0
    else:
        components["validation"] = 3.0

    total = round(sum(components.values()), 2)
    return {
        "score": total,
        "components": components,
        "accept_for_framework": total >= MIN_FRAMEWORK_SCORE,
        "min_framework_score": MIN_FRAMEWORK_SCORE,
        "quality_version": QUALITY_VERSION,
    }


def pack_score(metric_scores: list[dict[str, Any]]) -> float:
    if not metric_scores:
        return 0.0
    vals = [float(m.get("score") or 0) for m in metric_scores]
    return round(sum(vals) / len(vals), 2)
