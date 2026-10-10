"""Live endpoint reachability probes — production truth, not code existence."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.request import HTTPSHandler, build_opener

from live_data.collectors.nse_bhavcopy import bhavcopy_urls, _candidate_dates
from live_data.verification.schema import COLLECTOR_SPECS

NSE_ANNOUNCEMENT_URLS = (
    "https://www.nseindia.com/api/corporate-announcements?index=equities",
    "https://www.nseindia.com/",
)
BSE_URLS = (
    "https://www.bseindia.com/",
    "https://www.bseindia.com/corporates/corporate_act.aspx",
)
RBI_URLS = (
    "https://www.rbi.org.in/",
    "https://dbie.rbi.org.in/DBIE/#/dbie/home",
)
IR_URLS = {
    "INFY": "https://www.infosys.com/investors.html",
}


def _http_probe(url: str, *, timeout: int = 12, accept: str = "*/*") -> dict[str, Any]:
    t0 = time.time()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI-T2/1.0)",
        "Accept": accept,
        "Referer": "https://www.nseindia.com/" if "nse" in url else url,
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(256_000)
            return {
                "ok": 200 <= getattr(resp, "status", 200) < 400,
                "status_code": getattr(resp, "status", 200),
                "url": url,
                "bytes": len(body),
                "latency_ms": int((time.time() - t0) * 1000),
                "content_type": resp.headers.get("Content-Type"),
                "error": None,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status_code": None,
            "url": url,
            "bytes": 0,
            "latency_ms": int((time.time() - t0) * 1000),
            "error": str(exc)[:240],
        }


def _rbi_probe(url: str, *, timeout: int = 12) -> dict[str, Any]:
    t0 = time.time()
    last_err = None
    for ctx in (ssl.create_default_context(), ssl._create_unverified_context()):  # noqa: S323
        try:
            opener = build_opener(HTTPSHandler(context=ctx))
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI-T2/1.0)"}
            )
            with opener.open(req, timeout=timeout) as resp:
                body = resp.read(128_000)
                return {
                    "ok": True,
                    "status_code": getattr(resp, "status", 200),
                    "url": url,
                    "bytes": len(body),
                    "latency_ms": int((time.time() - t0) * 1000),
                    "tls_unverified": ctx.check_hostname is False,
                    "error": None,
                }
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    return {
        "ok": False,
        "status_code": None,
        "url": url,
        "bytes": 0,
        "latency_ms": int((time.time() - t0) * 1000),
        "error": str(last_err)[:240] if last_err else "rbi_probe_failed",
    }


def probe_endpoints() -> dict[str, Any]:
    """Probe official endpoints for each Track-1 collector."""
    results: dict[str, Any] = {}

    # NSE Bhavcopy — try most recent weekday archive URL
    bhav_attempts = []
    bhav_ok = None
    for d in _candidate_dates(lookback=3):
        for url in bhavcopy_urls(d)[:2]:
            p = _http_probe(url, timeout=10)
            bhav_attempts.append(p)
            if p["ok"] and p["bytes"] > 100:
                bhav_ok = p
                break
        if bhav_ok:
            break
    # Also probe NSE homepage for reachability signal
    nse_home = _http_probe("https://www.nseindia.com/", timeout=10)
    results["nse_bhavcopy"] = {
        "source_id": "nse_bhavcopy",
        "reachable": bool(bhav_ok) or bool(nse_home.get("ok")),
        "download_ok": bool(bhav_ok),
        "best": bhav_ok or nse_home,
        "attempts": bhav_attempts[:6],
        "homepage": nse_home,
        "auth_required": False,
        "note": "Archive download often 403 without browser session cookies",
    }

    ann_attempts = [_http_probe(u, timeout=10, accept="application/json,*/*") for u in NSE_ANNOUNCEMENT_URLS]
    ann_best = next((a for a in ann_attempts if a["ok"]), ann_attempts[0])
    results["nse_announcements"] = {
        "source_id": "nse_announcements",
        "reachable": any(a.get("ok") for a in ann_attempts),
        "download_ok": bool(ann_best.get("ok") and (ann_best.get("bytes") or 0) > 50),
        "best": ann_best,
        "attempts": ann_attempts,
        "auth_required": True,
        "note": "API often requires NSE session cookies",
    }

    bse_attempts = [_http_probe(u, timeout=10) for u in BSE_URLS]
    bse_best = next((a for a in bse_attempts if a["ok"]), bse_attempts[0])
    results["bse_corporate_actions"] = {
        "source_id": "bse_corporate_actions",
        "reachable": any(a.get("ok") for a in bse_attempts),
        "download_ok": bool(bse_best.get("ok")),
        "structured_export": False,  # HTML landing ≠ tabular CA export
        "best": bse_best,
        "attempts": bse_attempts,
        "auth_required": False,
        "note": "Homepage reachable; structured corporate-actions CSV export still adapter-limited",
    }

    rbi_attempts = [_rbi_probe(u, timeout=12) for u in RBI_URLS]
    rbi_best = next((a for a in rbi_attempts if a["ok"]), rbi_attempts[0])
    results["rbi_dbie"] = {
        "source_id": "rbi_dbie",
        "reachable": any(a.get("ok") for a in rbi_attempts),
        "download_ok": bool(rbi_best.get("ok")),
        "structured_series": False,
        "best": rbi_best,
        "attempts": rbi_attempts,
        "auth_required": False,
        "note": "DBIE TLS/hostname often brittle; structured JSON series export not published at home URL",
    }

    ir_url = IR_URLS["INFY"]
    ir = _http_probe(ir_url, timeout=12, accept="text/html,*/*")
    results["company_ir"] = {
        "source_id": "company_ir",
        "reachable": bool(ir.get("ok")),
        "download_ok": bool(ir.get("ok")),
        "structured_filings": "UNKNOWN",
        "best": ir,
        "attempts": [ir],
        "auth_required": False,
        "ticker": "INFY",
        "note": "IR HTML reachable; structured filing list needs site-specific adapters",
    }

    return {
        "probed_at": __import__("live_data.store", fromlist=["utc_now"]).utc_now(),
        "collectors": results,
        "specs": list(COLLECTOR_SPECS),
        "fabricated": False,
    }


def summarize_probes(probe_report: dict[str, Any]) -> dict[str, Any]:
    cols = probe_report.get("collectors") or {}
    return {
        "reachable": sum(1 for c in cols.values() if c.get("reachable")),
        "download_ok": sum(1 for c in cols.values() if c.get("download_ok")),
        "total": len(cols),
        "by_source": {
            sid: {
                "reachable": c.get("reachable"),
                "download_ok": c.get("download_ok"),
                "error": (c.get("best") or {}).get("error"),
                "latency_ms": (c.get("best") or {}).get("latency_ms"),
            }
            for sid, c in cols.items()
        },
    }
