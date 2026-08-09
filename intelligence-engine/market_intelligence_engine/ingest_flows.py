"""Ingest exchange-level FII/DII into warehouse via DQIV gateway."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SOURCE = "upstox"


def normalise_upstox_flow(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise Upstox market/fii and market/dii responses into warehouse rows."""
    observations = payload.get("observations") or []
    if observations:
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for item in observations:
            date, segment = str(item.get("observation_date") or "")[:10], str(item.get("segment") or "")[:32]
            participant = str(item.get("participant") or "").upper()
            if not date or not segment or participant not in {"FII", "DII"}:
                continue
            row = grouped.setdefault(
                (date, segment),
                {
                    "date": date,
                    "segment": segment,
                    "interval": item.get("interval") or "1D",
                    "source": SOURCE,
                },
            )
            prefix, buy, sell = participant.lower(), item.get("buy_amount"), item.get("sell_amount")
            row[f"{prefix}_buy"], row[f"{prefix}_sell"] = buy, sell
            try:
                row[f"{prefix}_net"] = round(float(buy) - float(sell), 2) if buy is not None and sell is not None else None
            except (TypeError, ValueError):
                row[f"{prefix}_net"] = None
            if participant == "FII":
                for field in (
                    "buy_contracts", "sell_contracts", "oi_contracts", "oi_amount",
                    "long_contracts", "short_contracts", "call_long_contracts",
                    "put_long_contracts", "call_short_contracts", "put_short_contracts",
                ):
                    row[f"fii_{field}"] = item.get(field)
                row["time_stamp"] = item.get("time_stamp")
        return list(grouped.values())
    date = str(payload.get("date") or datetime.now(timezone.utc).date().isoformat())
    raw_segment = str(payload.get("segment") or payload.get("data_type") or "NSE_EQ")
    # Upstox API uses NSE_EQ|CASH; warehouse options are NSE_EQ / CASH.
    if raw_segment in {"NSE_EQ|CASH", "NSE_EQ", "CASH"} or raw_segment.startswith("NSE_EQ"):
        segment = "NSE_EQ"
    else:
        segment = raw_segment[:32] or "NSE_EQ"
    fii = payload.get("fii") or {}
    dii = payload.get("dii") or {}

    def _net(block: dict[str, Any]) -> float | None:
        buy = next((block.get(key) for key in ("buy_amount", "buy", "net_buy", "purchase") if block.get(key) is not None), None)
        sell = next((block.get(key) for key in ("sell_amount", "sell", "net_sell", "sales") if block.get(key) is not None), None)
        try:
            if buy is not None and sell is not None:
                return round(float(buy) - float(sell), 2)
            if block.get("net") is not None:
                return round(float(block["net"]), 2)
        except (TypeError, ValueError):
            return None
        return None

    row = {
        "date": date,
        "segment": segment,
        "interval": str(payload.get("interval") or "1D"),
        "fii_net": _net(fii),
        "dii_net": _net(dii),
        "fii_buy": fii.get("buy") or fii.get("purchase"),
        "fii_sell": fii.get("sell") or fii.get("sales"),
        "dii_buy": dii.get("buy") or dii.get("purchase"),
        "dii_sell": dii.get("sell") or dii.get("sales"),
        "source": SOURCE,
    }
    return [row]


def ingest_flows(rows: list[dict[str, Any]], *, actor: str = "market_intelligence_engine") -> dict[str, Any]:
    from institutional_warehouse import gateway

    if not rows:
        return {"ok": False, "error": "no_rows"}
    result = gateway.write("institutional_flow", rows, source=SOURCE, actor=actor)
    return {"ok": True, **result}
