"""Prediction tracking & self-evaluation — 3m / 6m / 12m horizons (KIP P1)."""

from __future__ import annotations

import datetime as _dt
import re

from app.kip.models import KipDocument, PredictionEvalRequest, PredictionRecord, PredictionStats


_RETURN_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*%")


def extract_predictions_from_document(doc: KipDocument) -> list[PredictionRecord]:
    """Create open prediction records from AGI documents with thesis/targets."""
    if not (doc.document.source or "").lower().startswith("agi"):
        return []
    if not doc.research.investment_thesis and not doc.research.target_prices:
        return []
    preds: list[PredictionRecord] = []
    predicted_at = doc.document.date or _dt.date.today()
    target = doc.research.target_prices[0] if doc.research.target_prices else ""
    expected = doc.research.expected_return or _infer_expected_return(doc)
    horizon = _parse_horizon_days(doc.research.time_horizon)
    for t in doc.investment.tickers or ["UNKNOWN"]:
        preds.append(
            PredictionRecord(
                ticker=t.upper(),
                document_id=doc.document_id,
                article_id=doc.article_id,
                thesis=doc.research.investment_thesis[:1000],
                target_price=target,
                expected_return=expected,
                catalysts=list(doc.research.catalysts[:8]),
                sector=(doc.investment.sectors[0] if doc.investment.sectors else ""),
                analyst=doc.document.author or "AGI",
                predicted_at=predicted_at,
                horizon_days=horizon,
            )
        )
    return preds


def evaluate_prediction(pred: PredictionRecord, req: PredictionEvalRequest) -> PredictionRecord:
    as_of = req.as_of or _dt.date.today()
    age_days = (as_of - pred.predicted_at).days
    if age_days >= 365:
        status = "evaluated_12m"
    elif age_days >= 180:
        status = "evaluated_6m"
    else:
        status = "evaluated_3m"

    expected_sign = _expected_direction(pred.expected_return)
    hit = None
    if expected_sign is not None:
        hit = (req.outcome_return >= 0) if expected_sign >= 0 else (req.outcome_return < 0)
    elif pred.target_price:
        # without market price, treat positive outcome as hit when bullish language present
        hit = req.outcome_return >= 0

    thesis_success = req.thesis_success
    if thesis_success is None and hit is not None:
        thesis_success = hit

    return pred.model_copy(
        update={
            "status": status,
            "outcome_return": req.outcome_return,
            "hit": hit,
            "thesis_success": thesis_success,
            "catalyst_hit": req.catalyst_hit,
            "evaluated_at": as_of,
            "notes": req.notes,
        }
    )


def compute_stats(predictions: list[PredictionRecord], *, ticker: str | None = None) -> PredictionStats:
    rows = predictions
    if ticker:
        rows = [p for p in rows if p.ticker.upper() == ticker.upper()]
    evaluated = [p for p in rows if p.hit is not None]
    hit_rate = (
        round(sum(1 for p in evaluated if p.hit) / len(evaluated), 4) if evaluated else None
    )
    avg_ret = (
        round(sum(p.outcome_return or 0.0 for p in evaluated) / len(evaluated), 4)
        if evaluated
        else None
    )
    thesis_rows = [p for p in evaluated if p.thesis_success is not None]
    thesis_rate = (
        round(sum(1 for p in thesis_rows if p.thesis_success) / len(thesis_rows), 4)
        if thesis_rows
        else None
    )
    cat_rows = [p for p in evaluated if p.catalyst_hit is not None]
    cat_rate = (
        round(sum(1 for p in cat_rows if p.catalyst_hit) / len(cat_rows), 4) if cat_rows else None
    )

    sector_accuracy: dict[str, float] = {}
    by_sector: dict[str, list[PredictionRecord]] = {}
    for p in evaluated:
        key = p.sector or "unknown"
        by_sector.setdefault(key, []).append(p)
    for sector, items in by_sector.items():
        sector_accuracy[sector] = round(sum(1 for p in items if p.hit) / len(items), 4)

    analyst_accuracy: dict[str, float] = {}
    by_analyst: dict[str, list[PredictionRecord]] = {}
    for p in evaluated:
        key = p.analyst or "unknown"
        by_analyst.setdefault(key, []).append(p)
    for analyst, items in by_analyst.items():
        analyst_accuracy[analyst] = round(sum(1 for p in items if p.hit) / len(items), 4)

    return PredictionStats(
        ticker=ticker.upper() if ticker else None,
        predictions=len(rows),
        evaluated=len(evaluated),
        hit_rate=hit_rate,
        average_return=avg_ret,
        thesis_success_rate=thesis_rate,
        catalyst_accuracy=cat_rate,
        sector_accuracy=sector_accuracy,
        analyst_accuracy=analyst_accuracy,
    )


def _infer_expected_return(doc: KipDocument) -> str:
    text = doc.cleaned_content or doc.content or ""
    m = re.search(r"expected return[^.\n]{0,40}?(-?\d+(?:\.\d+)?\s*%)", text, re.I)
    if m:
        return m.group(1).strip()
    m = _RETURN_RE.search(doc.research.valuation or "")
    return m.group(0) if m else ""


def _parse_horizon_days(horizon: str) -> int:
    h = (horizon or "").lower()
    if "12" in h or "year" in h or "12m" in h:
        return 365
    if "6" in h or "6m" in h:
        return 180
    if "3" in h or "quarter" in h or "3m" in h:
        return 90
    return 90


def _expected_direction(expected_return: str) -> int | None:
    if not expected_return:
        return None
    m = _RETURN_RE.search(expected_return)
    if not m:
        low = expected_return.lower()
        if any(w in low for w in ("upside", "outperform", "buy", "overweight")):
            return 1
        if any(w in low for w in ("downside", "underperform", "sell", "underweight")):
            return -1
        return None
    return 1 if float(m.group(1)) >= 0 else -1
