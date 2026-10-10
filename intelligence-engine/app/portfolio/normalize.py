"""Normalize manual / CSV / model portfolios into PortfolioSnapshot — never invents prices."""

from __future__ import annotations

import csv
import io
from typing import Any

from app.schemas.models import PortfolioHolding, PortfolioSnapshot

# Identity-only model templates (weights sum ~1). Not performance claims.
MODEL_PORTFOLIOS: dict[str, list[dict[str, Any]]] = {
    "balanced_india": [
        {"symbol": "RELIANCE", "weight": 0.12, "sector": "Energy"},
        {"symbol": "TCS", "weight": 0.12, "sector": "IT"},
        {"symbol": "HDFCBANK", "weight": 0.12, "sector": "Banks"},
        {"symbol": "INFY", "weight": 0.10, "sector": "IT"},
        {"symbol": "ICICIBANK", "weight": 0.10, "sector": "Banks"},
        {"symbol": "ITC", "weight": 0.08, "sector": "FMCG"},
        {"symbol": "BHARTIARTL", "weight": 0.08, "sector": "Telecom"},
        {"symbol": "LT", "weight": 0.08, "sector": "Industrials"},
        {"symbol": "SBIN", "weight": 0.10, "sector": "Banks"},
        {"symbol": "ASIANPAINT", "weight": 0.10, "sector": "Materials"},
    ],
    "quality_compounders": [
        {"symbol": "TCS", "weight": 0.20, "sector": "IT"},
        {"symbol": "INFY", "weight": 0.15, "sector": "IT"},
        {"symbol": "HDFCBANK", "weight": 0.20, "sector": "Banks"},
        {"symbol": "ASIANPAINT", "weight": 0.15, "sector": "Materials"},
        {"symbol": "NESTLEIND", "weight": 0.15, "sector": "FMCG"},
        {"symbol": "TITAN", "weight": 0.15, "sector": "Consumer"},
    ],
}


def _sym(raw: Any) -> str:
    return str(raw or "").strip().upper().replace(".NS", "").replace(".NSE", "")


def _float(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def normalize_holding(row: dict[str, Any]) -> PortfolioHolding | None:
    symbol = _sym(row.get("symbol") or row.get("ticker") or row.get("Symbol") or row.get("Ticker"))
    if not symbol:
        return None
    weight = _float(row.get("weight") or row.get("Weight") or row.get("allocation"))
    if weight is not None and weight > 1:
        weight = weight / 100.0
    qty = _float(row.get("quantity") or row.get("qty") or row.get("Quantity"))
    avg = _float(row.get("avg_price") or row.get("avgPrice") or row.get("Avg Price") or row.get("price"))
    sector = row.get("sector") or row.get("Sector")
    name = row.get("name") or row.get("Name") or row.get("company")
    return PortfolioHolding(
        symbol=symbol,
        weight=weight,
        quantity=qty,
        avg_price=avg,
        sector=str(sector).strip() if sector else None,
        name=str(name).strip() if name else None,
        notes=str(row.get("notes") or "").strip() or None,
    )


def parse_csv_holdings(csv_text: str) -> list[PortfolioHolding]:
    text = (csv_text or "").strip()
    if not text:
        return []
    reader = csv.DictReader(io.StringIO(text))
    out: list[PortfolioHolding] = []
    for row in reader:
        holding = normalize_holding(row)
        if holding:
            out.append(holding)
    if out:
        return out
    # Fallback: symbol,weight lines without header
    for line in text.splitlines():
        parts = [p.strip() for p in line.replace("\t", ",").split(",") if p.strip()]
        if len(parts) < 1 or parts[0].lower() in {"symbol", "ticker"}:
            continue
        row = {"symbol": parts[0]}
        if len(parts) > 1:
            row["weight"] = parts[1]
        if len(parts) > 2:
            row["quantity"] = parts[2]
        holding = normalize_holding(row)
        if holding:
            out.append(holding)
    return out


def _renormalize_weights(holdings: list[PortfolioHolding]) -> list[PortfolioHolding]:
    weighted = [h for h in holdings if h.weight is not None and h.weight > 0]
    if not weighted:
        # Equal weight when only symbols provided — disclosed as assumption
        n = len(holdings)
        if n == 0:
            return holdings
        eq = 1.0 / n
        return [
            h.model_copy(update={"weight": eq, "notes": (h.notes or "") + (" | equal-weight assumption" if not h.notes else "")})
            for h in holdings
        ]
    total = sum(h.weight or 0 for h in weighted)
    if total <= 0:
        return holdings
    fixed: list[PortfolioHolding] = []
    for h in holdings:
        if h.weight is None:
            fixed.append(h)
        else:
            fixed.append(h.model_copy(update={"weight": round((h.weight or 0) / total, 6)}))
    return fixed


def build_snapshot(
    *,
    name: str = "Client Portfolio",
    client_id: str | None = None,
    source: str = "manual",
    holdings: list[dict[str, Any]] | None = None,
    csv_text: str | None = None,
    model_id: str | None = None,
) -> PortfolioSnapshot:
    notes: list[str] = []
    rows: list[PortfolioHolding] = []

    if source == "model" or model_id:
        mid = (model_id or "balanced_india").strip().lower()
        template = MODEL_PORTFOLIOS.get(mid)
        if not template:
            notes.append(f"Unknown model_id={mid}; available: {', '.join(MODEL_PORTFOLIOS)}")
            template = MODEL_PORTFOLIOS["balanced_india"]
            notes.append("Fell back to balanced_india model template (identity weights only).")
        rows = [normalize_holding(r) for r in template]
        rows = [r for r in rows if r]
        source = "model"
        notes.append(f"Model portfolio template: {mid}. Weights are policy targets, not live NAV.")
    elif csv_text:
        rows = parse_csv_holdings(csv_text)
        source = "csv"
    else:
        for row in holdings or []:
            h = normalize_holding(row)
            if h:
                rows.append(h)
        source = source if source in {"manual", "csv", "model", "broker_future"} else "manual"

    # Dedupe by symbol, keep first
    seen: set[str] = set()
    unique: list[PortfolioHolding] = []
    for h in rows:
        if h.symbol in seen:
            continue
        seen.add(h.symbol)
        unique.append(h)

    unique = _renormalize_weights(unique)
    if not unique:
        notes.append("No holdings parsed — portfolio package will withhold scores.")
    if source == "broker_future":
        notes.append("Broker integration is architectural only — no live broker sync in this build.")

    return PortfolioSnapshot(
        name=name or "Client Portfolio",
        client_id=client_id,
        source=source,  # type: ignore[arg-type]
        holdings=unique,
        notes=notes,
    )


def sector_exposure(snapshot: PortfolioSnapshot) -> dict[str, float]:
    buckets: dict[str, float] = {}
    for h in snapshot.holdings:
        key = h.sector or "Unclassified"
        buckets[key] = round(buckets.get(key, 0.0) + float(h.weight or 0.0), 6)
    return dict(sorted(buckets.items(), key=lambda kv: kv[1], reverse=True))
