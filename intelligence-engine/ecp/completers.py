"""Soft completion adapters — fill validated gaps only (never overwrite)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ecp.schema import ECP_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _eid(*parts: str) -> str:
    raw = "|".join(str(p) for p in parts)
    return "ecp_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _evidence_object(
    *,
    evidence_type: str,
    ticker: str,
    source_id: str,
    title: str,
    facts: List[Dict[str, Any]],
    confidence: float = 0.72,
) -> Dict[str, Any]:
    value_text = "; ".join(
        f"{f.get('field')}={f.get('value_text') or f.get('value')}" for f in facts[:8]
    )[:800]
    return {
        "evidence_id": _eid(source_id, evidence_type, ticker, title[:40], value_text[:60]),
        "leo_version": "leo-v1.0.0",
        "ecp_version": ECP_VERSION,
        "evidence_type": evidence_type,
        "fact_key": (facts[0].get("field") if facts else evidence_type),
        "value_text": value_text or title,
        "value": facts[0].get("value") if facts else None,
        "entity": ticker,
        "company_symbol": ticker,
        "source_id": source_id,
        "source_name": source_id.upper(),
        "title": title,
        "url": "",
        "published": _now(),
        "extracted_facts": facts[:20],
        "confidence": confidence,
        "verification_status": "provisionally_verified",
        "rank_weight": 1.5,
        "provenance": {
            "source_id": source_id,
            "connector": "ecp",
            "fetched_at": _now(),
            "orchestrator": "ECP",
        },
        "metadata": {"completed_by": "ecp", "kind": "auto_completion"},
        "version": 1,
    }


def complete_market_and_valuation(
    ticker: str,
    *,
    client: Any | None = None,
) -> Dict[str, Any]:
    """
    Soft-complete market_data + valuation_metrics (+ financial statement snapshots)
    via MarketDataClient / YFP / DVC. Returns evidence objects + enrich packages.
    """
    from app.core.async_run import run_coro
    from app.core.config import get_settings
    from app.market_data.client import MarketDataClient

    t = (ticker or "").upper()
    md = client or MarketDataClient.from_settings(get_settings())
    providers_used: List[str] = []
    objects: List[Dict[str, Any]] = []
    ypack: Dict[str, Any] = {}
    dvc_pack: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    # 1) Yahoo secondary enrich (canonical)
    try:
        ypack = run_coro(md.yahoo_enrich(t))
        if ypack.get("enabled"):
            providers_used.append("yahoo")
    except Exception as exc:  # noqa: BLE001
        errors["yahoo"] = str(exc)[:200]
        ypack = {}

    # 2) DVC multi-provider validation
    try:
        dvc_pack = run_coro(md.validated_package(t, persist=True))
        if dvc_pack.get("enabled"):
            providers_used.append("dvc")
            wp = dvc_pack.get("winning_provider_summary")
            if wp and wp not in providers_used:
                providers_used.append(str(wp))
    except Exception as exc:  # noqa: BLE001
        errors["dvc"] = str(exc)[:200]
        dvc_pack = {}

    # 3) Direct MarketDataClient quote/fundamentals (first-success failover)
    quote = None
    fund = None
    try:
        quote = run_coro(md.get_quote(t))
        providers_used.append("market_data_client")
    except Exception as exc:  # noqa: BLE001
        errors["quote"] = str(exc)[:200]
    try:
        fund = run_coro(md.get_fundamentals(t))
        if "market_data_client" not in providers_used:
            providers_used.append("market_data_client")
    except Exception as exc:  # noqa: BLE001
        errors["fundamentals"] = str(exc)[:200]

    # Build market_data evidence from best available
    md_facts: List[Dict[str, Any]] = []
    vf = (dvc_pack.get("validated_fields") or {}) if isinstance(dvc_pack, dict) else {}
    yq = ypack.get("quote") if isinstance(ypack.get("quote"), dict) else {}
    ymetrics = {}
    if isinstance(ypack.get("fundamentals"), dict):
        ymetrics = ypack["fundamentals"].get("metrics") or {}

    def _pick(*candidates):
        for c in candidates:
            if c not in (None, ""):
                return c
        return None

    price = _pick(
        (vf.get("last") or {}).get("value") if isinstance(vf.get("last"), dict) else None,
        yq.get("last"),
        getattr(quote, "last", None),
    )
    if price is not None:
        md_facts.append({"field": "current_price", "value": price, "value_text": str(price), "confidence": 0.85})
    for field, sources in (
        ("volume", ((vf.get("volume") or {}).get("value"), yq.get("volume"), getattr(quote, "volume", None))),
        ("market_cap", ((vf.get("market_cap") or {}).get("value"), ymetrics.get("market_cap"))),
        ("enterprise_value", ((vf.get("enterprise_value") or {}).get("value"), ymetrics.get("enterprise_value"))),
        ("fifty_two_week_high", ((vf.get("fifty_two_week_high") or {}).get("value"), ymetrics.get("fifty_two_week_high"))),
        ("fifty_two_week_low", ((vf.get("fifty_two_week_low") or {}).get("value"), ymetrics.get("fifty_two_week_low"))),
        ("dividend_yield", ((vf.get("dividend_yield") or {}).get("value"), ymetrics.get("dividend_yield"))),
        ("shares_outstanding", ((vf.get("shares_outstanding") or {}).get("value"), ymetrics.get("shares_outstanding"))),
    ):
        val = _pick(*sources)
        if val is not None:
            md_facts.append({"field": field, "value": val, "value_text": str(val), "confidence": 0.8})

    if md_facts:
        src = "dvc" if vf else ("yahoo" if yq else "market_data_client")
        objects.append(
            _evidence_object(
                evidence_type="market_data",
                ticker=t,
                source_id=src,
                title=f"{t} market data (ECP)",
                facts=md_facts,
                confidence=0.82,
            )
        )

    # Valuation facts
    val_facts: List[Dict[str, Any]] = []
    for field in ("trailing_pe", "forward_pe", "price_to_book", "price_to_sales", "ev_ebitda", "peg", "beta"):
        val = _pick(
            (vf.get(field) or {}).get("value") if isinstance(vf.get(field), dict) else None,
            ymetrics.get(field),
            (fund.metrics.get(field) if fund is not None and hasattr(fund, "metrics") else None),
        )
        if val is not None:
            val_facts.append({"field": field, "value": val, "value_text": str(val), "confidence": 0.78})
    if val_facts:
        objects.append(
            _evidence_object(
                evidence_type="valuation_metrics",
                ticker=t,
                source_id="yahoo" if ymetrics else "dvc",
                title=f"{t} valuation metrics (ECP)",
                facts=val_facts,
                confidence=0.78,
            )
        )

    # Financial statement / metrics evidence from Yahoo JSON metrics
    fin_facts: List[Dict[str, Any]] = []
    for field in (
        "roe",
        "roa",
        "revenue",
        "revenue_growth",
        "operating_margin",
        "profit_margin",
        "free_cash_flow",
        "gross_margin",
        "ebitda",
    ):
        val = _pick(
            (vf.get(field) or {}).get("value") if isinstance(vf.get(field), dict) else None,
            ymetrics.get(field),
        )
        if val is not None:
            fin_facts.append({"field": field, "value": val, "value_text": str(val), "confidence": 0.75})
    has_stmt = any(
        ymetrics.get(k)
        for k in (
            "income_statement_annual_json",
            "balance_sheet_annual_json",
            "cashflow_annual_json",
            "income_statement_quarterly_json",
        )
    )
    if fin_facts or has_stmt:
        if has_stmt:
            fin_facts.append(
                {
                    "field": "statements_available",
                    "value": True,
                    "value_text": "income/balance/cashflow snapshots available",
                    "confidence": 0.7,
                }
            )
        objects.append(
            _evidence_object(
                evidence_type="financial_statements",
                ticker=t,
                source_id="yahoo",
                title=f"{t} financial statements / metrics (ECP)",
                facts=fin_facts or [{"field": "statements", "value_text": "present", "confidence": 0.7}],
                confidence=0.74,
            )
        )

    # Soft sector KPI placeholders from available metrics (never invent)
    kpi_facts: List[Dict[str, Any]] = []
    for field in ("roe", "roa", "operating_margin", "revenue_growth", "gross_margin"):
        val = _pick(
            (vf.get(field) or {}).get("value") if isinstance(vf.get(field), dict) else None,
            ymetrics.get(field),
        )
        if val is not None:
            kpi_facts.append({"field": field, "value": val, "value_text": str(val), "confidence": 0.7})
    if kpi_facts:
        objects.append(
            _evidence_object(
                evidence_type="sector_kpis",
                ticker=t,
                source_id="ecp_derived",
                title=f"{t} sector-relevant metrics (ECP derived)",
                facts=kpi_facts,
                confidence=0.68,
            )
        )

    return {
        "ticker": t,
        "providers_used": list(dict.fromkeys(providers_used)),
        "evidence_objects": objects,
        "yahoo_pack": ypack if ypack.get("enabled") else {},
        "dvc_pack": dvc_pack if dvc_pack.get("enabled") else {},
        "errors": errors,
        "completed_types": sorted({o["evidence_type"] for o in objects}),
        "ecp_version": ECP_VERSION,
    }


def complete_from_kip_kf(
    ticker: str,
    query: str,
    *,
    kip: Any | None = None,
    kf: Any | None = None,
) -> Dict[str, Any]:
    """Soft pull company knowledge from KIP / Knowledge Foundation (fill gaps only)."""
    objects: List[Dict[str, Any]] = []
    providers: List[str] = []
    knowledge: Dict[str, Any] = {}
    t = (ticker or "").upper()

    if kip is not None:
        try:
            # Soft retrieve — platforms vary; tolerate shapes
            result = None
            for meth in ("retrieve", "search", "company"):
                fn = getattr(kip, meth, None)
                if callable(fn):
                    try:
                        result = fn(query or t) if meth != "company" else fn(t)
                        break
                    except TypeError:
                        try:
                            result = fn(q=query or t)
                            break
                        except Exception:
                            continue
                    except Exception:
                        continue
            if result:
                providers.append("kip")
                if hasattr(result, "model_dump"):
                    knowledge["kip"] = result.model_dump(mode="json")
                elif isinstance(result, dict):
                    knowledge["kip"] = result
                facts = []
                hits = []
                if isinstance(knowledge.get("kip"), dict):
                    hits = knowledge["kip"].get("hits") or knowledge["kip"].get("documents") or []
                for h in (hits or [])[:5]:
                    if isinstance(h, dict):
                        facts.append(
                            {
                                "field": h.get("title") or h.get("fact_key") or "knowledge",
                                "value_text": str(h.get("summary") or h.get("text") or h.get("value") or "")[:400],
                                "confidence": float(h.get("confidence") or 0.6),
                            }
                        )
                if facts:
                    objects.append(
                        _evidence_object(
                            evidence_type="peer_comparison",
                            ticker=t,
                            source_id="kip",
                            title=f"{t} KIP knowledge (ECP)",
                            facts=facts,
                            confidence=0.62,
                        )
                    )
        except Exception:
            pass

    if kf is not None:
        try:
            result = None
            for meth in ("search", "get_company", "company"):
                fn = getattr(kf, meth, None)
                if callable(fn):
                    try:
                        result = fn(query or t, limit=6) if meth == "search" else fn(t)
                        break
                    except TypeError:
                        try:
                            result = fn(t)
                            break
                        except Exception:
                            continue
                    except Exception:
                        continue
            if result:
                providers.append("knowledge_foundation")
                dump = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
                if isinstance(dump, dict):
                    knowledge["kf"] = dump
                    hits = dump.get("hits") or []
                    facts = []
                    for h in hits[:5]:
                        if isinstance(h, dict):
                            facts.append(
                                {
                                    "field": h.get("kind") or "kf",
                                    "value_text": str(h.get("title") or h.get("key") or "")[:300],
                                    "confidence": 0.65,
                                }
                            )
                    if facts:
                        objects.append(
                            _evidence_object(
                                evidence_type="macro",
                                ticker=t,
                                source_id="kf",
                                title=f"{t} KF context (ECP)",
                                facts=facts,
                                confidence=0.64,
                            )
                        )
        except Exception:
            pass

    return {
        "providers_used": providers,
        "evidence_objects": objects,
        "knowledge": knowledge,
        "completed_types": sorted({o["evidence_type"] for o in objects}),
        "ecp_version": ECP_VERSION,
    }
