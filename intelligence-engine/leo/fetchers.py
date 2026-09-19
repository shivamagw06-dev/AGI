"""Fetch live / soft evidence from selected sources. Never reason on raw payloads here."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.resilience.circuit_breaker import get_provider_circuits


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 2)


def _fetch_one_source(
    src: dict[str, Any],
    ticker: str | None,
    *,
    eve: Any | None,
    kip: Any | None,
    aoi: Any | None,
    mee: Any | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch a single source; returns (items, call_log_row)."""
    sid = src["source_id"]
    circuits = get_provider_circuits()
    t0 = time.perf_counter()
    if not circuits.allow(f"leo:{sid}"):
        return [], {
            "source_id": sid,
            "status": "circuit_open",
            "latency_ms": _ms(t0),
            "items": 0,
            "via": src.get("via"),
            "called": False,
        }
    try:
        if sid in {"nse", "bse", "company_ir", "rbi"}:
            items = _fetch_aoi(sid, ticker, aoi=aoi)
            status = "ok" if items else "empty"
        elif sid in {"indianapi", "finnhub", "fmp", "yahoo"}:
            items = _fetch_market_data(sid, ticker)
            status = "ok" if items else "empty_or_unconfigured"
        elif sid in {"groww", "twelve_data", "fred", "alphavantage", "newsapi"}:
            items = _fetch_agib(sid, ticker)
            status = "ok" if items else "empty_or_unreachable"
        elif sid == "internal_research":
            items = _fetch_internal(ticker, eve=eve, kip=kip, mee=mee)
            status = "ok" if items else "empty"
        else:
            items = []
            status = "skipped"
        latency = _ms(t0)
        if status == "ok":
            circuits.success(f"leo:{sid}")
        elif status in {"empty_or_unconfigured", "empty_or_unreachable"}:
            circuits.failure(f"leo:{sid}", error=status)
        row = {
            "source_id": sid,
            "status": status,
            "latency_ms": latency,
            "items": len(items),
            "via": src.get("via"),
            "called": status
            in {"ok", "empty", "empty_or_unconfigured", "empty_or_unreachable"},
            "parallel": True,
        }
        return items, row
    except Exception as exc:  # noqa: BLE001
        circuits.failure(f"leo:{sid}", error=str(exc)[:200])
        return [], {
            "source_id": sid,
            "status": "error",
            "latency_ms": _ms(t0),
            "error": str(exc)[:240],
            "items": 0,
            "called": True,
            "parallel": True,
        }


def fetch_for_plan(
    plan: dict[str, Any],
    sources: list[dict[str, Any]],
    *,
    eve: Any | None = None,
    kip: Any | None = None,
    aoi: Any | None = None,
    mee: Any | None = None,
) -> dict[str, Any]:
    """Execute source fetches in parallel; return raw bundles + call log."""
    ticker = (plan.get("ticker") or "").upper() or None
    call_log: list[dict[str, Any]] = []
    bundles: list[dict[str, Any]] = []

    if not sources:
        return {"bundles": bundles, "api_calls": call_log, "ticker": ticker, "parallel": True}

    workers = min(6, max(1, len(sources)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="leo-src") as pool:
        futures = [
            pool.submit(
                _fetch_one_source,
                src,
                ticker,
                eve=eve,
                kip=kip,
                aoi=aoi,
                mee=mee,
            )
            for src in sources
        ]
        for fut in as_completed(futures):
            try:
                items, row = fut.result()
            except Exception as exc:  # noqa: BLE001
                call_log.append(
                    {
                        "source_id": "unknown",
                        "status": "error",
                        "latency_ms": 0,
                        "error": str(exc)[:240],
                        "items": 0,
                        "called": True,
                        "parallel": True,
                    }
                )
                continue
            call_log.append(row)
            latency = float(row.get("latency_ms") or 0)
            sid = row.get("source_id")
            for it in items:
                bundles.append({**it, "source_id": sid, "fetch_latency_ms": latency})

    # Stable order for downstream determinism
    call_log.sort(key=lambda r: str(r.get("source_id") or ""))
    return {
        "bundles": bundles,
        "api_calls": call_log,
        "ticker": ticker,
        "parallel": True,
        "workers": workers,
    }


def _fetch_aoi(source_id: str, ticker: str | None, *, aoi: Any | None = None) -> list[dict[str, Any]]:
    """Use AOI connectors (NSE/BSE/Company IR/RBI) — soft structured corporate evidence."""
    out: list[dict[str, Any]] = []
    try:
        from app.aoi.registry import CompanyRegistry

        if source_id == "nse":
            from app.aoi.connectors.exchanges import NseConnector

            conn = NseConnector(config={"streams": [
                "announcements", "corporate_actions", "board_meetings",
                "financial_filings", "shareholding",
            ], "base_url": "https://www.nseindia.com"})
        elif source_id == "bse":
            from app.aoi.connectors.exchanges import BseConnector

            conn = BseConnector(config={"streams": ["announcements", "corporate_actions"], "base_url": "https://www.bseindia.com"})
        elif source_id == "company_ir":
            from app.aoi.connectors.company_ir import CompanyIrConnector

            conn = CompanyIrConnector(config={})
        elif source_id == "rbi":
            from app.aoi.connectors.macro_gov import RbiConnector

            conn = RbiConnector(
                config={
                    "streams": ["repo_rate", "inflation", "liquidity", "money_supply", "gdp"],
                    "base_url": "https://www.rbi.org.in",
                }
            )
        else:
            return []

        registry = None
        if aoi is not None and hasattr(aoi, "registry"):
            registry = aoi.registry
        if registry is None:
            registry = CompanyRegistry()
            registry.seed_default_universes()

        arts = conn.discover(registry)
        # Filter to ticker when known (skip filter for pure macro streams)
        if ticker and source_id != "rbi":
            filtered = [
                a for a in arts
                if (getattr(a, "metadata", None) or {}).get("nse_symbol", "").upper() == ticker
                or ticker.lower() in (getattr(a, "company_id", "") or "").lower()
                or ticker.lower() in (getattr(a, "title", "") or "").lower()
            ]
            arts = (filtered or arts)[:12]
        else:
            arts = arts[:8]

        for art in arts:
            try:
                art = conn.download(art)
                art = conn.parse(art)
                facts = conn.extract(art)
            except Exception:
                facts = []
            dtype = getattr(art, "doc_type", "") or "corporate_announcement"
            etype = _map_doc_type(dtype, source_id)
            out.append(
                {
                    "kind": "document",
                    "evidence_type": etype,
                    "title": getattr(art, "title", "") or etype,
                    "url": getattr(art, "url", ""),
                    "published": getattr(art, "discovered_at", None),
                    "company_id": getattr(art, "company_id", None),
                    "facts": [
                        {
                            "field": getattr(f, "field", "") or getattr(f, "fact_key", "fact"),
                            "value_text": getattr(f, "value_text", "") or str(getattr(f, "value", "")),
                            "confidence": float(getattr(f, "confidence", 0.7) or 0.7),
                        }
                        for f in (facts or [])[:12]
                    ],
                    "artifact": art,
                    "raw": {
                        "doc_type": dtype,
                        "connector": source_id,
                        "content_preview": (getattr(art, "content_text", "") or "")[:400],
                    },
                }
            )
    except Exception:
        return out
    return out


def _map_doc_type(dtype: str, source_id: str) -> str:
    d = (dtype or "").lower()
    if "annual" in d:
        return "annual_report"
    if "quarter" in d or "result" in d or "financial_filing" in d:
        return "quarterly_results"
    if "presentation" in d or "investor" in d:
        return "investor_presentation"
    if "transcript" in d or "earnings" in d:
        return "earnings_transcript"
    if "esg" in d:
        return "esg_report"
    if source_id == "rbi":
        return "macro"
    if d in {"announcements", "corporate_actions", "board_meetings", "shareholding", "press_release"}:
        return "corporate_announcement"
    return "corporate_announcement"


def _fetch_market_data(source_id: str, ticker: str | None) -> list[dict[str, Any]]:
    if not ticker:
        return []
    try:
        from app.core.config import get_settings
        from app.market_data.client import MarketDataClient
        import asyncio

        settings = get_settings()
        client = MarketDataClient.from_settings(settings)
        if not client.registry.list_providers():
            return []

        async def _run():
            items = []
            # Prefer provider-specific secondary path for Yahoo; failover for others
            if source_id == "yahoo":
                yahoo = client.yahoo_provider()
                if yahoo is None or not yahoo.is_configured():
                    return []
                try:
                    quote = await yahoo.get_quote(ticker)
                except Exception:
                    quote = None
                try:
                    fund = await yahoo.get_fundamentals(ticker)
                except Exception:
                    fund = None
                try:
                    actions = await yahoo.get_corporate_actions(ticker)
                except Exception:
                    actions = []
            else:
                try:
                    quote = await client.get_quote(ticker)
                except Exception:
                    quote = None
                try:
                    fund = await client.get_fundamentals(ticker)
                except Exception:
                    fund = None
                try:
                    actions = await client.get_corporate_actions(ticker)
                except Exception:
                    actions = []

            if quote is not None:
                items.append(
                    {
                        "kind": "market_data",
                        "evidence_type": "market_data",
                        "title": f"{ticker} quote via {source_id}",
                        "facts": [
                            {
                                "field": "last_price",
                                "value_text": str(
                                    getattr(quote, "last", None) or getattr(quote, "price", None) or quote
                                ),
                            },
                            {"field": "symbol", "value_text": ticker},
                            {"field": "volume", "value_text": str(getattr(quote, "volume", None))},
                        ],
                        "raw": quote.model_dump(mode="json") if hasattr(quote, "model_dump") else {"quote": str(quote)[:500]},
                        "provider_requested": source_id,
                    }
                )
            if fund is not None:
                metrics = getattr(fund, "metrics", None) or {}
                if not isinstance(metrics, dict) and hasattr(fund, "model_dump"):
                    metrics = (fund.model_dump(mode="json") or {}).get("metrics") or {}
                items.append(
                    {
                        "kind": "fundamentals",
                        "evidence_type": "financial_statements",
                        "title": f"{ticker} fundamentals via {source_id}",
                        "facts": [
                            {"field": k, "value_text": str(v)[:300]}
                            for k, v in list(metrics.items())[:24]
                            if v is not None and not str(k).endswith("_json")
                        ],
                        "raw": {"metrics_keys": list(metrics.keys())[:40], "provider": source_id},
                        "provider_requested": source_id,
                    }
                )
                items.append(
                    {
                        "kind": "valuation",
                        "evidence_type": "valuation_metrics",
                        "title": f"{ticker} valuation metrics via {source_id}",
                        "facts": [
                            {"field": k, "value_text": str(v)}
                            for k, v in list(metrics.items())
                            if any(x in str(k).lower() for x in ("pe", "pb", "ev", "roe", "yield", "market", "book"))
                            and v is not None
                        ][:12],
                        "raw": {"from": "fundamentals", "provider": source_id},
                        "provider_requested": source_id,
                    }
                )
            for a in (actions or [])[:6]:
                items.append(
                    {
                        "kind": "corporate_action",
                        "evidence_type": "corporate_announcement",
                        "title": f"{ticker} corporate action via {source_id}",
                        "facts": [
                            {
                                "field": "action",
                                "value_text": str(
                                    getattr(a, "action_type", None) or a
                                )[:300],
                            }
                        ],
                        "raw": a.model_dump(mode="json") if hasattr(a, "model_dump") else {"action": str(a)[:300]},
                        "provider_requested": source_id,
                    }
                )
            return items

        try:
            return asyncio.run(_run())
        except RuntimeError:
            # Nested event loop — skip live market data rather than deadlock
            return []
    except Exception:
        return []


def _fetch_agib(source_id: str, ticker: str | None) -> list[dict[str, Any]]:
    """Call Node cached endpoints via AgibClient (sync wrapper)."""
    try:
        import asyncio
        from app.tools.agib_client import AgibClient

        client = AgibClient()
        path_map = {
            "groww": f"/api/market/ticker?symbol={ticker}" if ticker else "/api/market/dashboard",
            "twelve_data": "/api/market/pre-market-briefing",
            "fred": "/api/market/macro-briefing",
            "alphavantage": "/api/market/macro-briefing",
            "newsapi": "/api/news/headlines",
        }
        path = path_map.get(source_id)
        if not path:
            return []

        async def _run():
            data = await client.get_json(path)
            return data

        try:
            data = asyncio.run(_run())
        except RuntimeError:
            data = None

        if not data:
            return []

        etype = "macro" if source_id in {"fred", "alphavantage"} else ("news" if source_id == "newsapi" else "market_data")
        facts = []
        if isinstance(data, dict):
            for k in ("lastPrice", "ltp", "price", "repo_rate", "cpi", "gdp", "summary", "headline"):
                if data.get(k) is not None:
                    facts.append({"field": k, "value_text": str(data.get(k))[:300]})
            # nested common shapes
            for nest in ("quote", "ticker", "macro", "indices"):
                node = data.get(nest)
                if isinstance(node, dict):
                    for k, v in list(node.items())[:8]:
                        facts.append({"field": f"{nest}.{k}", "value_text": str(v)[:200]})
        if not facts:
            facts = [{"field": "payload", "value_text": str(data)[:400]}]
        return [
            {
                "kind": "agib",
                "evidence_type": etype,
                "title": f"{source_id} via AGIB Node",
                "facts": facts[:16],
                "raw": data if isinstance(data, dict) else {"data": str(data)[:500]},
                "url": path,
            }
        ]
    except Exception:
        return []


def _fetch_internal(
    ticker: str | None,
    *,
    eve: Any | None = None,
    kip: Any | None = None,
    mee: Any | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    q = ticker or ""
    if eve is not None and q:
        try:
            pack = eve.consult(q, limit=8) if hasattr(eve, "consult") else None
            if isinstance(pack, dict):
                hits = pack.get("hits") or []
                if hits:
                    out.append(
                        {
                            "kind": "eve",
                            "evidence_type": "sector_kpis",
                            "title": f"EVE verified evidence for {q}",
                            "facts": [
                                {
                                    "field": h.get("fact_key") or h.get("label") or "evidence",
                                    "value_text": str(h.get("snippet") or h.get("value_text") or h)[:300],
                                    "confidence": float(h.get("confidence") or 0.7),
                                }
                                for h in hits[:10]
                                if isinstance(h, dict)
                            ],
                            "raw": {"hits": len(hits)},
                        }
                    )
        except Exception:
            pass
    if mee is not None and q:
        try:
            pack = mee.consult(q, limit=6) if hasattr(mee, "consult") else None
            if isinstance(pack, dict) and (pack.get("hits") or pack.get("recent_events")):
                events = pack.get("recent_events") or pack.get("hits") or []
                out.append(
                    {
                        "kind": "mee",
                        "evidence_type": "corporate_announcement",
                        "title": f"Market events for {q}",
                        "facts": [
                            {"field": "event", "value_text": str(e)[:300]}
                            for e in events[:8]
                        ],
                        "raw": {"count": len(events)},
                    }
                )
        except Exception:
            pass
    if kip is not None and q:
        try:
            if hasattr(kip, "company_dossier"):
                dossier = kip.company_dossier(q)
                d = dossier.model_dump(mode="json") if hasattr(dossier, "model_dump") else (dossier if isinstance(dossier, dict) else {})
                if d:
                    out.append(
                        {
                            "kind": "kip",
                            "evidence_type": "peer_comparison",
                            "title": f"KIP company dossier {q}",
                            "facts": [
                                {"field": "house_view", "value_text": str(d.get("house_view") or "")[:300]},
                            ],
                            "raw": {"keys": list(d.keys())[:20]},
                        }
                    )
        except Exception:
            pass
    # Always contribute sector KPI scaffold when ticker known (SIF) so plan can mark sector_kpis
    if ticker:
        try:
            from sif.detection import detect_sector
            from sif.frameworks import get_framework

            det = detect_sector(ticker, ticker)
            fw = get_framework(det.get("sector_id"))
            if fw:
                out.append(
                    {
                        "kind": "sif_kpis",
                        "evidence_type": "sector_kpis",
                        "title": f"Sector KPI checklist — {fw.name}",
                        "facts": [
                            {"field": m, "value_text": f"Required sector KPI: {m}"}
                            for m in (fw.priority_metrics or [])[:10]
                        ],
                        "raw": {"sector_id": fw.sector_id, "framework_version": fw.version},
                    }
                )
        except Exception:
            pass
    return out
