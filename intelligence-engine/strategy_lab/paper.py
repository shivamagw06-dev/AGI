"""Forward-only paper observation and outcome ledger for Strategy Lab."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

HORIZON_SESSIONS = 21
ROUND_TRIP_COST_BPS = 50.0
MINIMUM_SIGNAL_DATES = 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _max_drawdown(returns: list[float]) -> float | None:
    if not returns:
        return None
    wealth = peak = 1.0
    worst = 0.0
    for value in returns:
        wealth *= 1.0 + value / 100.0
        peak = max(peak, wealth)
        worst = min(worst, 100.0 * (wealth / peak - 1.0))
    return round(worst, 4)


def capture(cards: list[dict[str, Any]]) -> dict[str, Any]:
    from institutional_warehouse import gateway, store

    stamp = _now()
    existing = {
        (str(row.get("strategy_id") or ""), str(row.get("signal_as_of") or ""), str(row.get("ticker") or "").upper())
        for row in store.all_rows("strategy_paper_snapshots", limit=100000)
    }
    rows: list[dict[str, Any]] = []
    for card in cards:
        if not card.get("calculator_available"):
            continue
        strategy_id = str(card.get("strategy_id") or "")
        for signal in card.get("signals") or []:
            price = _number((signal.get("prices") or {}).get("signal_price") or signal.get("entry"))
            ticker = str(signal.get("ticker") or "").upper()
            signal_as_of = str(signal.get("signal_session") or signal.get("timestamp") or "")[:10]
            direction = str(signal.get("research_direction") or "NEUTRAL").upper()
            if not strategy_id or not ticker or len(signal_as_of) != 10 or not price or price <= 0:
                continue
            if (strategy_id, signal_as_of, ticker) in existing:
                continue
            rows.append({
                "strategy_id": strategy_id,
                "strategy_version": card.get("version"),
                "signal_as_of": signal_as_of,
                "ticker": ticker,
                "research_direction": direction,
                "signal": signal.get("signal"),
                "score": signal.get("score"),
                "signal_price": price,
                "horizon_sessions": HORIZON_SESSIONS,
                "captured_at": stamp,
            })
    result = gateway.write(
        "strategy_paper_snapshots", rows, source="strategy_lab.paper", actor="forecast_worker",
        reason="forward_only_paper_signal_capture", detect_conflicts=False,
    ) if rows else {"ok": True, "written": 0}
    return {"ok": bool(result.get("ok", True)), "eligible": len(rows), "written": int(result.get("written") or 0)}


def evaluate() -> dict[str, Any]:
    from institutional_warehouse import gateway, store
    from strategy_lab.production import _series, _warehouse_rows

    snapshots = store.all_rows("strategy_paper_snapshots", limit=100000)
    existing = store.all_rows("strategy_paper_outcomes", limit=100000)
    completed = {
        (row.get("strategy_id"), row.get("signal_as_of"), row.get("ticker"), int(row.get("horizon_sessions") or 0))
        for row in existing
    }
    series = _series(_warehouse_rows())
    rows: list[dict[str, Any]] = []
    stamp = _now()
    for snapshot in snapshots:
        key = (
            snapshot.get("strategy_id"), snapshot.get("signal_as_of"), snapshot.get("ticker"),
            int(snapshot.get("horizon_sessions") or HORIZON_SESSIONS),
        )
        if key in completed:
            continue
        bars = series.get(str(snapshot.get("ticker") or "").upper()) or []
        dates = [str(bar.get("date")) for bar in bars]
        try:
            start = dates.index(str(snapshot.get("signal_as_of")))
        except ValueError:
            continue
        horizon = key[3]
        if start + horizon >= len(bars):
            continue
        signal_price = _number(snapshot.get("signal_price"))
        outcome_price = _number(bars[start + horizon].get("close"))
        if not signal_price or not outcome_price:
            continue
        direction = str(snapshot.get("research_direction") or "NEUTRAL").upper()
        raw = 100.0 * (outcome_price / signal_price - 1.0)
        gross = -raw if direction == "SHORT" else raw if direction == "LONG" else 0.0
        net = gross - ROUND_TRIP_COST_BPS / 100.0
        rows.append({
            "strategy_id": key[0], "strategy_version": snapshot.get("strategy_version"),
            "signal_as_of": key[1], "evaluated_as_of": dates[start + horizon], "ticker": key[2],
            "research_direction": direction, "signal_price": signal_price, "outcome_price": outcome_price,
            "horizon_sessions": horizon, "gross_return_pct": round(gross, 4),
            "round_trip_cost_bps": ROUND_TRIP_COST_BPS, "net_return_pct": round(net, 4),
            "profitable": net > 0, "evaluated_at": stamp,
        })
    result = gateway.write(
        "strategy_paper_outcomes", rows, source="strategy_lab.paper", actor="forecast_worker",
        reason="matured_paper_signal_outcome", detect_conflicts=False,
    ) if rows else {"ok": True, "written": 0}
    return {"ok": bool(result.get("ok", True)), "matured": len(rows), "written": int(result.get("written") or 0)}


def persist_gate_receipts() -> dict[str, Any]:
    from institutional_warehouse import store
    from strategy_lab.production import IMPLEMENTED_STRATEGIES, VERSION
    from strategy_lab.registry_store import append_validation_evidence

    outcomes = store.all_rows("strategy_paper_outcomes", limit=100000)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in outcomes:
        grouped[str(row.get("strategy_id") or "")].append(row)
    receipts: dict[str, Any] = {}
    for strategy_id in sorted(IMPLEMENTED_STRATEGIES):
        rows = grouped.get(strategy_id, [])
        dates = sorted({str(row.get("signal_as_of")) for row in rows if row.get("signal_as_of")})
        values = [float(row["net_return_pct"]) for row in rows if row.get("net_return_pct") is not None]
        mean_return = sum(values) / len(values) if values else None
        win_rate = 100.0 * sum(bool(row.get("profitable")) for row in rows) / len(rows) if rows else None
        daily = []
        for day in dates:
            day_values = [float(row["net_return_pct"]) for row in rows if str(row.get("signal_as_of")) == day and row.get("net_return_pct") is not None]
            if day_values:
                daily.append(sum(day_values) / len(day_values))
        drawdown = _max_drawdown(daily)
        enough = len(dates) >= MINIMUM_SIGNAL_DATES
        passed = bool(enough and mean_return is not None and mean_return > 0 and (win_rate or 0) >= 50 and (drawdown or -999) >= -20)
        status = "PASSED" if passed else "FAILED" if enough else "PARTIAL"
        evidence = {"walk_forward_paper": {
            "status": status,
            "observed_at": max(dates, default=None),
            "source": "warehouse.strategy_paper_outcomes",
            "detail": {
                "forward_only": True, "signal_dates": len(dates), "minimum_signal_dates": MINIMUM_SIGNAL_DATES,
                "outcomes": len(rows), "horizon_sessions": HORIZON_SESSIONS,
                "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
                "mean_net_return_pct": round(mean_return, 4) if mean_return is not None else None,
                "win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
                "max_drawdown_pct": drawdown,
                "acceptance": {"positive_mean": True, "minimum_win_rate_pct": 50, "max_drawdown_limit_pct": 20},
            },
        }}
        receipts[strategy_id] = append_validation_evidence(strategy_id, VERSION, evidence)
    return {"ok": all(item.get("ok") for item in receipts.values()), "strategies": receipts}


def board() -> dict[str, Any]:
    """Read-only forward-validation progress; never generates or grades signals."""
    from institutional_warehouse import store
    from strategy_lab.production import IMPLEMENTED_STRATEGIES

    snapshots = store.all_rows("strategy_paper_snapshots", limit=100000)
    outcomes = store.all_rows("strategy_paper_outcomes", limit=100000)
    completed = {
        (str(row.get("strategy_id") or ""), str(row.get("signal_as_of") or ""),
         str(row.get("ticker") or "").upper(), int(row.get("horizon_sessions") or HORIZON_SESSIONS))
        for row in outcomes
    }
    strategies: dict[str, Any] = {}
    for strategy_id in sorted(IMPLEMENTED_STRATEGIES):
        signals = [row for row in snapshots if str(row.get("strategy_id") or "") == strategy_id]
        graded = [row for row in outcomes if str(row.get("strategy_id") or "") == strategy_id]
        signal_dates = sorted({str(row.get("signal_as_of")) for row in graded if row.get("signal_as_of")})
        values = [float(row["net_return_pct"]) for row in graded if row.get("net_return_pct") is not None]
        pending = sum(
            1 for row in signals
            if (strategy_id, str(row.get("signal_as_of") or ""), str(row.get("ticker") or "").upper(),
                int(row.get("horizon_sessions") or HORIZON_SESSIONS)) not in completed
        )
        strategies[strategy_id] = {
            "snapshots": len(signals),
            "pending_outcomes": pending,
            "matured_outcomes": len(graded),
            "independent_signal_dates": len(signal_dates),
            "minimum_signal_dates": MINIMUM_SIGNAL_DATES,
            "remaining_signal_dates": max(0, MINIMUM_SIGNAL_DATES - len(signal_dates)),
            "mean_net_return_pct": round(sum(values) / len(values), 4) if values else None,
            "win_rate_pct": round(100.0 * sum(bool(row.get("profitable")) for row in graded) / len(graded), 2) if graded else None,
            "last_signal_as_of": max((str(row.get("signal_as_of")) for row in signals), default=None),
            "last_evaluated_as_of": max((str(row.get("evaluated_as_of")) for row in graded), default=None),
            "validation_status": "EVIDENCE_AVAILABLE" if len(signal_dates) >= MINIMUM_SIGNAL_DATES else "ACCUMULATING",
        }
    return {
        "ok": True,
        "status": "ACCUMULATING_FORWARD_EVIDENCE" if any(
            row["remaining_signal_dates"] for row in strategies.values()
        ) else "MINIMUM_OBSERVATION_WINDOW_REACHED",
        "forward_only": True,
        "horizon_sessions": HORIZON_SESSIONS,
        "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
        "execution_eligible": False,
        "strategies": strategies,
        "rule": "Observation count alone never validates a strategy; economic acceptance gates still apply.",
    }


def run(cards: list[dict[str, Any]]) -> dict[str, Any]:
    captured = capture(cards)
    evaluated = evaluate()
    changed = int(captured.get("written") or 0) + int(evaluated.get("written") or 0)
    receipts = persist_gate_receipts() if changed else {"ok": True, "strategies": {}, "skipped": "no_new_paper_evidence"}
    return {"ok": captured.get("ok") and evaluated.get("ok") and receipts.get("ok"),
            "capture": captured, "evaluation": evaluated, "receipts": receipts}
