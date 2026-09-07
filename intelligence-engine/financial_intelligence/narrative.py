"""Template narrative engine — no LLM opinions."""

from __future__ import annotations

from typing import Any

from financial_intelligence.schema import MARGIN_METRICS


def _fmt_num(v: float | None) -> str:
    if v is None:
        return "n/a"
    if abs(v) >= 100:
        return f"{v:,.1f}"
    if abs(v) >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def narrative_for_trend(trend: dict[str, Any]) -> str | None:
    """Deterministic prose from a detect_trends() result."""
    primary = trend.get("primary")
    if not primary:
        return None
    metric = str(trend.get("metric") or primary.get("metric") or "metric")
    window = str(primary.get("window") or "").upper()
    curr = primary.get("current_value")
    prior = primary.get("prior_value")
    change = primary.get("change")
    unit = primary.get("change_unit")
    direction = primary.get("direction")
    label = trend.get("trend_label")

    pretty = metric.replace("_", " ")
    if metric in MARGIN_METRICS and unit == "bps":
        verb = "expanded" if direction == "up" else ("compressed" if direction == "down" else "was unchanged")
        return (
            f"{pretty.capitalize()} is {_fmt_num(curr)}%, which {verb} by "
            f"{_fmt_num(abs(change) if change is not None else None)} bps "
            f"compared with the prior {window} period ({_fmt_num(prior)}%)."
        )

    if direction == "up":
        growth_phrase = "grown" if metric in {"revenue", "cash", "eps_basic", "net_income", "free_cash_flow", "operating_cash_flow"} else "increased"
        if label == "revenue_acceleration":
            return (
                f"Revenue has grown faster than the previous comparable period "
                f"({window}: +{_fmt_num(change)}% to {_fmt_num(curr)} from {_fmt_num(prior)})."
            )
        if label == "revenue_deceleration" and (change or 0) > 0:
            return (
                f"Revenue continues to grow but at a slower pace than the longer-term trend "
                f"({window}: +{_fmt_num(change)}% to {_fmt_num(curr)})."
            )
        return (
            f"{pretty.capitalize()} has {growth_phrase} "
            f"{_fmt_num(change)}% {window} to {_fmt_num(curr)} from {_fmt_num(prior)}."
        )

    if direction == "down":
        return (
            f"{pretty.capitalize()} has declined "
            f"{_fmt_num(abs(change) if change is not None else None)}% {window} "
            f"to {_fmt_num(curr)} from {_fmt_num(prior)}."
        )

    return f"{pretty.capitalize()} was largely unchanged {window} at {_fmt_num(curr)}."


def narrative_for_quality(signal: dict[str, Any]) -> str:
    code = signal.get("code") or "quality_signal"
    detail = signal.get("detail") or ""
    return f"{str(code).replace('_', ' ').capitalize()}. {detail}".strip()
