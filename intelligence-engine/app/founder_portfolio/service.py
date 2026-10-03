from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from app.founder_portfolio.analytics import build_ledger, parse_day, risk_metrics, xirr
from app.founder_portfolio.providers import FounderPriceResolver
from app.founder_portfolio.store import FounderPortfolioStore

class FounderPortfolioService:
    def __init__(self): self.store, self.prices = FounderPortfolioStore(), FounderPriceResolver()
    def health(self): return {"ok": self.store.configured, "service": "founder-portfolio-intelligence", "storage_configured": self.store.configured, "upstox_configured": bool(self.prices.upstox_token), "providers": ["upstox", "yahoo_canonical", "amfi_nav", "yahoo_fx"]}
    async def latest_report(self):
        rows = await self.store.rows("founder_portfolio_validation_reports", order="run_at.desc", limit="1"); return rows[0] if rows else None
    async def refresh(self):
        started = datetime.now(timezone.utc); transactions = await self.store.rows("founder_portfolio_transactions", order="trade_date.asc,created_at.asc"); settings_rows = await self.store.rows("founder_portfolio_settings", portfolio_id="eq.founder", limit="1"); settings = settings_rows[0] if settings_rows else {}; ledger = build_ledger(transactions); positions = ledger["positions"]
        if not positions: return await self._report("FAILED", 0, 0, False, [], {}, {}, "No active positions in private ledger")
        quotes, missing, sources = {}, [], Counter()
        for position in positions:
            try: quote = await self.prices.quote(position); quotes[self._key(position)] = quote; sources[quote.source] += 1
            except Exception as exc: missing.append({"symbol": str(position.get("symbol")), "reason": str(exc)[:240]})
        if missing: return await self._report("FAILED", len(positions), len(quotes), False, missing, dict(sources), {}, "Portfolio preserved: one or more held assets had no verified price or NAV")
        fx = await self.prices.fx_usdinr() if any(str(p.get("currency")).upper() == "USD" for p in positions) or ledger["cash"].get("USD") else None; usd_inr = fx.price if fx else 1.0; benchmark_return, benchmark_sources = await self.prices.benchmark_return(settings.get("benchmark_components") or ""); sources.update({f"benchmark:{k}": 1 for k in benchmark_sources})
        values, total_positions, allocation = [], 0.0, defaultdict(float)
        for position in positions:
            quote = quotes[self._key(position)]; rate = usd_inr if str(position.get("currency")).upper() == "USD" else 1.0; value = float(position["quantity"]) * quote.price * rate; total_positions += value; values.append({**position, "quote": quote, "fx_rate": rate, "value_inr": value})
        cash_value = float(ledger["cash"].get("INR", 0)) + float(ledger["cash"].get("USD", 0)) * usd_inr; total_value = total_positions + cash_value
        if total_value <= 0: return await self._report("FAILED", len(positions), len(quotes), False, [], dict(sources), {}, "Portfolio total value is not positive")
        for item in values:
            item["weight"] = item["value_inr"] / total_value * 100; allocation[str(item.get("asset_type") or "other")] += item["weight"]; cost = float(item.get("average_cost") or 0); item["return_pct"] = (item["quote"].price / cost - 1) * 100 if cost else None
        today = date.today(); prior_rows = await self.store.rows("founder_portfolio_snapshots", order="snapshot_date.desc", limit="1"); prior = prior_rows[0] if prior_rows else None; prior_date = parse_day(prior["snapshot_date"]) if prior else None; flow_since = 0.0
        for flow in ledger["external_flows"]:
            if prior_date is None or parse_day(flow["date"]) > prior_date: flow_since += float(flow["amount"]) * (usd_inr if flow["currency"] == "USD" else 1)
        if prior and float(prior["total_value_inr"] or 0) > 0:
            daily_return = (total_value-float(prior["total_value_inr"])-flow_since)/float(prior["total_value_inr"]); portfolio_index = float(prior.get("portfolio_index") or 100)*(1+daily_return); benchmark_index = float(prior.get("benchmark_index") or 100)*(1+(benchmark_return or 0))
        else: daily_return, portfolio_index, benchmark_index = None, 100.0, 100.0
        twr_pct = (portfolio_index/100-1)*100; investor_flows = [(parse_day(f["date"]), -float(f["amount"])*(usd_inr if f["currency"] == "USD" else 1)) for f in ledger["external_flows"]]; xirr_pct = xirr(investor_flows, today, total_value)
        history = await self.store.rows("founder_portfolio_performance", order="snapshot_date.asc"); current = {"snapshot_date": today.isoformat(), "portfolio_index": portfolio_index, "benchmark_index": benchmark_index, "daily_return_pct": daily_return*100 if daily_return is not None else None, "benchmark_daily_return_pct": benchmark_return*100 if benchmark_return is not None else None, "twr_pct": twr_pct, "drawdown_pct": 0, "updated_at": started.isoformat()}; performance = [r for r in history if r.get("snapshot_date") != today.isoformat()] + [current]; risk = risk_metrics(performance, [i["weight"] for i in values]); peak = max(float(r.get("portfolio_index") or 100) for r in performance); current["drawdown_pct"] = (portfolio_index/peak-1)*100 if peak else 0
        attribution = []
        if prior and float(prior.get("total_value_inr") or 0) > 0:
            prior_total = float(prior["total_value_inr"]); prior_holdings = {self._key(i): i for i in (prior.get("holdings") or [])}
            for item in values:
                old = prior_holdings.get(self._key(item))
                if not old: continue
                quantity = float(old.get("quantity") or 0); old_price = float(old.get("price") or 0); old_fx = float(old.get("fx_rate") or (usd_inr if str(item.get("currency")).upper() == "USD" else 1)); new_price = float(item["quote"].price); new_fx = float(item.get("fx_rate") or 1)
                asset_part = quantity * (new_price-old_price) * old_fx / prior_total * 100; fx_part = quantity * new_price * (new_fx-old_fx) / prior_total * 100
                attribution.append({"valuation_date": today.isoformat(), "symbol": str(item.get("symbol") or ""), "asset_name": str(item.get("asset_name") or item.get("symbol") or ""), "asset_type": str(item.get("asset_type") or "other"), "market": str(item.get("market") or ""), "contribution_pct": asset_part+fx_part, "asset_contribution_pct": asset_part, "fx_contribution_pct": fx_part, "weight_pct": item.get("weight"), "updated_at": started.isoformat()})
        snapshot = {"snapshot_date": today.isoformat(), "total_value_inr": total_value, "cash_value_inr": cash_value, "net_external_flow_inr": flow_since, "daily_return_pct": current["daily_return_pct"], "portfolio_index": portfolio_index, "benchmark_index": benchmark_index, "twr_pct": twr_pct, "xirr_pct": xirr_pct, "holdings": [self._private(i) for i in values], "allocation": dict(allocation), "risk": risk}
        disclosures = await self.store.rows("founder_portfolio_disclosures"); by_key = {self._key(i): i for i in values}
        for disclosure in disclosures:
            item = by_key.get(self._key(disclosure))
            if item:
                quote = item["quote"]; await self.store.upsert("founder_portfolio_disclosures", {**disclosure, "public_weight": item["weight"], "return_pct": item["return_pct"], "latest_price": quote.price, "price_source": quote.source, "price_as_of": quote.as_of, "updated_at": started.isoformat()}, on_conflict="id")
        await self.store.upsert("founder_portfolio_snapshots", snapshot, on_conflict="snapshot_date"); await self.store.upsert("founder_portfolio_performance", current, on_conflict="snapshot_date")
        for row in attribution: await self.store.upsert("founder_portfolio_attribution", row, on_conflict="valuation_date,symbol,asset_type,market")
        benchmark_pct = (benchmark_index/100-1)*100
        await self.store.upsert("founder_portfolio_settings", {**settings, "portfolio_id": "founder", "portfolio_return_pct": twr_pct, "benchmark_return_pct": benchmark_pct, "twr_pct": twr_pct, "xirr_pct": xirr_pct, "cash_weight_pct": cash_value/total_value*100, **risk, "last_published_at": started.isoformat(), "updated_at": started.isoformat(), "status": "live"}, on_conflict="portfolio_id")
        return await self._report("OK", len(positions), len(quotes), True, [], dict(sources), {"total_value_inr": total_value, "twr_pct": twr_pct, "xirr_pct": xirr_pct, **risk}, "All held assets priced; private snapshot and public disclosure updated")
    async def _report(self, status, assets, priced, snapshot, missing, sources, metrics, message): return await self.store.insert("founder_portfolio_validation_reports", {"status": status, "asset_count": assets, "priced_count": priced, "snapshot_written": snapshot, "missing_assets": missing, "sources": sources, "metrics": metrics, "message": message})
    @staticmethod
    def _key(row): return "|".join([str(row.get("symbol") or "").upper(), str(row.get("asset_type") or ""), str(row.get("market") or "")])
    @staticmethod
    def _private(item):
        quote = item["quote"]; return {"symbol": item.get("symbol"), "asset_name": item.get("asset_name"), "asset_type": item.get("asset_type"), "market": item.get("market"), "currency": item.get("currency"), "quantity": item.get("quantity"), "average_cost": item.get("average_cost"), "price": quote.price, "price_source": quote.source, "price_as_of": quote.as_of, "fx_rate": item.get("fx_rate"), "value_inr": item.get("value_inr"), "weight": item.get("weight"), "return_pct": item.get("return_pct"), "realized_pnl": item.get("realized_pnl")}
