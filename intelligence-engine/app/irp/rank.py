"""Steps 5–6 — Semantic filter + evidence ranking (uses KIP artefacts; no redesign)."""

from __future__ import annotations

from typing import Any

from app.irp.models import RankedEvidenceItem, ResearchPlan, ResolvedEntityPack

_SOURCE_RELIABILITY = {
    "agi_research": 0.95,
    "house_view": 0.93,
    "broker_research": 0.8,
    "broker": 0.8,
    "company_filings": 0.9,
    "filing": 0.9,
    "earnings": 0.85,
    "latest_news": 0.55,
    "news": 0.55,
    "general": 0.5,
    "conflict": 0.6,
}

_SOURCE_RANK = {
    "agi_research": 1,
    "house_view": 2,
    "broker_research": 3,
    "broker": 3,
    "company_filings": 4,
    "filing": 4,
    "earnings": 5,
    "latest_news": 6,
    "news": 6,
    "general": 7,
    "conflict": 5,
}


def filter_and_rank_evidence(
    items: list[dict[str, Any]],
    *,
    entities: ResolvedEntityPack,
    plan: ResearchPlan,
) -> tuple[list[RankedEvidenceItem], list[RankedEvidenceItem]]:
    accepted: list[RankedEvidenceItem] = []
    rejected: list[RankedEvidenceItem] = []
    focus = {t.upper() for t in (entities.tickers or plan.focus_tickers or [])}
    sector_tokens = _sector_tokens(entities)
    reject_topics = [t.lower() for t in (entities.reject_topics or plan.reject_topics or [])]

    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "")
        snippet = str(raw.get("snippet") or raw.get("summary") or "")
        blob = f"{title} {snippet}".lower()
        source = str(raw.get("source_class") or raw.get("type") or raw.get("document_type") or "general")
        tickers = [str(t).upper() for t in (raw.get("tickers") or []) if t]

        reject_reason = None
        if any(rt in blob for rt in reject_topics):
            # Allow if also clearly on-focus
            if not (sector_tokens and any(tok in blob for tok in sector_tokens)) and not (
                focus and any(t in focus for t in tickers)
            ):
                reject_reason = "unrelated_topic"
        if focus and tickers and not any(t in focus for t in tickers):
            # Off-universe company mention with no sector overlap
            if sector_tokens and not any(tok in blob for tok in sector_tokens):
                reject_reason = "unrelated_company"
        if sector_tokens and not any(tok in blob for tok in sector_tokens):
            if not (focus and any(t in focus for t in tickers)):
                # Keep AGI docs with weak lexical overlap if title isn't junk
                if "agi" not in source.lower() and source not in {"agi_research", "house_view"}:
                    reject_reason = reject_reason or "weak_entity_overlap"

        relevance = _relevance(blob, title, tickers, focus, sector_tokens)
        freshness = float(raw.get("freshness") or raw.get("freshness_score") or 0.6)
        reliability = float(raw.get("reliability_score") or _SOURCE_RELIABILITY.get(source, 0.55))
        if isinstance(raw.get("reliability"), str):
            reliability = {"high": 0.9, "medium": 0.65, "low": 0.4}.get(
                str(raw["reliability"]).lower(), reliability
            )
        coverage = min(1.0, 0.35 + 0.15 * len(tickers) + (0.25 if any(tok in blob for tok in sector_tokens) else 0))
        confidence = float(raw.get("confidence") or 0.5)
        if confidence > 1:
            confidence = confidence / 100.0

        item = RankedEvidenceItem(
            document_id=str(raw.get("document_id") or raw.get("id") or "") or None,
            title=title,
            snippet=snippet[:400],
            source_class=source,
            stance=str(raw.get("stance") or "neutral"),
            relevance_score=round(relevance, 4),
            freshness=round(freshness, 4),
            reliability=round(reliability, 4),
            coverage=round(coverage, 4),
            confidence=round(confidence, 4),
            tickers=tickers,
            rejected=bool(reject_reason),
            reject_reason=reject_reason,
            raw=raw,
        )
        if reject_reason:
            rejected.append(item)
        else:
            accepted.append(item)

    accepted.sort(
        key=lambda x: (
            _SOURCE_RANK.get(x.source_class, 7),
            -x.relevance_score,
            -x.reliability,
            -x.freshness,
        )
    )
    return accepted, rejected


def _sector_tokens(entities: ResolvedEntityPack) -> list[str]:
    out: list[str] = []
    for value in (entities.sector_label, entities.sector, entities.sector_key):
        if not value:
            continue
        out.extend(str(value).lower().replace("_", " ").split())
    out.extend(["it services", "indian it", "information technology", "software"])
    # company names for sector questions
    for c in entities.companies or []:
        if c.get("name"):
            out.append(str(c["name"]).lower())
        if c.get("ticker"):
            out.append(str(c["ticker"]).lower())
    # unique
    seen: set[str] = set()
    tokens: list[str] = []
    for t in out:
        t = t.strip()
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        tokens.append(t)
    return tokens


def _relevance(
    blob: str,
    title: str,
    tickers: list[str],
    focus: set[str],
    sector_tokens: list[str],
) -> float:
    score = 0.2
    if any(tok in blob for tok in sector_tokens):
        score += 0.35
    if focus and any(t in focus for t in tickers):
        score += 0.3
    if any(t.lower() in (title or "").lower() for t in focus):
        score += 0.15
    if "q1fy" in blob or "outlook" in blob or "house view" in blob:
        score += 0.1
    return min(1.0, score)
