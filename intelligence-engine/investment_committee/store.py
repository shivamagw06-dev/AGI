"""Forever store for committee minutes, timeline, predictions, accuracy (process-local)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


_LOCK = Lock()
_MINUTES: dict[str, list[dict[str, Any]]] = {}  # ticker -> minutes (append-only)
_PREDICTIONS: dict[str, list[dict[str, Any]]] = {}  # ticker -> prediction rows
_ACCURACY: dict[str, list[dict[str, Any]]] = {}  # ticker -> accuracy reviews


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def put_minutes(ticker: str | None, minutes: dict[str, Any]) -> dict[str, Any]:
    if not ticker:
        row = {**deepcopy(minutes), "meeting_id": str(uuid4()), "recorded_at": _now()}
        return row
    t = ticker.upper()
    row = {
        **deepcopy(minutes),
        "ticker": t,
        "meeting_id": minutes.get("meeting_id") or str(uuid4()),
        "recorded_at": _now(),
    }
    with _LOCK:
        hist = _MINUTES.setdefault(t, [])
        hist.append(row)
        # store forever within process — soft cap only to protect memory
        if len(hist) > 500:
            del hist[:-500]
    return row


def list_minutes(ticker: str | None, *, limit: int = 40) -> list[dict[str, Any]]:
    if not ticker:
        return []
    t = ticker.upper()
    with _LOCK:
        rows = list(_MINUTES.get(t) or [])
    return deepcopy(rows[-limit:])


def timeline(ticker: str | None, *, limit: int = 20) -> list[dict[str, Any]]:
    """Historical committee memory as a stance timeline."""
    rows = list_minutes(ticker, limit=limit)
    out = []
    for r in rows:
        out.append(
            {
                "meeting_id": r.get("meeting_id"),
                "recorded_at": r.get("recorded_at") or r.get("date"),
                "position": r.get("committee_position") or r.get("decision_stance") or r.get("decision"),
                "conviction": r.get("conviction"),
                "vote": r.get("vote_tally"),
                "question": r.get("question"),
            }
        )
    return out


def put_predictions(ticker: str | None, meeting_id: str, predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not ticker or not predictions:
        return predictions
    t = ticker.upper()
    rows = []
    for p in predictions:
        rows.append(
            {
                **deepcopy(p),
                "ticker": t,
                "meeting_id": meeting_id,
                "recorded_at": _now(),
                "status": "open",
            }
        )
    with _LOCK:
        bucket = _PREDICTIONS.setdefault(t, [])
        bucket.extend(rows)
        if len(bucket) > 500:
            del bucket[:-500]
    return rows


def list_open_predictions(ticker: str | None, *, limit: int = 20) -> list[dict[str, Any]]:
    if not ticker:
        return []
    t = ticker.upper()
    with _LOCK:
        rows = [r for r in (_PREDICTIONS.get(t) or []) if r.get("status") == "open"]
    return deepcopy(rows[-limit:])


def record_actuals(
    ticker: str,
    *,
    meeting_id: str | None = None,
    actuals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score prediction accountability when actuals arrive (committee reviews itself)."""
    t = (ticker or "").upper()
    actuals = actuals or []
    scored: list[dict[str, Any]] = []
    hits = 0
    total = 0
    with _LOCK:
        preds = list(_PREDICTIONS.get(t) or [])
        for pred in preds:
            if meeting_id and pred.get("meeting_id") != meeting_id:
                continue
            if pred.get("status") != "open":
                continue
            metric = str(pred.get("metric") or "").lower()
            match = None
            for a in actuals:
                if str(a.get("metric") or "").lower() == metric:
                    match = a
                    break
            if match is None:
                continue
            total += 1
            expected = pred.get("expected")
            actual = match.get("actual")
            ok = _close_enough(expected, actual)
            if ok:
                hits += 1
            pred["status"] = "reviewed"
            pred["actual"] = actual
            pred["accurate"] = ok
            pred["reviewed_at"] = _now()
            scored.append(deepcopy(pred))
        accuracy_pct = round(100.0 * hits / total, 1) if total else None
        review = {
            "ticker": t,
            "meeting_id": meeting_id,
            "reviewed_at": _now(),
            "predictions_scored": total,
            "hits": hits,
            "committee_accuracy_pct": accuracy_pct,
            "details": scored,
        }
        if total:
            bucket = _ACCURACY.setdefault(t, [])
            bucket.append(review)
            if len(bucket) > 200:
                del bucket[:-200]
    return review


def latest_accuracy(ticker: str | None) -> dict[str, Any] | None:
    if not ticker:
        return None
    t = ticker.upper()
    with _LOCK:
        rows = _ACCURACY.get(t) or []
        return deepcopy(rows[-1]) if rows else None


def _close_enough(expected: Any, actual: Any) -> bool:
    try:
        e = float(str(expected).replace("%", "").strip())
        a = float(str(actual).replace("%", "").strip())
        if e == 0:
            return abs(a) < 1e-6
        return abs(a - e) / abs(e) <= 0.25
    except Exception:
        return str(expected).strip().lower() == str(actual).strip().lower()


def metrics() -> dict[str, Any]:
    with _LOCK:
        return {
            "tickers_with_minutes": len(_MINUTES),
            "minutes_events": sum(len(v) for v in _MINUTES.values()),
            "prediction_rows": sum(len(v) for v in _PREDICTIONS.values()),
            "accuracy_reviews": sum(len(v) for v in _ACCURACY.values()),
        }


def reset_for_tests() -> None:
    with _LOCK:
        _MINUTES.clear()
        _PREDICTIONS.clear()
        _ACCURACY.clear()
