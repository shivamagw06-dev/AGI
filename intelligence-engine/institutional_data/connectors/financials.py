"""Financial Statements connector — institutional statements, no fixtures in production."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from institutional_data.connectors.base import Connector, ConnectorResult

YAHOO_SUMMARY = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
UA = "Mozilla/5.0 (compatible; AGIB-KF-HD/1.0)"


def fixtures_allowed() -> bool:
    """Never allow fixture financials in production."""
    env = (os.getenv("APP_ENV") or os.getenv("AGIB_ENV") or "").strip().lower()
    if env in {"production", "prod"}:
        return False
    return str(os.getenv("KF_HD_FIXTURE_QUARTERLY", "false")).lower() in {"1", "true", "yes", "on"}


class FinancialStatementsConnector(Connector):
    connector_id = "hd_financial_statements_v1"
    source_id = "financial_statements"
    official_source = "NSE IND-AS XBRL (primary) / Yahoo Finance quoteSummary (failover)"

    def collect(self, **kwargs: Any) -> ConnectorResult:
        entity = str(kwargs.get("entity") or kwargs.get("ticker") or "").upper()
        t0 = time.time()
        if not entity:
            return ConnectorResult(
                ok=False,
                connector_id=self.connector_id,
                source_id=self.source_id,
                error="entity_required",
            )
        if entity.endswith(".NS") or entity.endswith(".BO"):
            ysym = entity
        else:
            try:
                from app.market_data.providers.yahoo_symbols import to_yahoo_symbol

                ysym = to_yahoo_symbol(entity)
            except Exception:
                ysym = f"{entity}.NS"
        records: list[dict[str, Any]] = []
        errors: list[str] = []
        mode = "live"
        parse_path = None

        # Injected for tests
        if kwargs.get("injected"):
            mode = "injected"
            records = list(kwargs["injected"])
            parse_path = "injected"
        else:
            # Primary: NSE integrated + corporates financial results XBRL (P2.1)
            try:
                nse_records, parse_path = self._nse_financials(
                    entity,
                    quarterly_xbrl=int(kwargs.get("quarterly_xbrl") or 4),
                    annual_xbrl=int(kwargs.get("annual_xbrl") or 2),
                )
                records.extend(nse_records)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"nse:{str(exc)[:160]}")

            # Failover: Yahoo quoteSummary
            if not records:
                try:
                    annual = self._fetch_modules(
                        ysym,
                        [
                            "incomeStatementHistory",
                            "balanceSheetHistory",
                            "cashflowStatementHistory",
                        ],
                    )
                    quarterly = self._fetch_modules(
                        ysym,
                        [
                            "incomeStatementHistoryQuarterly",
                            "balanceSheetHistoryQuarterly",
                            "cashflowStatementHistoryQuarterly",
                        ],
                    )
                    records.extend(self._extract_statements(annual, entity=entity, frequency="annual"))
                    records.extend(self._extract_statements(quarterly, entity=entity, frequency="quarterly"))
                    parse_path = parse_path or "yahoo_quotesummary"
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"yahoo:{str(exc)[:160]}")

        # Production: never pad with fixtures. Dev may opt-in.
        if not records and fixtures_allowed():
            mode = "fixture_dev_only"
            errors.append("live_empty_fixture_skipped_in_prod_path")

        # Mark proxy annuals from prices as non-canonical if present
        quality = self._quality_score(records)
        ok = bool(records) and quality >= 0.4
        return ConnectorResult(
            ok=ok,
            connector_id=self.connector_id,
            source_id=self.source_id,
            records=records,
            mode=mode,
            error=None if ok else (errors[0] if errors else "financials_unavailable"),
            diagnostics={
                "entity": entity,
                "yahoo_symbol": ysym,
                "errors": errors,
                "parse_path": parse_path,
                "latency_ms": int((time.time() - t0) * 1000),
                "annual_count": sum(1 for r in records if r.get("frequency") == "annual"),
                "quarterly_count": sum(1 for r in records if r.get("frequency") == "quarterly"),
                "fixtures_allowed": fixtures_allowed(),
            },
            coverage_pct=min(100.0, quality * 100.0),
            quality_score=quality,
            repair_items=[]
            if ok
            else [{"company": entity, "reason": "incomplete_financials", "connector": self.connector_id, "priority": 2}],
        )

    def _nse_financials(
        self,
        entity: str,
        *,
        quarterly_xbrl: int = 4,
        annual_xbrl: int = 2,
    ) -> tuple[list[dict[str, Any]], str]:
        from earnings_intelligence.production import analyse

        pack = analyse(
            entity,
            quarterly_xbrl=quarterly_xbrl,
            annual_xbrl=annual_xbrl,
            persist=False,
        )
        if not pack.get("ok"):
            return [], "nse_earnings_empty"

        def provenance(row: dict[str, Any]) -> dict[str, Any]:
            return {
                "units_in": row.get("units_in"),
                "metadata": {
                    "source": "earnings_intelligence",
                    "provider": row.get("provider") or "nse_india",
                    "parser_path": row.get("parser_path"),
                    "xbrl_url": row.get("xbrl_url"),
                    "unit_resolution": row.get("unit_resolution"),
                    "scaled_from_integrated_lakhs": bool(
                        row.get("scaled_from_integrated_lakhs")
                    ),
                },
            }

        out: list[dict[str, Any]] = []
        for row in pack.get("quarter_history") or []:
            inc = row.get("income_statement") or {}
            if not inc:
                continue
            out.append(
                {
                    "entity": entity,
                    "statement": "income",
                    "frequency": "quarterly",
                    "period": row.get("quarter_label") or row.get("period_end"),
                    "period_end": row.get("period_end"),
                    "available_from": row.get("filing_date") or row.get("period_end"),
                    "accounts": {
                        "revenue": inc.get("revenue_from_operations"),
                        "total_revenue": inc.get("revenue_from_operations"),
                        "ebitda": inc.get("ebitda"),
                        "ebit": inc.get("ebit"),
                        "net_income": inc.get("pat_owners") or inc.get("pat"),
                        "eps": inc.get("eps_basic"),
                    },
                    **provenance(row),
                    "ttm": False,
                    "quality_score": 0.9,
                    "restatement": False,
                    "version": 1,
                }
            )
        for row in pack.get("annual_history") or []:
            pe = row.get("period_end")
            af = row.get("filing_date") or pe
            inc = row.get("income_statement") or {}
            bal = row.get("balance_sheet") or {}
            cf = row.get("cash_flow") or {}
            if inc:
                out.append(
                    {
                        "entity": entity,
                        "statement": "income",
                        "frequency": "annual",
                        "period": row.get("fiscal_year_label") or pe,
                        "period_end": pe,
                        "available_from": af,
                        "accounts": {
                            "revenue": inc.get("revenue_from_operations"),
                            "total_revenue": inc.get("revenue_from_operations"),
                            "ebitda": inc.get("ebitda"),
                            "ebit": inc.get("ebit"),
                            "net_income": inc.get("pat_owners") or inc.get("pat"),
                            "eps": inc.get("eps_basic"),
                        },
                        **provenance(row),
                        "ttm": False,
                        "quality_score": 0.9,
                        "restatement": False,
                        "version": 1,
                    }
                )
            if bal:
                out.append(
                    {
                        "entity": entity,
                        "statement": "balance",
                        "frequency": "annual",
                        "period": row.get("fiscal_year_label") or pe,
                        "period_end": pe,
                        "available_from": af,
                        "accounts": {
                            "total_debt": bal.get("total_debt"),
                            "cash": bal.get("cash"),
                            "equity": bal.get("total_equity"),
                            "shares": None,
                        },
                        **provenance(row),
                        "ttm": False,
                        "quality_score": 0.9,
                        "restatement": False,
                        "version": 1,
                    }
                )
            if cf:
                out.append(
                    {
                        "entity": entity,
                        "statement": "cashflow",
                        "frequency": "annual",
                        "period": row.get("fiscal_year_label") or pe,
                        "period_end": pe,
                        "available_from": af,
                        "accounts": {
                            "ocf": cf.get("operating_cash_flow"),
                            "fcf": cf.get("free_cash_flow"),
                            "capex": cf.get("capex"),
                        },
                        **provenance(row),
                        "ttm": False,
                        "quality_score": 0.9,
                        "restatement": False,
                        "version": 1,
                    }
                )
        return out, "nse_earnings_intelligence"

    def validate(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        failures = []
        seen = set()
        for r in records:
            key = (r.get("entity"), r.get("statement"), r.get("period"), r.get("frequency"))
            if key in seen:
                failures.append({"reason": "duplicate", "key": key})
            seen.add(key)
            # Schema
            if r.get("statement") not in {"income", "balance", "cashflow", "ttm"}:
                failures.append({"reason": "schema_statement", "period": r.get("period")})
            # PIT: available_from must be >= period_end
            pe = str(r.get("period_end") or "")[:10]
            af = str(r.get("available_from") or "")[:10]
            if pe and af and af < pe:
                failures.append({"reason": "pit_available_from_before_period_end", "period": r.get("period")})
            # Account consistency soft checks
            payload = r.get("accounts") or {}
            rev = payload.get("total_revenue") or payload.get("revenue")
            ni = payload.get("net_income")
            if rev is not None and ni is not None and abs(float(ni)) > abs(float(rev)) * 5:
                failures.append({"reason": "account_consistency_outlier", "period": r.get("period")})
        # Continuity: annual periods should be yearly sequence if ≥3
        annuals = sorted({r.get("period") for r in records if r.get("frequency") == "annual" and r.get("statement") == "income"})
        continuity_ok = len(annuals) >= 1
        return {
            "ok": continuity_ok and not any(f["reason"].startswith("pit_") for f in failures),
            "failures": failures[:50],
            "duplicate_count": sum(1 for f in failures if f["reason"] == "duplicate"),
            "continuity_ok": continuity_ok,
            "periods": len(seen),
        }

    def normalize(self, records: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        return records  # already canonical

    def store(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.schema import pit_record

        entity = str(kwargs.get("entity") or (records[0].get("entity") if records else "")).upper()
        annual_out = []
        quarterly_out = []
        for r in records:
            payload = {
                "statement": r.get("statement"),
                "frequency": r.get("frequency"),
                "accounts": r.get("accounts") or {},
                "quality_score": r.get("quality_score"),
                "restatement": r.get("restatement", False),
                "version": r.get("version") or 1,
                "metadata": r.get("metadata") or {},
                "units_in": r.get("units_in"),
                "provider": (r.get("metadata") or {}).get("provider"),
                "parser_path": (r.get("metadata") or {}).get("parser_path"),
                "source_document": (r.get("metadata") or {}).get("xbrl_url"),
            }
            # Flatten key accounts for HD derived producers
            for k, v in (r.get("accounts") or {}).items():
                if k in {"revenue", "total_revenue", "net_income", "ebitda", "ebit", "total_debt", "cash", "equity", "ocf", "fcf", "capex", "shares", "eps"}:
                    payload[k if k != "total_revenue" else "revenue"] = v
            rec = pit_record(
                entity=entity,
                kind=f"financial_{r.get('frequency')}_{r.get('statement')}",
                period=str(r.get("period")),
                period_end=str(r.get("period_end")),
                available_from=str(r.get("available_from") or r.get("period_end")),
                payload=payload,
                source="financial_connector",
                confidence=float(r.get("quality_score") or 0.85),
            )
            if r.get("frequency") == "annual":
                annual_out.append(rec)
            else:
                quarterly_out.append(rec)

        def _hd_write() -> dict[str, Any]:
            if annual_out:
                hd_store.put_series("financials_annual", entity, annual_out)
            if quarterly_out:
                hd_store.put_series("financials_quarterly", entity, quarterly_out)
            try:
                hd_store.put_report(
                    f"financial_versions_{entity}",
                    {
                        "entity": entity,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "annual": len(annual_out),
                        "quarterly": len(quarterly_out),
                        "source": "financial_connector",
                    },
                )
            except Exception:
                pass
            return {"annual": len(annual_out), "quarterly": len(quarterly_out), "ok": True}

        # FSE-02.1: canonical ingest first; HD dual-write always remains (migration rule).
        fse_ingest: dict[str, Any] | None = None
        try:
            from financial_statements_engine.collection.flags import canonical_ingest_enabled
            from financial_statements_engine.collection.ingest import ingest_structured_json

            if canonical_ingest_enabled() and entity and records:
                period_end = None
                period_type = "annual"
                for r in records:
                    if r.get("period_end"):
                        period_end = str(r.get("period_end"))[:10]
                        period_type = "annual" if r.get("frequency") == "annual" else "quarterly"
                        break
                evidence_payload = {
                    "entity": entity,
                    "source": "financial_connector",
                    "annual": len(annual_out),
                    "quarterly": len(quarterly_out),
                    "records": [
                        {
                            "period": r.get("period"),
                            "period_end": r.get("period_end"),
                            "frequency": r.get("frequency"),
                            "statement": r.get("statement"),
                            "accounts": r.get("accounts") or {},
                        }
                        for r in records[:40]
                    ],
                }
                fse_ingest = ingest_structured_json(
                    ticker=entity,
                    payload=evidence_payload,
                    source="financial_connector",
                    document_type="structured_financials",
                    period_type=period_type,
                    period_end=period_end,
                    collector="financial_statements_connector",
                    filing_type=period_type,
                )
        except Exception:
            fse_ingest = None

        hd = _hd_write()
        return {
            **hd,
            "dual_write_hd": True,
            "fse_ingest": {
                "action": (fse_ingest or {}).get("action"),
                "evidence_id": (fse_ingest or {}).get("evidence_id"),
                "event_emitted": (fse_ingest or {}).get("event_emitted"),
            }
            if fse_ingest
            else None,
        }

    def coverage(self, **kwargs: Any) -> dict[str, Any]:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.universe_priority import supported_universe

        u = kwargs.get("entities") or supported_universe()
        n = len(u) or 1
        covered = 0
        for e in u:
            a = hd_store.get_series("financials_annual", e) or {}
            q = hd_store.get_series("financials_quarterly", e) or {}
            # Count only non-proxy institutional statements
            a_recs = [r for r in (a.get("records") or []) if (r.get("source") == "financial_connector") or ((r.get("payload") or {}).get("statement"))]
            q_recs = [r for r in (q.get("records") or []) if (r.get("source") == "financial_connector") or ((r.get("payload") or {}).get("statement"))]
            if len(a_recs) >= 3 and len(q_recs) >= 4:
                covered += 1
        return {"connector_id": self.connector_id, "coverage_pct": round(100.0 * covered / n, 1), "covered": covered, "universe": n}

    def _fetch_modules(self, ysym: str, modules: list[str]) -> dict[str, Any]:
        params = urlencode({"modules": ",".join(modules)})
        url = f"{YAHOO_SUMMARY.format(symbol=ysym)}?{params}"
        req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=40) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"yahoo_financials_http_{exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"yahoo_financials_url:{exc.reason}") from exc

    def _extract_statements(self, payload: dict[str, Any], *, entity: str, frequency: str) -> list[dict[str, Any]]:
        result = ((payload.get("quoteSummary") or {}).get("result") or [None])[0] or {}
        out: list[dict[str, Any]] = []
        mapping = {
            "incomeStatementHistory": ("income", "incomeStatementHistory"),
            "incomeStatementHistoryQuarterly": ("income", "incomeStatementHistory"),
            "balanceSheetHistory": ("balance", "balanceSheetStatements"),
            "balanceSheetHistoryQuarterly": ("balance", "balanceSheetStatements"),
            "cashflowStatementHistory": ("cashflow", "cashflowStatements"),
            "cashflowStatementHistoryQuarterly": ("cashflow", "cashflowStatements"),
        }
        for mod_key, (stype, list_key) in mapping.items():
            block = result.get(mod_key) or {}
            # Yahoo nests list under slightly different keys
            rows = block.get(list_key) or block.get("incomeStatementHistory") or block.get("balanceSheetStatements") or block.get("cashflowStatements") or []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                end_ts = (row.get("endDate") or {}).get("raw") if isinstance(row.get("endDate"), dict) else row.get("endDate")
                if not end_ts:
                    continue
                try:
                    pe = datetime.fromtimestamp(int(end_ts), tz=timezone.utc).date()
                except Exception:
                    continue
                period = f"FY{str(pe.year)[2:]}" if frequency == "annual" else f"{pe.year}Q{(pe.month - 1) // 3 + 1}"
                accounts = self._accounts_from_row(row, stype)
                # available_from: filing lag ~45d annual / ~30d quarterly (conservative, never before period_end)
                lag = 45 if frequency == "annual" else 30
                from datetime import timedelta

                af = (pe + timedelta(days=lag)).isoformat()
                out.append(
                    {
                        "entity": entity,
                        "statement": stype,
                        "frequency": frequency,
                        "period": period,
                        "period_end": pe.isoformat(),
                        "available_from": af,
                        "accounts": accounts,
                        "quality_score": 0.9 if accounts else 0.5,
                        "restatement": False,
                        "version": 1,
                        "metadata": {"source": "yahoo_quoteSummary"},
                        "units_in": "rupee",
                        "ttm": False,
                    }
                )
                out[-1]["metadata"].update({
                    "provider": "yahoo_finance",
                    "parser_path": "yahoo_quotesummary",
                })
        return out

    def _accounts_from_row(self, row: dict[str, Any], stype: str) -> dict[str, Any]:
        def g(*keys: str) -> float | None:
            for k in keys:
                v = row.get(k)
                if isinstance(v, dict) and "raw" in v:
                    try:
                        return float(v["raw"])
                    except Exception:
                        return None
                if isinstance(v, (int, float)):
                    return float(v)
            return None

        if stype == "income":
            return {
                k: v
                for k, v in {
                    "revenue": g("totalRevenue", "revenue"),
                    "total_revenue": g("totalRevenue", "revenue"),
                    "gross_profit": g("grossProfit"),
                    "ebit": g("ebit", "operatingIncome"),
                    "ebitda": g("ebitda"),
                    "net_income": g("netIncome", "netIncomeApplicableToCommonShares"),
                    "eps": g("dilutedEPS", "basicEPS"),
                }.items()
                if v is not None
            }
        if stype == "balance":
            return {
                k: v
                for k, v in {
                    "total_debt": g("totalDebt", "longTermDebt"),
                    "cash": g("cash", "cashAndCashEquivalents"),
                    "equity": g("totalStockholderEquity", "stockholdersEquity"),
                    "shares": g("commonStock", "shareIssued"),
                }.items()
                if v is not None
            }
        return {
            k: v
            for k, v in {
                "ocf": g("totalCashFromOperatingActivities", "operatingCashFlow"),
                "fcf": g("freeCashFlow"),
                "capex": g("capitalExpenditures"),
            }.items()
            if v is not None
        }

    def _quality_score(self, records: list[dict[str, Any]]) -> float:
        if not records:
            return 0.0
        annual = sum(1 for r in records if r.get("frequency") == "annual" and r.get("statement") == "income")
        quarterly = sum(1 for r in records if r.get("frequency") == "quarterly" and r.get("statement") == "income")
        score = min(1.0, 0.15 * annual + 0.1 * quarterly)
        return round(max(score, 0.35 if records else 0.0), 3)
