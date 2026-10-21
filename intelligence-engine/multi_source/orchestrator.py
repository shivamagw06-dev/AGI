"""Retrieval orchestrator — route → parallel adapters → evidence fusion."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from multi_source.intent_router import route_sources
from multi_source.nifty_research import NiftyResearchSource
from multi_source.private_markets import PrivateMarketsSource
from multi_source.protocol import EvidenceItem
from multi_source.valuation_cms import ValuationCmsSource

# Conflict preference (higher wins when summaries disagree)
SOURCE_PRIORITY = {
    "nifty_research": 80,
    "valuation_monitor": 70,
    "transactions_cms": 68,
    "private_markets": 65,
}


def _fuse(items: list[EvidenceItem]) -> list[dict[str, Any]]:
    """Deduplicate by entity+source, rank by confidence/score, keep provenance."""
    seen: set[str] = set()
    fused: list[EvidenceItem] = []
    for item in sorted(
        items,
        key=lambda x: (SOURCE_PRIORITY.get(x.source, 50), x.confidence, x.score),
        reverse=True,
    ):
        key = f"{item.source}:{item.entity}:{item.summary[:80]}".lower()
        if key in seen:
            continue
        seen.add(key)
        fused.append(item)
    return [i.as_dict() for i in fused[:20]]


def _hints_from_evidence(evidence: list[dict[str, Any]]) -> list[str]:
    hints: list[str] = []
    for item in evidence[:8]:
        src = item.get("source")
        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue
        label = {
            "private_markets": "Private Markets",
            "valuation_monitor": "Valuation Monitor",
            "transactions_cms": "Transactions",
            "nifty_research": "Nifty Research",
        }.get(str(src), str(src))
        hints.append(f"[{label}] {summary}"[:400])
    return hints


def retrieve_multi_source(
    question: str,
    *,
    ticker: str | None = None,
    entities: list[dict[str, Any]] | None = None,
    timeout_sec: float = 2.8,
) -> dict[str, Any]:
    """
    Soft multi-source retrieval for Ask AGI.
    Never raises — returns empty pack on failure.
    """
    started = time.time()
    routing = route_sources(question, ticker=ticker, entities=entities)
    telemetry: list[dict[str, Any]] = []
    collected: list[EvidenceItem] = []

    jobs: list[tuple[str, Any]] = []
    if routing.get("private_markets"):
        jobs.append(("private_markets", PrivateMarketsSource()))
    if routing.get("valuation_monitor"):
        jobs.append(("valuation_monitor", ValuationCmsSource()))
    if routing.get("nifty_research"):
        jobs.append(("nifty_research", NiftyResearchSource()))

    if not jobs:
        return {
            "enabled": True,
            "routing": routing,
            "sources_queried": [],
            "evidence": [],
            "ask_agi_hints": [],
            "evidence_count": 0,
            "latency_ms": int((time.time() - started) * 1000),
            "fabricated": False,
        }

    def _run(source_id: str, adapter: Any) -> tuple[str, list[EvidenceItem], float, str | None]:
        t0 = time.time()
        try:
            items = adapter.search(question, ticker=ticker) or []
            return source_id, items, (time.time() - t0) * 1000, None
        except Exception as exc:
            return source_id, [], (time.time() - t0) * 1000, str(exc)[:160]

    with ThreadPoolExecutor(max_workers=min(4, len(jobs))) as pool:
        futures = {pool.submit(_run, sid, adapter): sid for sid, adapter in jobs}
        try:
            for fut in as_completed(futures, timeout=timeout_sec):
                sid, items, latency, err = fut.result()
                telemetry.append(
                    {
                        "id": sid,
                        "status": "error" if err else ("hit" if items else "empty"),
                        "latency_ms": int(latency),
                        "hit_count": len(items),
                        "error": err,
                    }
                )
                collected.extend(items)
        except Exception:
            # Timeout or executor failure — keep whatever completed
            for fut, sid in futures.items():
                if fut.done():
                    try:
                        s, items, latency, err = fut.result()
                        telemetry.append(
                            {
                                "id": s,
                                "status": "error" if err else ("hit" if items else "empty"),
                                "latency_ms": int(latency),
                                "hit_count": len(items),
                                "error": err,
                            }
                        )
                        collected.extend(items)
                    except Exception:
                        telemetry.append({"id": sid, "status": "error", "latency_ms": 0, "hit_count": 0})
                else:
                    telemetry.append({"id": sid, "status": "timeout", "latency_ms": int(timeout_sec * 1000), "hit_count": 0})

    evidence = _fuse(collected)
    hints = _hints_from_evidence(evidence)
    return {
        "enabled": True,
        "routing": routing,
        "sources_queried": telemetry,
        "evidence": evidence,
        "ask_agi_hints": hints,
        "evidence_count": len(evidence),
        "conflicts": [],  # reserved — adapters currently complementary
        "latency_ms": int((time.time() - started) * 1000),
        "fabricated": False,
        "architecture": "multi_source_v1",
    }
