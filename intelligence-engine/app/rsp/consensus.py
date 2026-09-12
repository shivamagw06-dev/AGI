"""Consensus engine — AGI / broker / market / contrarian / unknowns."""

from __future__ import annotations

from typing import Any

from app.rsp.models import ConsensusView, EvidenceStatement, OpinionCluster


def cluster_opinions(evidence: list[EvidenceStatement]) -> list[OpinionCluster]:
    buckets: dict[str, list[EvidenceStatement]] = {
        "bull": [],
        "bear": [],
        "valuation": [],
        "risk": [],
        "catalyst": [],
        "macro": [],
        "base": [],
    }
    for e in evidence:
        if e.kind != "opinion" and e.cluster not in buckets:
            # facts can still inform clusters lightly
            pass
        label = e.cluster or _infer_cluster(e.statement)
        buckets.setdefault(label, []).append(e)

    clusters: list[OpinionCluster] = []
    for label, rows in buckets.items():
        if not rows:
            continue
        stance = "neutral"
        if label == "bull":
            stance = "bullish"
        elif label == "bear":
            stance = "bearish"
        weight = sum(r.score for r in rows) / max(1, len(rows))
        clusters.append(
            OpinionCluster(
                cluster_id=f"cluster_{label}",
                label=label,
                stance=stance,
                statements=[r.statement for r in rows[:8]],
                sources=sorted({r.source for r in rows if r.source})[:12],
                weight=round(weight, 4),
            )
        )
    clusters.sort(key=lambda c: c.weight, reverse=True)
    return clusters


def build_consensus(
    *,
    evidence: list[EvidenceStatement],
    clusters: list[OpinionCluster],
    house_view: dict[str, Any] | None,
    engines: dict[str, Any],
    kip_context: dict[str, Any] | None,
) -> ConsensusView:
    agi_rows = [e for e in evidence if e.source.startswith("agi") or e.source == "house_view"]
    broker_rows = [e for e in evidence if "broker" in e.source.lower()]
    news_rows = [e for e in evidence if "news" in e.source.lower()]

    hv_thesis = ""
    if house_view:
        cv = house_view.get("current_view") or {}
        hv_thesis = str(cv.get("thesis") or "")
        if not hv_thesis:
            hv_thesis = str(house_view.get("latest_thesis") or "")

    agi_view = hv_thesis or (agi_rows[0].statement if agi_rows else "AGI house view unavailable")
    broker_consensus = _summarize_stance(broker_rows, fallback="Broker consensus unavailable")
    market_consensus = _market_from_engines(engines, news_rows)
    contrarian = _contrarian(agi_view, broker_rows, clusters)
    unknowns = _unknowns(evidence, house_view, engines, kip_context)

    agreement = _agreement_score(agi_rows, broker_rows, engines)
    return ConsensusView(
        agi_view=agi_view[:800],
        broker_consensus=broker_consensus[:500],
        market_consensus=market_consensus[:500],
        contrarian_view=contrarian[:500],
        unknown_areas=unknowns[:12],
        agreement_score=agreement,
    )


def _infer_cluster(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ("risk", "concern", "npa", "stress", "downgrade")):
        return "risk"
    if any(w in t for w in ("catalyst", "earnings", "upcoming", "trigger")):
        return "catalyst"
    if any(w in t for w in ("valuation", "target", "multiple", "pe ", "fair value")):
        return "valuation"
    if any(w in t for w in ("macro", "rates", "rbi", "fed", "inflation", "regime")):
        return "macro"
    if any(w in t for w in ("buy", "bull", "upgrade", "overweight", "upside")):
        return "bull"
    if any(w in t for w in ("sell", "bear", "underweight", "downside")):
        return "bear"
    return "base"


def _summarize_stance(rows: list[EvidenceStatement], *, fallback: str) -> str:
    if not rows:
        return fallback
    bull = sum(1 for e in rows if e.cluster == "bull" or "buy" in e.statement.lower() or "upgrade" in e.statement.lower())
    bear = sum(1 for e in rows if e.cluster == "bear" or "sell" in e.statement.lower() or "downgrade" in e.statement.lower())
    if bull == 0 and bear == 0:
        return rows[0].statement[:300]
    if bull > bear:
        return f"Broker lean bullish ({bull} vs {bear}): {rows[0].statement[:220]}"
    if bear > bull:
        return f"Broker lean bearish ({bear} vs {bull}): {rows[0].statement[:220]}"
    return f"Broker mixed ({bull}/{bear}): {rows[0].statement[:220]}"


def _market_from_engines(engines: dict[str, Any], news: list[EvidenceStatement]) -> str:
    parts: list[str] = []
    l4 = engines.get("l4") or {}
    if l4:
        parts.append(
            f"L4 {l4.get('side') or l4.get('label') or 'n/a'} "
            f"(conf={l4.get('confidence', l4.get('score', 'n/a'))})"
        )
    e01 = engines.get("e01") or {}
    if e01:
        parts.append(f"Regime={e01.get('regime') or e01.get('label') or 'n/a'}")
    e11 = engines.get("e11") or {}
    if e11:
        parts.append(f"Sentiment={e11.get('label') or e11.get('side') or 'n/a'}")
    if news:
        parts.append(f"News: {news[0].statement[:160]}")
    return "; ".join(parts) if parts else "Market consensus unavailable"


def _contrarian(agi_view: str, broker: list[EvidenceStatement], clusters: list[OpinionCluster]) -> str:
    bear = next((c for c in clusters if c.label == "bear"), None)
    if bear and bear.statements:
        return f"Contrarian / bear case: {bear.statements[0]}"
    for e in broker:
        if "sell" in e.statement.lower() or "underweight" in e.statement.lower() or "downgrade" in e.statement.lower():
            if "preferred" in agi_view.lower() or "buy" in agi_view.lower() or "franchise" in agi_view.lower():
                return f"Contrarian vs AGI: {e.statement[:300]}"
    return "No strong contrarian view identified"


def _unknowns(
    evidence: list[EvidenceStatement],
    house_view: dict[str, Any] | None,
    engines: dict[str, Any],
    kip_context: dict[str, Any] | None,
) -> list[str]:
    unk: list[str] = []
    if not house_view or not (house_view.get("current_view") or house_view.get("latest_thesis")):
        unk.append("AGI house view incomplete for this ticker")
    if not any("broker" in e.source.lower() for e in evidence):
        unk.append("Limited broker coverage in retrieval")
    if not engines.get("l4"):
        unk.append("L4 opinion not supplied")
    if not engines.get("e13"):
        unk.append("Fundamental engine state (E13) not supplied")
    if not (kip_context or {}).get("filings_used") and not (kip_context or {}).get("filings"):
        unk.append("No recent filings in retrieval set")
    if house_view and house_view.get("failed_assumptions"):
        unk.append("Prior assumptions marked failed — outcome uncertain")
    return unk


def _agreement_score(
    agi: list[EvidenceStatement],
    broker: list[EvidenceStatement],
    engines: dict[str, Any],
) -> float:
    if not agi and not broker:
        return 0.3
    score = 0.5
    agi_bull = any(e.cluster == "bull" or "buy" in e.statement.lower() for e in agi)
    broker_bull = any(e.cluster == "bull" or "buy" in e.statement.lower() or "upgrade" in e.statement.lower() for e in broker)
    broker_bear = any(e.cluster == "bear" or "sell" in e.statement.lower() or "downgrade" in e.statement.lower() for e in broker)
    if agi and broker:
        if agi_bull and broker_bull:
            score = 0.8
        elif agi_bull and broker_bear:
            score = 0.35
        else:
            score = 0.55
    l4 = engines.get("l4") or {}
    side = str(l4.get("side") or "").lower()
    if side in {"long", "buy"} and agi_bull:
        score = min(0.95, score + 0.05)
    if side in {"short", "sell"} and agi_bull:
        score = max(0.2, score - 0.15)
    return round(score, 4)
