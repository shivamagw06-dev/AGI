"""AIP-06 / AIP-07 Prediction + portfolio attribution."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.aip.models import AttributionReport, PredictionAttribution
from app.validation.golden.loader import GoldenDataset


def _report_id(dataset_id: str, weight_set_id: str) -> str:
    raw = f"aip_attr|{dataset_id}|{weight_set_id}"
    return "attr_" + sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_attribution(
    scored: list[dict[str, Any]],
    dataset: GoldenDataset,
    *,
    weight_set_id: str,
) -> AttributionReport:
    day_by = {d.as_of: d for d in dataset.days}
    rows: list[PredictionAttribution] = []
    for r in scored:
        g = day_by.get(r["as_of"])
        fwd = g.forward_returns.get(r["symbol"]) if g else None
        pred_up = r["score"] >= 50.0
        correct = None
        if fwd is not None:
            correct = pred_up == (float(fwd) > 0.0)
        rows.append(
            PredictionAttribution(
                as_of=r["as_of"],
                symbol=r["symbol"],
                score=float(r["score"]),
                label=str(r["label"]),
                confidence=float(r["confidence"]),
                engine_shares=dict(r.get("engine_shares") or {}),
                dominant_engine=r.get("dominant_engine"),
                forward_return=float(fwd) if fwd is not None else None,
                correct=correct,
            )
        )
    return AttributionReport(
        report_id=_report_id(dataset.dataset_id, weight_set_id),
        dataset_id=dataset.dataset_id,
        weight_set_id=weight_set_id,
        rows=rows,
        production_influence=False,
    )
