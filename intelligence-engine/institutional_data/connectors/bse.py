"""BSE Corporate Actions connector — multi-strategy parsers, never silent HTML death."""

from __future__ import annotations

import csv
import io
import json
import re
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from institutional_data.connectors.base import Connector, ConnectorResult


class BSECorporateActionsConnector(Connector):
    connector_id = "lidi_bse_corporate_actions_v1"
    source_id = "bse_corporate_actions"
    official_source = "BSE India"

    def collect(self, **kwargs: Any) -> ConnectorResult:
        t0 = time.time()
        diagnostics: dict[str, Any] = {"strategies": []}
        injected = kwargs.get("injected_csv")
        allow_sample = bool(kwargs.get("allow_recorded_sample"))

        # Strategy chain: Primary JSON API → Secondary CSV/JSON → HTML table → Regex → Diagnostics
        strategies = (
            ("primary_json_api", self._strategy_json_api),
            ("secondary_csv_like", self._strategy_csv_like),
            ("fallback_html_table", self._strategy_html_table),
            ("fallback_regex", self._strategy_regex),
        )
        records: list[dict[str, Any]] = []
        parse_path = None
        mode = "live"
        last_err = None

        if injected is not None:
            mode = "injected"
            text = injected if isinstance(injected, str) else injected.decode("utf-8", errors="replace")
            records, parse_path = self._parse_any(text)
            diagnostics["strategies"].append({"name": "injected", "ok": bool(records), "n": len(records)})
        else:
            for name, fn in strategies:
                try:
                    got, path, meta = fn()
                    diagnostics["strategies"].append({"name": name, "ok": bool(got), "n": len(got or []), **(meta or {})})
                    if got:
                        records = got
                        parse_path = path
                        break
                except Exception as exc:  # noqa: BLE001
                    last_err = str(exc)[:200]
                    diagnostics["strategies"].append({"name": name, "ok": False, "error": last_err})

            if not records and allow_sample:
                mode = "recorded_sample"
                from pathlib import Path

                sample = Path(__file__).resolve().parents[2] / "live_data" / "samples" / "bse_corporate_actions.csv"
                if sample.exists():
                    records, parse_path = self._parse_any(sample.read_text(encoding="utf-8"))
                    diagnostics["strategies"].append({"name": "recorded_sample", "ok": bool(records), "n": len(records)})

        # Always persist parser diagnostics for repair
        self._store_diagnostics(diagnostics, parse_path=parse_path, error=last_err)

        ok = bool(records)
        result = ConnectorResult(
            ok=ok,
            connector_id=self.connector_id,
            source_id=self.source_id,
            records=records,
            mode=mode,
            error=None if ok else (last_err or "bse_all_strategies_exhausted"),
            diagnostics={
                **diagnostics,
                "parse_path": parse_path,
                "latency_ms": int((time.time() - t0) * 1000),
                "success_pct": self._strategy_success_pct(diagnostics),
                "failure_pct": round(100.0 - (self._strategy_success_pct(diagnostics) or 0), 1),
            },
            coverage_pct=100.0 if ok else 0.0,
        )
        if not ok:
            result.repair_items.append(
                {
                    "reason": "bse_parser_exhausted",
                    "connector": self.connector_id,
                    "priority": 1,
                    "diagnostics": diagnostics.get("strategies"),
                }
            )
        return result

    def validate(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        if not records:
            return {"ok": False, "reason": "empty"}
        required = ("symbol", "action_type", "ex_date")
        bad = [r for r in records if not all(r.get(k) for k in required)]
        return {"ok": len(bad) < len(records), "accepted": len(records) - len(bad), "rejected": len(bad)}

    def normalize(self, records: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        out = []
        for r in records:
            sym = str(r.get("symbol") or r.get("ticker") or "").upper().strip()
            if not sym:
                continue
            out.append(
                {
                    "symbol": sym,
                    "action_type": str(r.get("action_type") or r.get("purpose") or "unknown").lower(),
                    "ex_date": str(r.get("ex_date") or r.get("exDate") or "")[:10],
                    "record_date": str(r.get("record_date") or "")[:10] or None,
                    "ratio": r.get("ratio"),
                    "amount": r.get("amount"),
                    "source": "bse",
                    "raw": {k: r.get(k) for k in ("security", "purpose", "bc_start", "bc_end") if r.get(k)},
                }
            )
        return out

    def store(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.schema import pit_record

        by_sym: dict[str, list] = {}
        for r in records:
            by_sym.setdefault(r["symbol"], []).append(r)
        written = 0
        for sym, rows in by_sym.items():
            pits = []
            for r in rows:
                d = r.get("ex_date") or datetime.utcnow().date().isoformat()
                pits.append(
                    pit_record(
                        entity=sym,
                        kind="corporate_action",
                        period=d,
                        period_end=d,
                        available_from=d,
                        payload=r,
                        source="bse_connector",
                        confidence=0.9,
                    )
                )
            hd_store.put_series("corporate_actions", sym, pits)
            written += len(pits)
        # Also mirror via legacy collector path for LIDI validated store
        try:
            from live_data.collectors.bse_corporate_actions import collect_bse_corporate_actions

            # Prefer connector-owned store; soft-call legacy only when injected for compat tests
            if kwargs.get("delegate_legacy"):
                collect_bse_corporate_actions(
                    injected_csv=kwargs.get("injected_csv"),
                    allow_recorded_sample=bool(kwargs.get("allow_recorded_sample")),
                )
        except Exception:
            pass
        return {"written": written, "symbols": len(by_sym)}

    def coverage(self, **kwargs: Any) -> dict[str, Any]:
        from knowledge_factory.historical_depth.universe_priority import supported_universe
        from knowledge_factory.historical_depth import store as hd_store

        u = supported_universe()
        n = len(u) or 1
        covered = sum(1 for e in u if (hd_store.get_series("corporate_actions", e) or {}).get("records"))
        return {"connector_id": self.connector_id, "coverage_pct": round(100.0 * covered / n, 1), "covered": covered, "universe": n}

    # --- strategies -----------------------------------------------------------

    def _urls(self) -> list[str]:
        today = datetime.utcnow().date()
        fdate = (today - timedelta(days=180)).strftime("%d/%m/%Y")
        tdate = today.strftime("%d/%m/%Y")
        qs = urlencode(
            {
                "Fdate": fdate,
                "TDate": tdate,
                "Purposecode": "",
                "ddlcategorys": "",
                "ddlindicators": "",
                "scripcode": "",
                "segment": "0",
                "strSearch": "S",
            }
        )
        return [
            f"https://api.bseindia.com/BseIndiaAPI/api/DefaultData/GetData?{qs}",
            f"https://api.bseindia.com/BseIndiaAPI/api/Corpact/w?{qs}",
            "https://api.bseindia.com/BseIndiaAPI/api/DefaultData/GetData?segment=0&strSearch=S",
            "https://www.bseindia.com/corporates/corporate_act.aspx",
            "https://www.bseindia.com/corporates/corporates_act.html",
        ]

    def _http(self, url: str) -> bytes:
        from live_data.collectors.base import http_get

        return http_get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)",
                "Accept": "application/json,text/csv,text/html,*/*",
                "Referer": "https://www.bseindia.com/",
                "Origin": "https://www.bseindia.com",
            },
            timeout=30,
        )

    def _strategy_json_api(self) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
        for url in self._urls():
            if "api.bseindia.com" not in url:
                continue
            raw = self._http(url)
            text = raw.decode("utf-8", errors="replace")
            rows, path = self._parse_json(text)
            if rows:
                return rows, path, {"url": url}
        return [], "json", {"url": None}

    def _strategy_csv_like(self) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
        for url in self._urls():
            raw = self._http(url)
            text = raw.decode("utf-8", errors="replace")
            if "," in text and ("Security" in text or "Purpose" in text or "Ex Date" in text):
                rows, path = self._parse_csv(text)
                if rows:
                    return rows, path, {"url": url}
        return [], "csv", {}

    def _strategy_html_table(self) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
        for url in self._urls():
            if "api." in url:
                continue
            raw = self._http(url)
            text = raw.decode("utf-8", errors="replace")
            rows, path = self._parse_html_table(text)
            if rows:
                return rows, path, {"url": url}
        return [], "html_table", {}

    def _strategy_regex(self) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
        for url in self._urls():
            raw = self._http(url)
            text = raw.decode("utf-8", errors="replace")
            rows = self._parse_regex(text)
            if rows:
                return rows, "regex", {"url": url}
        return [], "regex", {}

    def _parse_any(self, text: str) -> tuple[list[dict[str, Any]], str]:
        for fn in (self._parse_json, self._parse_csv, self._parse_html_table):
            rows, p = fn(text)
            if rows:
                return rows, p
        return self._parse_regex(text), "regex"

    def _parse_json(self, text: str) -> tuple[list[dict[str, Any]], str]:
        try:
            data = json.loads(text)
        except Exception:
            return [], "json"
        rows_raw = data if isinstance(data, list) else (data.get("Table") or data.get("data") or data.get("Table1") or [])
        if isinstance(data, dict) and not rows_raw:
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    rows_raw = v
                    break
        out = []
        for r in rows_raw or []:
            if not isinstance(r, dict):
                continue
            sym = self._map_symbol(r.get("SECURITY_NAME") or r.get("scrip_Name") or r.get("Security Name") or r.get("scripname"))
            purpose = r.get("PURPOSE") or r.get("Purpose") or r.get("purpose") or ""
            ex = r.get("EX_DATE") or r.get("Ex Date") or r.get("ex_dt") or r.get("ExDt") or ""
            if not (sym and purpose):
                continue
            out.append(
                {
                    "symbol": sym,
                    "action_type": str(purpose).split()[0].lower() if purpose else "unknown",
                    "purpose": purpose,
                    "ex_date": str(ex)[:10],
                    "security": r.get("SECURITY_NAME") or r.get("Security Name"),
                }
            )
        return out, "json"

    def _parse_csv(self, text: str) -> tuple[list[dict[str, Any]], str]:
        # Delegate to existing resilient parser when available
        try:
            from live_data.collectors import bse_corporate_actions as bse

            actions, _, path = bse._parse_actions_any(text)
            out = []
            for a in actions or []:
                out.append(
                    {
                        "symbol": a.get("symbol") or a.get("ticker"),
                        "action_type": a.get("action_type") or a.get("purpose"),
                        "ex_date": a.get("ex_date") or a.get("effective_date"),
                        "purpose": a.get("purpose"),
                        "security": a.get("security"),
                    }
                )
            return [r for r in out if r.get("symbol")], path or "csv"
        except Exception:
            pass
        try:
            reader = csv.DictReader(io.StringIO(text))
            out = []
            for r in reader:
                keys = {k.lower().strip(): v for k, v in r.items() if k}
                sym = self._map_symbol(keys.get("security name") or keys.get("security") or keys.get("symbol"))
                purpose = keys.get("purpose") or keys.get("action") or ""
                ex = keys.get("ex date") or keys.get("ex_date") or ""
                if sym:
                    out.append({"symbol": sym, "action_type": purpose.split()[0].lower() if purpose else "unknown", "ex_date": str(ex)[:10], "purpose": purpose})
            return out, "csv"
        except Exception:
            return [], "csv"

    def _parse_html_table(self, text: str) -> tuple[list[dict[str, Any]], str]:
        try:
            from live_data.collectors import bse_corporate_actions as bse

            actions, _, path = bse._parse_actions_any(text)
            out = []
            for a in actions or []:
                if a.get("symbol") or a.get("ticker"):
                    out.append(
                        {
                            "symbol": a.get("symbol") or a.get("ticker"),
                            "action_type": a.get("action_type") or "unknown",
                            "ex_date": a.get("ex_date") or "",
                            "purpose": a.get("purpose"),
                        }
                    )
            return out, path or "html_table"
        except Exception:
            return [], "html_table"

    def _parse_regex(self, text: str) -> list[dict[str, Any]]:
        # Last-ditch: find ticker-like + dividend/split nearby
        out = []
        for m in re.finditer(
            r"(INFY|TCS|RELIANCE|HDFCBANK|ICICIBANK|WIPRO|SBIN|ITC)[^.]{0,80}(Dividend|Split|Bonus|Rights)",
            text,
            re.I,
        ):
            out.append(
                {
                    "symbol": m.group(1).upper(),
                    "action_type": m.group(2).lower(),
                    "ex_date": datetime.utcnow().date().isoformat(),
                    "purpose": m.group(2),
                }
            )
        return out

    def _map_symbol(self, name: Any) -> str | None:
        if not name:
            return None
        s = str(name).upper().strip()
        if re.fullmatch(r"[A-Z0-9]{1,15}", s):
            return s
        from live_data.collectors.bse_corporate_actions import NAME_MAP

        return NAME_MAP.get(s) or NAME_MAP.get(s.replace(".", ""))

    def _strategy_success_pct(self, diagnostics: dict[str, Any]) -> float:
        rows = diagnostics.get("strategies") or []
        if not rows:
            return 0.0
        ok = sum(1 for r in rows if r.get("ok"))
        return round(100.0 * ok / len(rows), 1)

    def _store_diagnostics(self, diagnostics: dict[str, Any], *, parse_path: str | None, error: str | None) -> None:
        try:
            from knowledge_factory.historical_depth import store as hd_store

            hd_store.put_report(
                "bse_parser_diagnostics",
                {
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                    "parse_path": parse_path,
                    "error": error,
                    "strategies": diagnostics.get("strategies"),
                    "success_pct": self._strategy_success_pct(diagnostics),
                },
            )
        except Exception:
            pass
