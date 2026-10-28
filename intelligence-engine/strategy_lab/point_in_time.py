"""Point-in-time observations, historical universes and total returns."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Iterable, Mapping, Sequence

from institutional_warehouse import store
from strategy_lab.contracts import content_hash


def _date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()[:10]
    if not raw:
        raise ValueError("date_required")
    return date.fromisoformat(raw)


def visible_observations(rows: Iterable[Mapping[str, Any]], as_of: Any) -> list[dict[str, Any]]:
    """Return the latest revision that was actually available by ``as_of``."""
    cutoff = _date(as_of)
    chosen: dict[tuple[str, str, str], dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        available = _date(row.get("available_from") or row.get("announcement_date"))
        if available > cutoff:
            continue
        key = (str(row.get("company_id")), str(row.get("metric_id")), str(row.get("period_end")))
        prior = chosen.get(key)
        rank = (available, str(row.get("revision_id") or ""), str(row.get("observation_id") or ""))
        prior_rank = (
            _date(prior.get("available_from") or prior.get("announcement_date")),
            str(prior.get("revision_id") or ""),
            str(prior.get("observation_id") or ""),
        ) if prior else None
        if prior_rank is None or rank > prior_rank:
            chosen[key] = row
    return sorted(chosen.values(), key=lambda row: (str(row.get("company_id")), str(row.get("metric_id")), str(row.get("period_end"))))


def universe_on(rows: Iterable[Mapping[str, Any]], as_of: Any, *, index_id: str | None = None) -> list[str]:
    cutoff = _date(as_of)
    members: set[str] = set()
    for row in rows:
        if index_id and str(row.get("index_id")) != index_id:
            continue
        start = _date(row.get("effective_from"))
        end_raw = row.get("effective_to")
        if start <= cutoff and (not end_raw or cutoff <= _date(end_raw)) and bool(row.get("investable", True)):
            members.add(str(row.get("company_id")))
    return sorted(members)


def known_corporate_actions(rows: Iterable[Mapping[str, Any]], as_of: Any) -> list[dict[str, Any]]:
    cutoff = _date(as_of)
    out = []
    for raw in rows:
        row = dict(raw)
        known = row.get("available_from") or row.get("announcement_date")
        if known and _date(known) <= cutoff:
            out.append(row)
    return sorted(out, key=lambda row: (str(row.get("company_id")), str(row.get("effective_date") or row.get("ex_date"))))


def total_return_series(
    prices: Sequence[Mapping[str, Any]],
    actions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Create an auditable total-return index from raw closes and known actions.

    Structural actions are applied only when the input action is explicitly
    corroborated. Cash dividends add to the period return on ex-date.
    """
    action_map: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for action in actions:
        action_map[str(action.get("ex_date") or action.get("effective_date"))[:10]].append(action)
    ordered = sorted((dict(row) for row in prices), key=lambda row: str(row.get("date") or row.get("as_of")))
    index = 100.0
    previous: float | None = None
    output = []
    for row in ordered:
        day = str(row.get("date") or row.get("as_of"))[:10]
        close = float(row.get("close") or row.get("adjusted_close") or 0.0)
        if close <= 0:
            continue
        dividend = 0.0
        structural_factor = 1.0
        applied: list[str] = []
        for action in action_map.get(day, []):
            kind = str(action.get("action_type") or "").lower()
            if kind == "dividend":
                dividend += float(action.get("cash_amount") or 0.0)
                applied.append("dividend")
            elif kind in {"split", "bonus", "rights", "merger", "demerger"} and bool(action.get("corroborated")):
                structural_factor *= float(action.get("ratio") or 1.0)
                applied.append(kind)
        period_return = 0.0
        if previous and previous > 0:
            comparable_close = close * structural_factor
            period_return = (comparable_close + dividend) / previous - 1.0
            index *= 1.0 + period_return
        output.append({**row, "total_return_index": index, "period_total_return": period_return, "actions_applied": applied})
        previous = close
    return output


def dataset_hash(rows: Iterable[Mapping[str, Any]]) -> str:
    return content_hash(sorted((dict(row) for row in rows), key=lambda row: content_hash(row)))


def persist_observations(rows: Iterable[Mapping[str, Any]], *, actor: str = "system") -> dict[str, Any]:
    prepared = []
    for raw in rows:
        row = dict(raw)
        required = ("company_id", "metric_id", "period_end", "available_from", "source")
        missing = [key for key in required if not row.get(key)]
        if missing:
            raise ValueError(f"point_in_time_missing:{','.join(missing)}")
        row.setdefault("observation_id", content_hash({key: row.get(key) for key in required + ("revision_id",)})[:32])
        prepared.append(row)
    return store.upsert(
        "point_in_time_observations", prepared, source="point_in_time_ingestion", actor=actor,
        reason="append_point_in_time_observations",
    )


def persist_membership(rows: Iterable[Mapping[str, Any]], *, actor: str = "system") -> dict[str, Any]:
    prepared = []
    for raw in rows:
        row = dict(raw)
        if not all(row.get(key) for key in ("company_id", "index_id", "effective_from", "source")):
            raise ValueError("universe_membership_missing_key")
        prepared.append(row)
    return store.upsert(
        "universe_membership_history", prepared, source="universe_history", actor=actor,
        reason="append_effective_dated_universe_membership",
    )
