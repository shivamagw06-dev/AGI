from __future__ import annotations
import math, statistics
from collections import defaultdict
from datetime import date, datetime
from typing import Any

def amount(row):
    quantity, price = float(row.get("quantity") or 0), float(row.get("price") or 0)
    return price if quantity == 0 else quantity * price
def build_ledger(transactions):
    positions, cash, realized, external = {}, defaultdict(float), defaultdict(float), []
    for row in sorted(transactions, key=lambda item: (str(item.get("trade_date") or ""), str(item.get("created_at") or ""))):
        action = str(row.get("action") or "").lower(); currency = str(row.get("currency") or "INR").upper(); quantity = float(row.get("quantity") or 0); price = float(row.get("price") or 0); fees = float(row.get("fees") or 0)
        key = "|".join([str(row.get("symbol") or "").upper(), str(row.get("asset_type") or ""), str(row.get("market") or "")]); position = positions.setdefault(key, {**row, "quantity": 0.0, "cost_basis": 0.0, "average_cost": 0.0})
        if action == "buy":
            cost = quantity * price + fees; position["quantity"] += quantity; position["cost_basis"] += cost; position["average_cost"] = position["cost_basis"] / position["quantity"] if position["quantity"] else 0; cash[currency] -= cost
        elif action == "sell":
            sold = min(quantity, position["quantity"]); proceeds = sold * price - fees; realized[key] += proceeds - sold * position["average_cost"]; position["quantity"] -= sold; position["cost_basis"] = position["quantity"] * position["average_cost"]; cash[currency] += proceeds
        elif action == "dividend": cash[currency] += amount(row) - fees
        elif action == "fee": cash[currency] -= amount(row) + fees
        elif action == "deposit": cash[currency] += amount(row); external.append({"date": row.get("trade_date"), "currency": currency, "amount": amount(row)})
        elif action == "withdrawal": cash[currency] -= amount(row); external.append({"date": row.get("trade_date"), "currency": currency, "amount": -amount(row)})
    return {"positions": [{**row, "realized_pnl": realized[key]} for key, row in positions.items() if row["quantity"] > 1e-10], "cash": dict(cash), "external_flows": external}
def xirr(flows, terminal_date, terminal_value):
    series = [(d, v) for d, v in flows if v] + [(terminal_date, terminal_value)]
    if len(series) < 2 or not any(v < 0 for _, v in series) or not any(v > 0 for _, v in series): return None
    origin = min(d for d, _ in series)
    def npv(rate): return sum(value / ((1 + rate) ** ((day - origin).days / 365.0)) for day, value in series)
    low, high = -0.9999, 10.0
    while npv(low) * npv(high) > 0 and high < 1000: high *= 2
    if npv(low) * npv(high) > 0: return None
    for _ in range(120):
        mid = (low + high) / 2
        if npv(low) * npv(mid) <= 0: high = mid
        else: low = mid
    return (low + high) / 2 * 100
def risk_metrics(performance, weights):
    returns = [float(r["daily_return_pct"]) / 100 for r in performance if r.get("daily_return_pct") is not None]; aligned = [(float(r["daily_return_pct"]) / 100, float(r["benchmark_daily_return_pct"]) / 100) for r in performance if r.get("daily_return_pct") is not None and r.get("benchmark_daily_return_pct") is not None]
    volatility = statistics.stdev(returns) * math.sqrt(252) * 100 if len(returns) > 1 else None; ordered = sorted(returns); var95 = max(0, -ordered[max(0, int(len(ordered) * .05) - 1)] * 100) if ordered else None; beta = None
    if len(aligned) > 1:
        rp, rb = zip(*aligned); mp, mb = statistics.mean(rp), statistics.mean(rb); covariance = sum((p-mp)*(b-mb) for p,b in aligned)/(len(aligned)-1); variance = statistics.variance(rb); beta = covariance/variance if variance else None
    peak = 0; max_dd = 0
    for value in [float(r.get("portfolio_index") or 100) for r in performance]: peak = max(peak, value); max_dd = min(max_dd, (value/peak-1)*100 if peak else 0)
    ordered_weights = sorted(weights, reverse=True)
    return {"volatility_pct": volatility, "var_95_pct": var95, "beta": beta, "max_drawdown_pct": max_dd, "largest_position_pct": ordered_weights[0] if ordered_weights else 0, "top_five_pct": sum(ordered_weights[:5]), "hhi": sum((w/100)**2 for w in weights)}
def parse_day(value):
    if isinstance(value, date) and not isinstance(value, datetime): return value
    return date.fromisoformat(str(value)[:10])
