"""Frozen V1 repricing observations and automated validation reports."""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .engine import price_option_snapshot
from .store import OptionEvidenceStore


TOLERANCE_FLOOR_POINTS = 5.0
TOLERANCE_PERCENT = 10.0
ACCEPTANCE_MAPE_PERCENT = 3.0
MINIMUM_ACCEPTANCE_DAYS = 60


def _premium_bucket(price: float) -> str:
    if price < 10:
        return "<10"
    if price < 25:
        return "10-25"
    if price < 50:
        return "25-50"
    if price < 100:
        return "50-100"
    if price < 250:
        return "100-250"
    return ">=250"


def _dte_bucket(dte_days: float) -> str:
    if dte_days < 1:
        return "0DTE"
    if dte_days <= 2:
        return "1-2DTE"
    if dte_days <= 7:
        return "3-7DTE"
    if dte_days <= 14:
        return "8-14DTE"
    if dte_days <= 30:
        return "15-30DTE"
    return ">30DTE"


def _moneyness_bucket(option_type: str, strike: float, spot: float) -> str:
    signed = (spot - strike) / spot * 100.0
    if option_type == "PE":
        signed = -signed
    if signed >= 2:
        return "deep_itm"
    if signed > 0.5:
        return "itm"
    if signed >= -0.5:
        return "atm"
    if signed > -2:
        return "otm"
    return "deep_otm"


def create_validation_observations(
    store: OptionEvidenceStore,
    inserted_snapshots: list[dict[str, Any]],
    *,
    max_horizon_minutes: float = 30.0,
) -> int:
    created = 0
    now = datetime.now(timezone.utc).isoformat()
    for current in inserted_snapshots:
        prior = current.get("prior_state")
        if not prior:
            continue
        prior_at = datetime.fromisoformat(prior["observed_at"])
        current_at = datetime.fromisoformat(current["captured_at"])
        horizon = (current_at - prior_at).total_seconds() / 60.0
        if horizon < 5 or horizon > max_horizon_minutes:
            continue
        if prior.get("iv_pct") is None or current["market_price"] <= 0:
            continue
        try:
            result = price_option_snapshot(
                {
                    "spot": current["spot"],
                    "strike": current["strike"],
                    "days_to_expiry": current["dte_days"],
                    "risk_free_rate_pct": current["risk_free_rate_pct"],
                    "dividend_yield_pct": current["dividend_yield_pct"],
                    "option_type": (
                        "call" if current["option_type"] == "CE" else "put"
                    ),
                    "model_volatility_pct": prior["iv_pct"],
                    "bid": None,
                    "ask": None,
                }
            )
            predicted = float((result.get("valuation") or {})["model_value"])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isfinite(predicted) or predicted < 0:
            continue
        actual = float(current["market_price"])
        error = actual - predicted
        absolute_error = abs(error)
        ape = absolute_error / actual * 100.0
        tolerance = max(
            TOLERANCE_FLOOR_POINTS,
            actual * TOLERANCE_PERCENT / 100.0,
        )
        observation = {
            "prior_snapshot_id": prior["snapshot_id"],
            "current_snapshot_id": current["snapshot_id"],
            "local_date": current["local_date"],
            "observed_at": current["captured_at"],
            "instrument_key": current["instrument_key"],
            "expiry": current["expiry"],
            "option_type": current["option_type"],
            "strike": current["strike"],
            "horizon_minutes": horizon,
            "dte_days": current["dte_days"],
            "dte_bucket": _dte_bucket(current["dte_days"]),
            "moneyness_bucket": _moneyness_bucket(
                current["option_type"], current["strike"], current["spot"]
            ),
            "premium_bucket": _premium_bucket(actual),
            "prior_iv_pct": prior["iv_pct"],
            "prior_market_price": prior["market_price"],
            "prior_spot": prior["spot"],
            "current_spot": current["spot"],
            "actual_price": actual,
            "predicted_price": predicted,
            "error_points": error,
            "absolute_error_points": absolute_error,
            "absolute_percentage_error": ape,
            "tolerance_points": tolerance,
            "within_tolerance": int(absolute_error <= tolerance),
            "pricing_method": "pricing_engine_v1:last_contract_iv",
            "created_at": now,
        }
        created += int(store.add_validation(observation))
    return created


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "observations": 0,
            "mape_pct": None,
            "mae_points": None,
            "median_absolute_error_points": None,
            "within_tolerance_pct": None,
        }
    return {
        "observations": len(rows),
        "mape_pct": statistics.mean(
            float(row["absolute_percentage_error"]) for row in rows
        ),
        "mae_points": statistics.mean(
            float(row["absolute_error_points"]) for row in rows
        ),
        "median_absolute_error_points": statistics.median(
            float(row["absolute_error_points"]) for row in rows
        ),
        "within_tolerance_pct": statistics.mean(
            int(row["within_tolerance"]) for row in rows
        )
        * 100.0,
    }


def _group_metrics(
    rows: list[dict[str, Any]], field: str
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {key: _metrics(value) for key, value in sorted(groups.items())}


def _clustered_day_ci(
    rows: list[dict[str, Any]], *, samples: int = 2000
) -> dict[str, float] | None:
    by_day: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_day[row["local_date"]].append(float(row["absolute_percentage_error"]))
    days = sorted(by_day)
    if len(days) < 2:
        return None
    daily_mapes = [statistics.mean(by_day[day]) for day in days]
    seed = int(hashlib.sha256("|".join(days).encode()).hexdigest()[:16], 16)
    generator = random.Random(seed)
    estimates = sorted(
        statistics.mean(
            daily_mapes[generator.randrange(len(daily_mapes))]
            for _ in daily_mapes
        )
        for _ in range(samples)
    )
    return {
        "lower_95_pct": estimates[int(samples * 0.025)],
        "upper_95_pct": estimates[int(samples * 0.975) - 1],
    }


def build_report(
    rows: list[dict[str, Any]], *, report_date: str
) -> dict[str, Any]:
    through = [row for row in rows if row["local_date"] <= report_date]
    target_day = [row for row in through if row["local_date"] == report_date]
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in through:
        by_day[row["local_date"]].append(row)
    day_mapes = {
        day: _metrics(day_rows)["mape_pct"] for day, day_rows in by_day.items()
    }
    cumulative = _metrics(through)
    cumulative["trading_days"] = len(by_day)
    cumulative["day_weighted_mape_pct"] = (
        statistics.mean(day_mapes.values()) if day_mapes else None
    )
    cumulative["day_clustered_mape_ci"] = _clustered_day_ci(through)
    if len(by_day) < MINIMUM_ACCEPTANCE_DAYS:
        status = "extended_validation_pending"
    elif (
        cumulative["mape_pct"] is not None
        and cumulative["day_weighted_mape_pct"] is not None
        and cumulative["mape_pct"] < ACCEPTANCE_MAPE_PERCENT
        and cumulative["day_weighted_mape_pct"] < ACCEPTANCE_MAPE_PERCENT
    ):
        status = "pass"
    else:
        status = "fail"
    return {
        "model": "Pricing Engine V1",
        "model_status": status,
        "report_date": report_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frozen_method": "last contract IV; no shared CE/PE IV; 15-minute refresh",
        "claim_boundary": "conditional repricing, not direction or profitability",
        "acceptance_rule": {
            "minimum_trading_days": MINIMUM_ACCEPTANCE_DAYS,
            "observation_weighted_mape_below_pct": ACCEPTANCE_MAPE_PERCENT,
            "day_weighted_mape_below_pct": ACCEPTANCE_MAPE_PERCENT,
        },
        "daily": _metrics(target_day),
        "cumulative": cumulative,
        "buckets": {
            "premium": _group_metrics(through, "premium_bucket"),
            "moneyness": _group_metrics(through, "moneyness_bucket"),
            "dte": _group_metrics(through, "dte_bucket"),
            "expiry": _group_metrics(through, "expiry"),
            "option_type": _group_metrics(through, "option_type"),
        },
        "daily_mape_pct": dict(sorted(day_mapes.items())),
    }


def _format(value: Any, decimals: int = 2) -> str:
    return "n/a" if value is None else f"{float(value):.{decimals}f}"


def _markdown(report: dict[str, Any]) -> str:
    daily = report["daily"]
    cumulative = report["cumulative"]
    lines = [
        "# Pricing Engine V1 daily validation",
        "",
        f"**Report date:** {report['report_date']}  ",
        f"**Status:** {report['model_status']}  ",
        f"**Boundary:** {report['claim_boundary']}",
        "",
        "## Daily result",
        "",
        "| Observations | MAPE | MAE points | Median error | Within tolerance |",
        "|---:|---:|---:|---:|---:|",
        (
            f"| {daily['observations']} | {_format(daily['mape_pct'])}% "
            f"| {_format(daily['mae_points'])} "
            f"| {_format(daily['median_absolute_error_points'])} "
            f"| {_format(daily['within_tolerance_pct'])}% |"
        ),
        "",
        "## Cumulative prospective validation",
        "",
        f"- Trading days: **{cumulative['trading_days']} / {MINIMUM_ACCEPTANCE_DAYS} minimum**",
        f"- Observation-weighted MAPE: **{_format(cumulative['mape_pct'])}%**",
        f"- Day-weighted MAPE: **{_format(cumulative['day_weighted_mape_pct'])}%**",
        f"- MAE: **{_format(cumulative['mae_points'])} option points**",
        f"- Median absolute error: **{_format(cumulative['median_absolute_error_points'])} points**",
        "",
        "## Bucket diagnostics",
        "",
    ]
    for title, bucket in report["buckets"].items():
        lines.extend(
            [
                f"### {title.replace('_', ' ').title()}",
                "",
                "| Bucket | Observations | MAPE | MAE points |",
                "|---|---:|---:|---:|",
            ]
        )
        for name, metrics in bucket.items():
            lines.append(
                f"| {name} | {metrics['observations']} "
                f"| {_format(metrics['mape_pct'])}% "
                f"| {_format(metrics['mae_points'])} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_daily_report(
    store: OptionEvidenceStore,
    report_date: str,
    output_directory: str | Path,
) -> dict[str, Any]:
    date.fromisoformat(report_date)
    report = build_report(
        store.validations(through_date=report_date), report_date=report_date
    )
    output = Path(output_directory).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{report_date}.json"
    markdown_path = output / f"{report_date}.md"
    json_temporary = json_path.with_suffix(".json.tmp")
    markdown_temporary = markdown_path.with_suffix(".md.tmp")
    json_temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_temporary.write_text(_markdown(report), encoding="utf-8")
    json_temporary.replace(json_path)
    markdown_temporary.replace(markdown_path)
    store.save_report(
        report_date,
        report["generated_at"],
        report["model_status"],
        report,
        str(markdown_path),
        str(json_path),
    )
    return {
        "report_date": report_date,
        "status": report["model_status"],
        "markdown_path": str(markdown_path),
        "json_path": str(json_path),
        "daily": report["daily"],
        "cumulative": report["cumulative"],
    }
