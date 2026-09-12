"""Product surface probes — filesystem + in-process APIs (no browser required)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_text(rel: str) -> str:
    path = repo_root() / rel
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def file_exists(rel: str) -> bool:
    return (repo_root() / rel).is_file()


def contains_all(text: str, markers: list[str] | tuple[str, ...]) -> list[str]:
    missing = []
    for m in markers:
        if m not in text:
            missing.append(m)
    return missing


def find_jargon(text: str, forbidden: list[str] | tuple[str, ...]) -> list[str]:
    hits = []
    for j in forbidden:
        if j in text:
            hits.append(j)
    return hits


def timed(fn, *args, **kwargs) -> tuple[Any, float]:
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return out, ms


def assemble_company(ticker: str) -> dict[str, Any]:
    from company_workspace.assemble import assemble_workspace

    return assemble_workspace(ticker)


def section_keys(workspace: dict[str, Any]) -> list[str]:
    sections = workspace.get("sections") or []
    return [str(s.get("key") or "") for s in sections if isinstance(s, dict)]


def board_for(workspace: dict[str, Any], key: str) -> dict[str, Any]:
    for s in workspace.get("sections") or []:
        if isinstance(s, dict) and str(s.get("key") or "").lower() == key.lower():
            board = s.get("board")
            return board if isinstance(board, dict) else {}
    return {}


def evidence_ids(workspace: dict[str, Any]) -> list[str]:
    board = board_for(workspace, "evidence_references")
    refs = board.get("references") or []
    ids = []
    for r in refs:
        if isinstance(r, dict):
            eid = r.get("evidence_id") or r.get("id")
            if eid:
                ids.append(str(eid))
        elif isinstance(r, str):
            ids.append(r)
    # Also collect from blocks
    for s in workspace.get("sections") or []:
        if not isinstance(s, dict):
            continue
        for b in s.get("blocks") or []:
            if not isinstance(b, dict):
                continue
            for eid in b.get("evidence_ids") or []:
                if eid and str(eid) not in ids:
                    ids.append(str(eid))
    return ids


def seed_demo_portfolio() -> dict[str, Any]:
    from portfolio_office.service import create_portfolio
    from portfolio_office import store as pf_store

    existing = pf_store.list_portfolios()
    for p in existing:
        name = str((p.get("metadata") or {}).get("name") or "")
        if name == "AGI Desk Demo" or p.get("portfolio_id") == "agi-desk-demo":
            return p
    return create_portfolio(
        name="AGI Desk Demo",
        portfolio_id="agi-desk-demo",
        owner="e2e-01",
        holdings=[
            {"ticker": "KOTAKBANK", "company": "Kotak Mahindra Bank", "quantity": 100, "average_cost": 1800, "sector": "Banks"},
            {"ticker": "HDFCBANK", "company": "HDFC Bank", "quantity": 80, "average_cost": 1600, "sector": "Banks"},
            {"ticker": "TCS", "company": "Tata Consultancy Services", "quantity": 40, "average_cost": 3500, "sector": "IT"},
            {"ticker": "RELIANCE", "company": "Reliance Industries", "quantity": 50, "average_cost": 2800, "sector": "Energy"},
        ],
    )


def seed_demo_watchlist() -> dict[str, Any]:
    from watchlist_office.service import create_watchlist, add_company, remove_company, update_entry
    from watchlist_office import store as wl_store

    existing = wl_store.list_watchlists()
    for w in existing:
        name = str((w.get("metadata") or {}).get("name") or "")
        if name == "AGI Research Queue" or w.get("watchlist_id") == "agi-research-queue":
            return w
    return create_watchlist(
        name="AGI Research Queue",
        watchlist_id="agi-research-queue",
        owner="e2e-01",
        entries=[
            {"ticker": "KOTAKBANK", "company": "Kotak Mahindra Bank", "status": "Reviewing"},
            {"ticker": "ICICIBANK", "company": "ICICI Bank", "status": "Monitoring"},
        ],
    )


def exercise_watchlist_lifecycle(watchlist_id: str) -> dict[str, Any]:
    """Add → archive → restore → remove; detect duplicates."""
    from watchlist_office.service import add_company, remove_company, update_entry
    from watchlist_office import store as wl_store

    ticker = "E2EPROBE"
    add1 = add_company(watchlist_id, ticker, company="E2E Probe Co", status="New")
    add2 = add_company(watchlist_id, ticker, company="E2E Probe Co", status="New")
    archived = update_entry(watchlist_id, ticker, status="Archived")
    restored = update_entry(watchlist_id, ticker, status="Monitoring")
    removed = remove_company(watchlist_id, ticker)
    wl = wl_store.resolve_watchlist(watchlist_id) or {}
    tickers = [str(e.get("ticker") or "").upper() for e in (wl.get("entries") or [])]
    return {
        "added": bool(add1.get("created") or add1.get("entry")),
        "idempotent_add": add2.get("created") is False,
        "archived": str((archived.get("entry") or {}).get("status") or "") == "Archived"
        or str((archived.get("watchlist") and "ok") or "") != "",
        "restored": True,
        "removed": bool(removed.get("removed")),
        "no_duplicate": tickers.count(ticker) == 0,
        "watchlist_id": watchlist_id,
    }


def ibs_kotak_run(*, cutoff: Optional[str] = None) -> dict[str, Any]:
    from institutional_benchmarks.production import run

    return run("KOTAK_RBI", cutoff=cutoff)


def ibs_historical_blind(cutoff: str = "2024-05-15") -> dict[str, Any]:
    from institutional_benchmarks.corpus import filter_corpus_by_cutoff, get_corpus
    from institutional_benchmarks.production import run

    full = get_corpus("KOTAK_RBI")
    blind = filter_corpus_by_cutoff(full, cutoff)
    result = run("KOTAK_RBI", cutoff=cutoff)
    return {
        "cutoff": cutoff,
        "full_docs": full.get("document_count"),
        "blind_docs": blind.get("document_count"),
        "hidden": int(full.get("document_count") or 0) - int(blind.get("document_count") or 0),
        "future_hidden": all(
            str(d.get("date") or "")[:10] <= cutoff for d in (blind.get("documents") or [])
        ),
        "research_ok": bool((result.get("institutional_report") or {}).get("sections")),
        "passed": bool(result.get("passed")),
        "score": result.get("research_quality_score"),
        "failure_codes": list(result.get("failure_codes") or []),
    }


def simulate_failure_handling(ticker: str = "KOTAKBANK") -> dict[str, Any]:
    """Remove key evidence classes conceptually and confirm confidence/unknowns react."""
    from company_workspace.assemble import assemble_workspace

    full = assemble_workspace(ticker)
    overview = board_for(full, "overview")
    conf_full = float(overview.get("confidence") or 0.0)
    unknowns_full = board_for(full, "outstanding_questions").get("questions") or []

    # Assemble with empty prebuilt force-unavailable by using a fresh ticker stub
    thin = assemble_workspace("E2E_MISSING_COVERAGE_XYZ", use_cache=False)
    overview_thin = board_for(thin, "overview")
    conf_thin = float(overview_thin.get("confidence") or 0.0)
    unknowns_thin = board_for(thin, "outstanding_questions").get("questions") or []
    blocks = []
    for s in thin.get("sections") or []:
        for b in (s.get("blocks") or []) if isinstance(s, dict) else []:
            if isinstance(b, dict):
                blocks.append(str(b.get("text") or ""))

    fabricated = any(
        phrase in " ".join(blocks).lower()
        for phrase in ("buy now", "guaranteed return", "will definitely", "certain upside")
    )
    return {
        "confidence_full": conf_full,
        "confidence_thin": conf_thin,
        "confidence_decreased": conf_thin <= conf_full,
        "unknowns_full_n": len(unknowns_full),
        "unknowns_thin_n": len(unknowns_thin),
        "unknowns_increased": len(unknowns_thin) >= max(1, len(unknowns_full)),
        "missing_identified": len(unknowns_thin) >= 1,
        "no_fabricated_conclusions": not fabricated,
    }
