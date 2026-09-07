"""Evidence extraction, fact/opinion separation, scoring, house-view alignment."""

from __future__ import annotations

from typing import Any

from app.rsp.models import EvidenceStatement


FACT_HINTS = (
    "reported",
    "filed",
    "announced",
    "eps",
    "revenue",
    "nim",
    "roe",
    "on 20",
    "dated",
    "as of",
    "grew",
    "declined",
    "%",
)
OPINION_HINTS = (
    "we believe",
    "we expect",
    "thesis",
    "should",
    "likely",
    "overweight",
    "underweight",
    "buy",
    "sell",
    "prefer",
    "view",
    "fair value",
    "target",
)


def extract_evidence(
    *,
    ranked_sources: list[dict[str, Any]],
    house_view: dict[str, Any] | None,
    engines: dict[str, Any],
    kip_context: dict[str, Any] | None,
) -> list[EvidenceStatement]:
    rows: list[EvidenceStatement] = []

    # House view thesis
    if house_view:
        cv = house_view.get("current_view") or {}
        thesis = str(cv.get("thesis") or house_view.get("latest_thesis") or "")
        if thesis:
            rows.append(
                _mk(
                    thesis,
                    source="house_view",
                    kind="opinion",
                    reliability=0.95,
                    freshness=float(house_view.get("research_confidence") or 0.7),
                    confidence=float(house_view.get("research_confidence") or 0.7),
                    docs=[str(cv.get("document_id") or "")],
                    cluster="base",
                    alignment="aligned",
                )
            )
        for b in (cv.get("bull_case") or house_view.get("bull_case") or [])[:5]:
            rows.append(
                _mk(str(b), source="house_view", kind="opinion", reliability=0.9, cluster="bull", alignment="aligned")
            )
        for b in (cv.get("bear_case") or house_view.get("bear_case") or [])[:5]:
            rows.append(
                _mk(str(b), source="house_view", kind="opinion", reliability=0.9, cluster="bear", alignment="aligned")
            )

    # Retrieved docs / evidence snippets
    for src in ranked_sources:
        snippet = str(src.get("snippet") or src.get("thesis") or src.get("title") or "")
        if not snippet:
            continue
        source_class = str(src.get("source_class") or src.get("type") or src.get("source") or "general")
        reliability = _reliability(source_class)
        kind = separate_kind(snippet)
        cluster = _cluster(snippet, source_class)
        alignment = align_to_house(snippet, house_view)
        rows.append(
            _mk(
                snippet,
                source=source_class,
                kind=kind,
                reliability=reliability,
                freshness=float(src.get("freshness", 0.6) or 0.6),
                confidence=float(src.get("confidence", 0.5) or 0.5),
                docs=[str(src.get("document_id") or "")] if src.get("document_id") else [],
                cluster=cluster,
                alignment=alignment,
                engines=[],
            )
        )

    # Engine outputs as evidence
    for eng, payload in engines.items():
        if not payload:
            continue
        statement = _engine_statement(eng, payload)
        if not statement:
            continue
        rows.append(
            _mk(
                statement,
                source=eng,
                kind="fact" if eng in {"e01", "e05", "e11"} else "opinion",
                reliability=0.85,
                freshness=0.9,
                confidence=float(payload.get("confidence") or payload.get("score") or 0.6),
                cluster=_engine_cluster(eng, payload),
                alignment=align_to_house(statement, house_view),
                engines=[eng.upper()],
            )
        )

    # Score + attach contradicting docs from kip conflicting set
    conflict_ids = []
    for c in (kip_context or {}).get("conflicting_evidence") or []:
        if isinstance(c, dict) and c.get("document_id"):
            conflict_ids.append(str(c["document_id"]))
    for e in rows:
        e.score = score_evidence(e)
        if e.house_view_alignment == "contrary":
            e.contradicting_documents = list(dict.fromkeys(e.supporting_documents + conflict_ids))[:8]
        elif conflict_ids and e.source.startswith("agi"):
            e.contradicting_documents = conflict_ids[:6]

    return rows


def separate_facts_opinions(
    evidence: list[EvidenceStatement],
) -> tuple[list[EvidenceStatement], list[EvidenceStatement]]:
    facts = [e for e in evidence if e.kind == "fact"]
    opinions = [e for e in evidence if e.kind == "opinion"]
    return facts, opinions


def separate_kind(text: str) -> str:
    t = (text or "").lower()
    fact_hits = sum(1 for h in FACT_HINTS if h in t)
    opinion_hits = sum(1 for h in OPINION_HINTS if h in t)
    if fact_hits > opinion_hits and fact_hits > 0:
        return "fact"
    return "opinion"


def score_evidence(e: EvidenceStatement) -> float:
    score = 0.35 * e.reliability + 0.25 * e.freshness + 0.25 * e.confidence
    if e.house_view_alignment == "aligned":
        score += 0.1
    elif e.house_view_alignment == "contrary":
        score += 0.05  # still informative
    if e.engine_support:
        score += 0.05
    return round(min(0.99, score), 4)


def align_to_house(text: str, house_view: dict[str, Any] | None) -> str:
    if not house_view:
        return "unknown"
    cv = house_view.get("current_view") or {}
    thesis = str(cv.get("thesis") or house_view.get("latest_thesis") or "").lower()
    if not thesis:
        return "unknown"
    t = (text or "").lower()
    bullish_hv = any(w in thesis for w in ("prefer", "franchise", "buy", "constructive", "quality", "strength"))
    bearish_txt = any(w in t for w in ("sell", "downgrade", "underweight", "bearish", "avoid"))
    bullish_txt = any(w in t for w in ("buy", "upgrade", "overweight", "bullish", "preferred"))
    if bullish_hv and bearish_txt:
        return "contrary"
    if bullish_hv and bullish_txt:
        return "aligned"
    # token overlap
    hv_tokens = {w for w in thesis.split() if len(w) > 4}
    tx_tokens = {w for w in t.split() if len(w) > 4}
    overlap = len(hv_tokens & tx_tokens)
    if overlap >= 3:
        return "aligned"
    if bearish_txt and bullish_hv:
        return "contrary"
    return "neutral"


def _mk(
    statement: str,
    *,
    source: str,
    kind: str,
    reliability: float = 0.6,
    freshness: float = 0.6,
    confidence: float = 0.55,
    docs: list[str] | None = None,
    cluster: str = "base",
    alignment: str = "unknown",
    engines: list[str] | None = None,
) -> EvidenceStatement:
    docs = [d for d in (docs or []) if d]
    return EvidenceStatement(
        statement=statement.strip()[:600],
        kind=kind,  # type: ignore[arg-type]
        source=source,
        reliability=reliability,
        freshness=freshness,
        confidence=confidence,
        supporting_documents=docs,
        engine_support=engines or [],
        house_view_alignment=alignment,  # type: ignore[arg-type]
        cluster=cluster,
    )


def _reliability(source_class: str) -> float:
    s = source_class.lower()
    if "agi" in s or "house" in s:
        return 0.95
    if s.startswith("e") and len(s) <= 3:
        return 0.85
    if "l4" in s:
        return 0.8
    if "broker" in s:
        return 0.75
    if "filing" in s:
        return 0.9
    if "news" in s:
        return 0.55
    return 0.5


def _cluster(text: str, source_class: str) -> str:
    t = text.lower()
    if any(w in t for w in ("risk", "npa", "stress", "concern")):
        return "risk"
    if any(w in t for w in ("catalyst", "earnings", "upcoming")):
        return "catalyst"
    if any(w in t for w in ("target", "valuation", "multiple", "fair value")):
        return "valuation"
    if any(w in t for w in ("macro", "regime", "rates", "rbi", "fed")):
        return "macro"
    if any(w in t for w in ("sell", "downgrade", "underweight", "bear")):
        return "bear"
    if any(w in t for w in ("buy", "upgrade", "overweight", "bull")):
        return "bull"
    if "broker" in source_class.lower():
        return "base"
    return "base"


def _engine_statement(eng: str, payload: dict[str, Any]) -> str:
    side = payload.get("side") or payload.get("label") or payload.get("regime") or payload.get("signal")
    conf = payload.get("confidence") or payload.get("score")
    extra = payload.get("summary") or payload.get("thesis") or ""
    parts = [f"{eng.upper()} state: {side}"]
    if conf is not None:
        parts.append(f"confidence={conf}")
    if extra:
        parts.append(str(extra)[:160])
    # portfolio exposure
    if eng == "e10":
        return f"E10 portfolio exposure: {payload}"
    return "; ".join(str(p) for p in parts if p)


def _engine_cluster(eng: str, payload: dict[str, Any]) -> str:
    if eng in {"e01", "e14"}:
        return "macro"
    if eng in {"e05"}:
        return "catalyst"
    if eng in {"e08", "e09", "e04", "e03", "e02"}:
        return "base"
    if eng in {"e11"}:
        side = str(payload.get("side") or payload.get("label") or "").lower()
        if "bear" in side or "neg" in side:
            return "bear"
        if "bull" in side or "pos" in side:
            return "bull"
    if eng in {"e13", "l4"}:
        side = str(payload.get("side") or "").lower()
        if side in {"long", "buy"}:
            return "bull"
        if side in {"short", "sell"}:
            return "bear"
    return "base"
