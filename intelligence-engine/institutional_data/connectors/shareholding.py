"""Shareholding connector — historical ownership (Promoter/FII/DII/MF/Public/Pledged).

P2.3: Correct NSE Master field mapping (pr_and_prgrp / public_val) + optional XBRL enrich.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

from institutional_data.connectors.base import Connector, ConnectorResult


class ShareholdingConnector(Connector):
    connector_id = "hd_shareholding_v1"
    source_id = "shareholding"
    official_source = "NSE / BSE shareholding patterns"

    def collect(self, **kwargs: Any) -> ConnectorResult:
        entity = str(kwargs.get("entity") or kwargs.get("ticker") or "").upper()
        t0 = time.time()
        if not entity:
            return ConnectorResult(
                ok=False, connector_id=self.connector_id, source_id=self.source_id, error="entity_required"
            )

        records: list[dict[str, Any]] = []
        errors: list[str] = []
        mode = "live"
        path = None

        # Primary: NSE corporate shareholding API (correct field map via ownership_intelligence)
        try:
            rows, path = self._nse_shareholding(
                entity,
                enrich_xbrl=bool(kwargs.get("enrich_xbrl", False)),
                xbrl_quarters=int(kwargs.get("xbrl_quarters") or 1),
            )
            records.extend(rows)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"nse:{str(exc)[:120]}")

        # Secondary: BSE HTML/pattern probe
        if not records:
            try:
                rows, path2 = self._bse_shareholding(entity)
                records.extend(rows)
                path = path or path2
            except Exception as exc:  # noqa: BLE001
                errors.append(f"bse:{str(exc)[:120]}")

        # Injected for tests
        if kwargs.get("injected"):
            mode = "injected"
            records = list(kwargs["injected"])

        ok = bool(records)
        return ConnectorResult(
            ok=ok,
            connector_id=self.connector_id,
            source_id=self.source_id,
            records=records,
            mode=mode,
            error=None if ok else (errors[0] if errors else "shareholding_unavailable"),
            diagnostics={
                "entity": entity,
                "errors": errors,
                "parse_path": path,
                "latency_ms": int((time.time() - t0) * 1000),
            },
            coverage_pct=100.0 if ok else 0.0,
            repair_items=[]
            if ok
            else [{"company": entity, "reason": "missing_shareholding", "connector": self.connector_id, "priority": 2}],
        )

    def validate(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        if not records:
            return {"ok": False, "reason": "empty"}
        bad = []
        for r in records:
            # Public already includes FII/DII/MF — never sum public with institutions.
            prom = float(r.get("promoter") or 0)
            pub = float(r.get("public") or 0)
            emp = float(r.get("employee_trusts") or 0)
            if r.get("promoter") is not None and r.get("public") is not None:
                master_total = prom + pub + emp
                if master_total > 105 or master_total < 80:
                    bad.append(
                        {
                            "period": r.get("period"),
                            "total": master_total,
                            "reason": "promoter_public_sum_out_of_range",
                        }
                    )
                continue
            # Fallback: promoter + institutional buckets when public missing
            total = sum(
                float(r.get(k) or 0) for k in ("promoter", "fii", "dii", "mutual_funds", "public")
            )
            if total > 105 or total < 80:
                bad.append({"period": r.get("period"), "total": total, "reason": "ownership_sum_out_of_range"})
        return {
            "ok": len(bad) == 0,
            "rejected": len(bad),
            "accepted": len(records) - len(bad),
            "failures": bad[:20],
        }

    def normalize(self, records: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        out = []
        for r in records:
            period_end = _period_end(r)
            out.append(
                {
                    "entity": str(r.get("entity") or kwargs.get("entity") or "").upper(),
                    "period": str(r.get("period") or period_end),
                    "period_end": period_end,
                    "promoter": _pct(r.get("promoter")),
                    "fii": _pct(r.get("fii") or r.get("fpi")),
                    "dii": _pct(r.get("dii")),
                    "mutual_funds": _pct(r.get("mutual_funds") or r.get("mf")),
                    "insurance": _pct(r.get("insurance")),
                    "public": _pct(r.get("public")),
                    "pledged": _pct(r.get("pledged") or r.get("promoter_pledged") or r.get("promoter_pledge_pct")),
                    "promoter_pledge": r.get("promoter_pledge"),
                    "employee_trusts": _pct(r.get("employee_trusts")),
                    "source": r.get("source") or "shareholding_connector",
                    "raw": r.get("raw"),
                }
            )
        return out

    def store(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.schema import pit_record

        entity = str(kwargs.get("entity") or (records[0].get("entity") if records else "")).upper()
        pits = []
        for r in records:
            pe = r.get("period_end") or r.get("period")
            pits.append(
                pit_record(
                    entity=entity,
                    kind="shareholding",
                    period=str(r.get("period")),
                    period_end=str(pe)[:10],
                    available_from=str(pe)[:10],
                    payload={
                        "promoter": r.get("promoter"),
                        "fii": r.get("fii"),
                        "dii": r.get("dii"),
                        "mutual_funds": r.get("mutual_funds"),
                        "insurance": r.get("insurance"),
                        "public": r.get("public"),
                        "pledged": r.get("pledged"),
                        "promoter_pledge": r.get("promoter_pledge"),
                        "employee_trusts": r.get("employee_trusts"),
                    },
                    source="shareholding_connector",
                    confidence=0.9,
                )
            )
        hd_store.put_series("shareholding", entity, pits)
        return {"written": len(pits), "entity": entity}

    def coverage(self, **kwargs: Any) -> dict[str, Any]:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.universe_priority import supported_universe

        u = kwargs.get("entities") or supported_universe()
        n = len(u) or 1
        covered = sum(1 for e in u if (hd_store.get_series("shareholding", e) or {}).get("records"))
        return {
            "connector_id": self.connector_id,
            "coverage_pct": round(100.0 * covered / n, 1),
            "covered": covered,
            "universe": n,
        }

    def _nse_shareholding(
        self,
        entity: str,
        *,
        enrich_xbrl: bool = False,
        xbrl_quarters: int = 1,
    ) -> tuple[list[dict[str, Any]], str]:
        from ownership_intelligence.master import quarter_timeline
        from ownership_intelligence.xbrl import enrich_quarter_with_xbrl

        tl = quarter_timeline(entity)
        rows = list(tl.get("quarters") or [])
        out: list[dict[str, Any]] = []
        for i, q in enumerate(rows):
            row = dict(q)
            if enrich_xbrl and i < max(0, int(xbrl_quarters)):
                row = enrich_quarter_with_xbrl(row)
            out.append(
                {
                    "entity": entity,
                    "period": row.get("period_end") or row.get("period_raw"),
                    "period_end": row.get("period_end"),
                    "period_raw": row.get("period_raw"),
                    "promoter": row.get("promoter"),
                    "fii": row.get("fii"),
                    "dii": row.get("dii"),
                    "mutual_funds": row.get("mutual_funds"),
                    "insurance": row.get("insurance"),
                    "public": row.get("public"),
                    "pledged": row.get("promoter_pledge_pct"),
                    "promoter_pledge": row.get("promoter_pledge"),
                    "employee_trusts": row.get("employee_trusts"),
                    "xbrl_url": row.get("xbrl_url"),
                    "filing_date": row.get("filing_date"),
                    "source": row.get("detail_source") or "nse_master",
                    "raw": row.get("raw"),
                }
            )
        return out, "nse_api"

    def _bse_shareholding(self, entity: str) -> tuple[list[dict[str, Any]], str]:
        from live_data.collectors.base import http_get

        # Soft probe — extract percentages if page renders server-side
        url = f"https://www.bseindia.com/stock-share-price/shareholding-pattern/{entity.lower()}/"
        try:
            raw = http_get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)",
                    "Referer": "https://www.bseindia.com/",
                },
                timeout=25,
            )
        except Exception:
            raw = http_get(
                "https://www.bseindia.com/corporates/Sharehold_Searchnew.aspx",
                headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)"},
                timeout=25,
            )
        text = raw.decode("utf-8", errors="replace")
        promoter = _find_pct(text, r"Promoter[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*%")
        fii = _find_pct(text, r"(?:FII|FPI)[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*%")
        dii = _find_pct(text, r"DII[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*%")
        public = _find_pct(text, r"Public[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*%")
        mf = _find_pct(text, r"Mutual\s*Fund[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*%")
        pledged = _find_pct(text, r"Pledg[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*%")
        if promoter is None and fii is None:
            return [], "bse_html_empty"
        today = datetime.now(timezone.utc).date().isoformat()
        return (
            [
                {
                    "entity": entity,
                    "period": today,
                    "period_end": today,
                    "promoter": promoter,
                    "fii": fii,
                    "dii": dii,
                    "mutual_funds": mf,
                    "public": public,
                    "pledged": pledged,
                    "source": "bse_html",
                }
            ],
            "bse_html",
        )


def _pct(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return round(float(v), 4)
    except Exception:
        return None


def _period_end(r: dict[str, Any]) -> str:
    from ownership_intelligence.dates import parse_nse_date

    for key in ("period_end", "period", "period_raw", "date"):
        pe = parse_nse_date(r.get(key))
        if pe:
            return pe
    return str(r.get("period_end") or r.get("period") or "")[:10]


def _find_pct(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None
