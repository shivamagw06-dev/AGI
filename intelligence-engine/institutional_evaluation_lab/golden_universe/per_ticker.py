"""Per-ticker pipeline: pack → live price → freshness → decision engine → metrics."""

from __future__ import annotations

import time
from typing import Any, Callable

from institutional_evaluation_lab.golden_universe.failures import classify_failure
from institutional_evaluation_lab.golden_universe.metrics import extract_metrics
from institutional_evaluation_lab.golden_universe.qa_governance import run_qa_checks


def _ms_since(t0: float) -> int:
    return max(0, int((time.time() - t0) * 1000))


def _load_pack(ticker: str) -> tuple[bool, dict[str, Any]]:
    try:
        from knowledge_factory.store import repository as store

        pack = store.get_pack(ticker) or {}
        return bool(pack), pack if isinstance(pack, dict) else {}
    except Exception:
        return False, {}


def _fetch_price(ticker: str, *, force: bool = False) -> dict[str, Any]:
    try:
        from forecast_provider_integration.market_snapshot import ensure_fresh_market_snapshot

        return ensure_fresh_market_snapshot(ticker, scope="company", force=force)
    except Exception as exc:
        return {
            "refreshed": False,
            "reason": "price_fetch_failed",
            "snapshot": {},
            "error": str(exc)[:200],
        }


def _build_cid(ticker: str, *, query: str) -> dict[str, Any]:
    try:
        from cid.production import get_or_build

        return get_or_build(ticker, query=query) or {}
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)[:200], "enabled": False}


def _build_company_analysis(
    ticker: str,
    *,
    query: str,
    cid: dict[str, Any],
    leo_pkg: dict[str, Any] | None,
) -> dict[str, Any]:
    try:
        from company_analysis.production import package_for_ask_agi as ca_package

        return (
            ca_package(query, ticker=ticker, cid=cid, leo_pkg=leo_pkg)
            or ca_package(query, ticker=ticker, cid=cid)
            or {}
        )
    except TypeError:
        try:
            from company_analysis.production import package_for_ask_agi as ca_package

            return ca_package(query, ticker=ticker, cid=cid) or {}
        except Exception as exc:
            return {"ticker": ticker, "error": str(exc)[:200]}
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)[:200]}


def _run_decision_engine(
    ticker: str,
    *,
    query: str,
    cid: dict[str, Any],
    company_analysis: dict[str, Any],
    live_evidence: dict[str, Any],
) -> dict[str, Any]:
    from decision_engine.production import package_for_ask_agi as ide_package

    return ide_package(
        query,
        ticker=ticker,
        cid=cid if cid.get("enabled") is not False else None,
        company_analysis=company_analysis if isinstance(company_analysis, dict) else None,
        live_evidence=live_evidence,
        force=True,
    )


def evaluate_ticker(
    row: dict[str, Any],
    *,
    force_price_refresh: bool = False,
    query: str | None = None,
    ide_runner: Callable[..., dict[str, Any]] | None = None,
    price_runner: Callable[..., dict[str, Any]] | None = None,
    skip_cid_ca: bool = False,
) -> dict[str, Any]:
    """Execute the full institutional evaluation pipeline for one golden-universe name."""
    t_total = time.time()
    ticker = str(row.get("ticker") or "").upper()
    name = row.get("name") or row.get("company_name")
    sector = row.get("sector")
    bucket = row.get("bucket")
    q = query or f"Should I buy {name or ticker}?"
    errors: list[str] = []
    timing: dict[str, int] = {}

    t0 = time.time()
    pack_present, pack = _load_pack(ticker)
    timing["company_pack_ms"] = _ms_since(t0)

    t0 = time.time()
    price_fn = price_runner or (lambda t, force=False: _fetch_price(t, force=force))
    try:
        price_pkg = price_fn(ticker, force=force_price_refresh)
    except TypeError:
        price_pkg = price_fn(ticker)
    except Exception as exc:
        price_pkg = {"snapshot": {}, "error": str(exc)[:200]}
        errors.append(f"price:{exc}")
    timing["groww_price_ms"] = _ms_since(t0)

    snap = (price_pkg or {}).get("snapshot") if isinstance(price_pkg, dict) else {}
    live_evidence = {
        "ticker": ticker,
        "quote": {
            "price": (snap or {}).get("ltp"),
            "ltp": (snap or {}).get("ltp"),
            "as_of": (snap or {}).get("as_of"),
            "source": (snap or {}).get("source_provider") or "groww",
        },
        "generated_at": (snap or {}).get("as_of"),
        "market_snapshot": snap or {},
    }

    t0 = time.time()
    if skip_cid_ca:
        cid = {"ticker": ticker, "enabled": True, "replay_stub": True}
        ca = {"ticker": ticker, "replay_stub": True}
    else:
        cid = _build_cid(ticker, query=q)
        if cid.get("error"):
            errors.append(f"cid:{cid.get('error')}")
        ca = _build_company_analysis(ticker, query=q, cid=cid, leo_pkg=live_evidence)
        if ca.get("error"):
            errors.append(f"company_analysis:{ca.get('error')}")
    timing["company_intelligence_ms"] = _ms_since(t0)

    t0 = time.time()
    ide_fn = ide_runner or _run_decision_engine
    try:
        ide_pkg = ide_fn(
            ticker,
            query=q,
            cid=cid,
            company_analysis=ca,
            live_evidence=live_evidence,
        )
    except Exception as exc:
        ide_pkg = {"enabled": False, "error": str(exc)[:240]}
        errors.append(f"decision_engine:{exc}")
    timing["decision_engine_ms"] = _ms_since(t0)
    timing["total_ms"] = _ms_since(t_total)

    metrics = extract_metrics(
        ticker=ticker,
        company_name=name or ide_pkg.get("company_name"),
        sector=sector,
        bucket=bucket,
        ide_pkg=ide_pkg,
        price_pkg=price_pkg if isinstance(price_pkg, dict) else {},
        pack_present=pack_present,
        runtime_ms=timing["total_ms"],
        errors=errors,
    )
    metrics["timing"] = timing
    metrics["knowledge_snapshot"] = (
        ca.get("generated_at")
        or cid.get("updated_at")
        or cid.get("generated_at")
        or (pack.get("generated_at") if isinstance(pack, dict) else None)
    )
    metrics["market_snapshot"] = (snap or {}).get("as_of") or (price_pkg or {}).get("as_of")
    metrics["replay_inputs"] = {
        "query": q,
        "price_snapshot": snap or {},
        "force_price_refresh": bool(force_price_refresh),
    }

    qa = run_qa_checks(metrics)
    metrics["qa"] = qa
    metrics["qa_passed"] = qa.get("passed")
    metrics["pipeline"] = {
        "load_company_pack": pack_present,
        "fetch_live_price": bool((snap or {}).get("ltp") is not None),
        "freshness_validation": not bool((snap or {}).get("stale")) if snap else False,
        "decision_engine": bool(ide_pkg.get("active") or ide_pkg.get("enabled")),
        "evaluation_report": True,
    }

    failure = classify_failure(
        pack_present=pack_present,
        price_pkg=price_pkg if isinstance(price_pkg, dict) else {},
        cid=cid,
        company_analysis=ca,
        ide_pkg=ide_pkg,
        metrics=metrics,
        errors=errors,
    )
    if failure:
        metrics["status"] = failure["status"]
        metrics["failure"] = failure
        metrics["ok"] = False
    else:
        metrics["status"] = "COMPLETED"
        metrics["failure"] = None
        metrics["ok"] = True
    return metrics
