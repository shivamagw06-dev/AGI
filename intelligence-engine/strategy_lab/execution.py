"""Indian cash-equity costs, event gates and deterministic fill simulation."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from strategy_lab.contracts import content_hash


@dataclass(frozen=True)
class IndiaCashCostSchedule:
    version: str
    effective_from: str
    brokerage_bps: float
    exchange_bps: float
    sebi_bps: float
    stt_buy_bps: float
    stt_sell_bps: float
    stamp_buy_bps: float
    gst_rate: float
    minimum_half_spread_bps: float
    impact_coefficient_bps: float
    research_only: bool = True

    @property
    def schedule_hash(self) -> str:
        return content_hash(asdict(self))

    @classmethod
    def conservative_research_default(cls) -> "IndiaCashCostSchedule":
        return cls(
            version="india-cash-research-2026-08",
            effective_from="2026-08-01",
            brokerage_bps=0.0,
            exchange_bps=0.30,
            sebi_bps=0.01,
            stt_buy_bps=10.0,
            stt_sell_bps=10.0,
            stamp_buy_bps=1.5,
            gst_rate=0.18,
            minimum_half_spread_bps=5.0,
            impact_coefficient_bps=10.0,
            research_only=True,
        )


def estimate_trade_cost(
    notional: float,
    side: str,
    *,
    adv: float,
    schedule: IndiaCashCostSchedule,
    quoted_spread_bps: float | None = None,
) -> dict[str, Any]:
    if notional < 0 or adv < 0:
        raise ValueError("negative_notional_or_adv")
    participation = notional / adv if adv > 0 else float("inf")
    spread_bps = max(schedule.minimum_half_spread_bps, float(quoted_spread_bps or 0.0) / 2.0)
    impact_bps = schedule.impact_coefficient_bps * math.sqrt(max(participation, 0.0)) if math.isfinite(participation) else float("inf")
    regulatory_bps = schedule.brokerage_bps + schedule.exchange_bps + schedule.sebi_bps
    gst_bps = regulatory_bps * schedule.gst_rate
    taxes_bps = schedule.stt_buy_bps + schedule.stamp_buy_bps if side.upper() == "BUY" else schedule.stt_sell_bps
    total_bps = regulatory_bps + gst_bps + taxes_bps + spread_bps + impact_bps
    return {
        "notional": notional,
        "side": side.upper(),
        "participation": participation,
        "regulatory_bps": regulatory_bps,
        "gst_bps": gst_bps,
        "taxes_bps": taxes_bps,
        "spread_bps": spread_bps,
        "impact_bps": impact_bps,
        "total_bps": total_bps,
        "cost": notional * total_bps / 10_000.0 if math.isfinite(total_bps) else None,
        "schedule_hash": schedule.schedule_hash,
    }


def event_gate(events: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> dict[str, Any]:
    blocked_types = {str(value).lower() for value in policy.get("block", [])}
    material = [dict(event) for event in events if bool(event.get("material", True))]
    blocking = [event for event in material if str(event.get("event_type") or "").lower() in blocked_types]
    mode = str(policy.get("mode") or "observe")
    allowed = not (mode == "block" and blocking)
    return {"allowed": allowed, "mode": mode, "blocking_events": blocking, "observed_events": material}


def simulate_order(
    order: Mapping[str, Any],
    quotes: Sequence[Mapping[str, Any]],
    *,
    schedule: IndiaCashCostSchedule,
    max_adv_participation: float = 0.05,
    decision_latency_ms: int = 250,
) -> dict[str, Any]:
    quantity = abs(float(order.get("quantity") or 0.0))
    side = str(order.get("side") or "BUY").upper()
    if quantity <= 0 or side not in {"BUY", "SELL"}:
        raise ValueError("invalid_order")
    remaining = quantity
    fills = []
    for quote in sorted((dict(item) for item in quotes), key=lambda item: str(item.get("timestamp"))):
        if remaining <= 0:
            break
        available = float(quote.get("ask_size") if side == "BUY" else quote.get("bid_size") or 0.0)
        price = float(quote.get("ask") if side == "BUY" else quote.get("bid") or 0.0)
        adv = float(quote.get("adv") or order.get("adv") or 0.0)
        cap = adv * max_adv_participation if adv > 0 else 0.0
        fill_qty = min(remaining, available, cap)
        if fill_qty <= 0 or price <= 0:
            continue
        fills.append({"timestamp": quote.get("timestamp"), "quantity": fill_qty, "price": price})
        remaining -= fill_qty
    filled = quantity - remaining
    notional = sum(fill["quantity"] * fill["price"] for fill in fills)
    average_price = notional / filled if filled else None
    cost = estimate_trade_cost(notional, side, adv=float(order.get("adv") or 0.0), schedule=schedule,
                               quoted_spread_bps=float(order.get("quoted_spread_bps") or 0.0)) if filled else None
    return {
        "order_id": order.get("order_id"),
        "symbol": order.get("symbol"),
        "side": side,
        "requested_quantity": quantity,
        "filled_quantity": filled,
        "unfilled_quantity": remaining,
        "fill_rate": filled / quantity,
        "average_fill_price": average_price,
        "fills": fills,
        "cost": cost,
        "decision_latency_ms": decision_latency_ms,
        "status": "FILLED" if remaining == 0 else ("PARTIAL" if filled else "UNFILLED"),
    }
