"""RBI Macro connector — structured series ingestion with versioned history."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from institutional_data.connectors.base import Connector, ConnectorResult

# Canonical series catalogue — missing series → structured warnings, not silent failure.
CANONICAL_SERIES = (
    {"series_id": "rbi.repo_rate", "metric": "repo_rate", "frequency": "event", "units": "percent"},
    {"series_id": "rbi.reverse_repo_rate", "metric": "reverse_repo_rate", "frequency": "event", "units": "percent"},
    {"series_id": "rbi.crr", "metric": "crr", "frequency": "event", "units": "percent"},
    {"series_id": "rbi.slr", "metric": "slr", "frequency": "event", "units": "percent"},
    {"series_id": "rbi.cpi", "metric": "cpi", "frequency": "monthly", "units": "percent"},
    {"series_id": "rbi.wpi", "metric": "wpi", "frequency": "monthly", "units": "percent"},
    {"series_id": "rbi.iip", "metric": "iip", "frequency": "monthly", "units": "percent"},
    {"series_id": "rbi.gdp", "metric": "gdp", "frequency": "quarterly", "units": "percent"},
    {"series_id": "rbi.fx_reserves_usd_bn", "metric": "fx_reserves_usd_bn", "frequency": "weekly", "units": "usd_bn"},
    {"series_id": "rbi.gsec_10y_yield", "metric": "gsec_10y_yield", "frequency": "daily", "units": "percent"},
    {"series_id": "rbi.bank_credit_growth_yoy", "metric": "bank_credit_growth_yoy", "frequency": "fortnightly", "units": "percent"},
    {"series_id": "rbi.aggregate_deposits_growth_yoy", "metric": "aggregate_deposits_growth_yoy", "frequency": "fortnightly", "units": "percent"},
)


class RBIMacroConnector(Connector):
    connector_id = "lidi_rbi_dbie_v1"
    source_id = "rbi_dbie"
    official_source = "Reserve Bank of India DBIE"

    def collect(self, **kwargs: Any) -> ConnectorResult:
        t0 = time.time()
        warnings: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        mode = "live"
        injected = kwargs.get("injected_json")
        allow_sample = bool(kwargs.get("allow_recorded_sample"))

        if injected is not None:
            mode = "injected"
            payload = json.loads(injected) if isinstance(injected, str) else injected
            records = self._from_payload(payload)
        else:
            # 1) Structured open-data / JSON probes
            records, path, err = self._collect_structured()
            # 2) Legacy HTML metric extract via existing collector helpers
            if not records:
                records, path2, err2 = self._collect_html_metrics()
                path = path or path2
                err = err or err2
            if not records and allow_sample:
                mode = "recorded_sample"
                from pathlib import Path

                sample = Path(__file__).resolve().parents[2] / "live_data" / "samples" / "rbi_dbie_key_rates.json"
                if sample.exists():
                    payload = json.loads(sample.read_text(encoding="utf-8"))
                    records = self._from_payload(payload)
                    path = "recorded_sample"
                    err = None
            diagnostics_path = path if "path" in dir() else None  # noqa: F821 — set below
            _ = diagnostics_path

        # Structured warnings for missing canonical series
        have = {str(r.get("metric")) for r in records}
        for spec in CANONICAL_SERIES:
            if spec["metric"] not in have:
                warnings.append(
                    {
                        "series_id": spec["series_id"],
                        "metric": spec["metric"],
                        "warning": "missing_series",
                        "frequency": spec["frequency"],
                        "units": spec["units"],
                    }
                )

        ok = bool(records)
        return ConnectorResult(
            ok=ok,
            connector_id=self.connector_id,
            source_id=self.source_id,
            records=records,
            mode=mode,
            error=None if ok else "rbi_no_structured_series",
            diagnostics={
                "warnings": warnings,
                "series_found": len(records),
                "series_missing": len(warnings),
                "latency_ms": int((time.time() - t0) * 1000),
                "parse_path": locals().get("path") or mode,
            },
            coverage_pct=round(100.0 * len(have) / max(1, len(CANONICAL_SERIES)), 1),
            repair_items=[]
            if ok
            else [{"reason": "rbi_structured_series_missing", "connector": self.connector_id, "priority": 1}],
        )

    def validate(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        if not records:
            return {"ok": False, "reason": "empty"}
        bad = [r for r in records if r.get("value") is None and r.get("metric") != "liquidity_stance"]
        return {"ok": len(bad) == 0, "accepted": len(records) - len(bad), "rejected": len(bad)}

    def normalize(self, records: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        out = []
        now = datetime.now(timezone.utc).isoformat()
        for r in records:
            metric = str(r.get("metric") or "")
            spec = next((s for s in CANONICAL_SERIES if s["metric"] == metric), None)
            out.append(
                {
                    "series_id": (spec or {}).get("series_id") or f"rbi.{metric}",
                    "metric": metric,
                    "value": r.get("value"),
                    "frequency": (spec or {}).get("frequency") or r.get("frequency") or "unknown",
                    "units": (spec or {}).get("units") or r.get("unit") or r.get("units"),
                    "source": "RBI",
                    "last_update": r.get("as_of") or r.get("last_update") or now[:10],
                    "history": r.get("history") or [],
                    "version": r.get("version") or 1,
                    "as_of": r.get("as_of"),
                }
            )
        return out

    def store(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        from knowledge_factory.historical_depth import store as hd_store
        from live_data import store as lidi_store

        # Versioned macro object catalogue
        catalogue = {
            "source": "RBI",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "series": records,
            "version": 1,
        }
        try:
            prior = lidi_store.get_object("rbi_macro", "CATALOGUE") or {}
            catalogue["version"] = int(prior.get("version") or 0) + 1
            # Merge history points
            by_id = {s["series_id"]: s for s in (prior.get("series") or []) if s.get("series_id")}
            for s in records:
                sid = s["series_id"]
                old = by_id.get(sid) or {}
                hist = list(old.get("history") or [])
                point = {"as_of": s.get("last_update"), "value": s.get("value")}
                if point["value"] is not None and point not in hist:
                    hist.append(point)
                s["history"] = hist[-500:]
                by_id[sid] = s
            catalogue["series"] = list(by_id.values())
            lidi_store.put_object("rbi_macro", "CATALOGUE", catalogue)
        except Exception:
            pass

        # Bridge into HD macro history
        hd_rows = []
        for s in records:
            if s.get("value") is None:
                continue
            period = str(s.get("last_update") or "")[:7] or datetime.utcnow().strftime("%Y-%m")
            hd_rows.append(
                {
                    "period": period,
                    "metric": s.get("metric"),
                    "value": s.get("value"),
                    "unit": s.get("units"),
                    "source": "rbi_connector",
                    "series_id": s.get("series_id"),
                }
            )
        if hd_rows:
            try:
                hd_store.put_macro_history(hd_rows)
            except Exception:
                pass
        return {"series_stored": len(records), "catalogue_version": catalogue.get("version")}

    def coverage(self, **kwargs: Any) -> dict[str, Any]:
        try:
            from live_data import store as lidi_store

            cat = lidi_store.get_object("rbi_macro", "CATALOGUE") or {}
            n = len(cat.get("series") or [])
        except Exception:
            n = 0
        return {
            "connector_id": self.connector_id,
            "coverage_pct": round(100.0 * n / max(1, len(CANONICAL_SERIES)), 1),
            "series_present": n,
            "series_canonical": len(CANONICAL_SERIES),
        }

    def _from_payload(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return list(payload.get("series") or [])

    def _collect_structured(self) -> tuple[list[dict[str, Any]], str | None, str | None]:
        """Probe JSON-ish RBI endpoints; fail soft with warnings."""
        urls = (
            "https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx?param=4",
            "https://dbie.rbi.org.in/DBIE/#/dbie/home",
        )
        last = None
        for url in urls:
            try:
                from live_data.collectors.base import http_get

                raw = http_get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)"}, timeout=25)
                text = raw.decode("utf-8", errors="replace")
                # Try JSON island
                if text.strip().startswith("{") or text.strip().startswith("["):
                    data = json.loads(text)
                    rows = self._from_payload(data if isinstance(data, dict) else {"series": data})
                    if rows:
                        return rows, "structured_json", None
            except Exception as exc:  # noqa: BLE001
                last = str(exc)[:160]
        return [], None, last

    def _collect_html_metrics(self) -> tuple[list[dict[str, Any]], str | None, str | None]:
        try:
            from live_data.collectors import rbi_dbie as rbi

            # Reuse HTML metric patterns without requiring full collector success envelope
            raw, url = None, None

            def _fetch():
                nonlocal raw, url
                import ssl
                from urllib.request import HTTPSHandler, Request, build_opener

                last = None
                for u in rbi.DBIE_URLS:
                    try:
                        opener = build_opener(HTTPSHandler(context=ssl.create_default_context()))
                        req = Request(u, headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)"})
                        with opener.open(req, timeout=25) as resp:
                            raw = resp.read()
                            url = u
                            return raw, u
                    except Exception as exc:  # noqa: BLE001
                        last = exc
                raise RuntimeError(str(last))

            raw, url = _fetch()
            payload, path = rbi._parse_rbi_payload(raw)
            series = list(payload.get("series") or [])
            return series, path, None if series else "rbi_html_no_metrics"
        except Exception as exc:  # noqa: BLE001
            return [], None, str(exc)[:160]
