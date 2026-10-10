"""RQ1 Sprint 1 — deterministic research ontology classifier.

No analysts. No intelligence layers. Constitution-first routing only.
"""

from __future__ import annotations

import re
from typing import Any

from research_ontology.entities import AMBIGUOUS_STEMS, resolve_entities
from research_ontology.schema import (
    NEXT_STAGE_BLOCKED,
    NEXT_STAGE_CLARIFY,
    NEXT_STAGE_CLASSIFY_ONLY,
    NO_ANALYST_EXECUTION,
    NO_LAYER_EXECUTION,
    RQ1_VERSION,
    SPRINT,
    intent_label,
    intent_objective,
)


def _norm(text: str) -> str:
    t = (text or "").lower()
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9./\s?-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _has_any(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    return any(p in text for p in phrases)


def _score_primary(norm: str, entity_pack: dict[str, Any]) -> tuple[str, float, list[str]]:
    """Return (intent_id, confidence 0-1, reasons)."""
    reasons: list[str] = []
    scores: dict[str, float] = {k: 0.0 for k in [
        "company_research",
        "sector_research",
        "index_research",
        "macro_research",
        "portfolio_research",
        "company_comparison",
        "screening",
        "forecast",
        "risk",
        "valuation",
        "technical",
        "educational",
        "news",
    ]}

    entities = entity_pack.get("entities") or []
    types = {e.get("entity_type") for e in entities}
    company_count = sum(1 for e in entities if e.get("entity_type") == "Company")

    # Educational — explain/teach concept
    if _has_any(norm, ("explain ", "what is ", "teach ", "define ", "meaning of ")):
        if any(e.get("concept") for e in entities) or _has_any(
            norm, ("roic", "ev/ebitda", "dcf", "p/e", "pe ratio", "pb ratio", "cagr", "wacc")
        ):
            scores["educational"] += 5.0
            reasons.append("educational_concept_lexicon")

    # Comparison
    if re.search(r"\bvs\.?\b|\bversus\b|\bcompare\b|\bcomparison\b", norm) and company_count >= 2:
        scores["company_comparison"] += 5.5
        reasons.append("compare_two_companies")
    elif re.search(r"\bvs\.?\b|\bversus\b|\bcompare\b", norm) and "Index" in types:
        scores["index_research"] += 4.0
        reasons.append("index_comparison")

    # Screening
    if _has_any(
        norm,
        (
            "best ",
            "top ",
            "high roic",
            "low debt",
            "screen",
            "stocks with",
            "companies with",
            "list of ",
        ),
    ):
        scores["screening"] += 4.8
        reasons.append("screening_lexicon")

    # News / event
    if _has_any(
        norm,
        (
            "today",
            "why did",
            "latest ",
            "announcement",
            "earnings summary",
            "summarise",
            "summarize",
            "quarterly earnings",
            "results today",
        ),
    ):
        scores["news"] += 4.6
        reasons.append("news_event_lexicon")

    # Technical
    if _has_any(
        norm,
        ("breakout", "rsi", "moving average", "moving averages", "macd", "chart", "trend?", "support", "resistance"),
    ) or re.search(r"\btrend\b", norm) and _has_any(norm, ("price", "stock", "chart")):
        scores["technical"] += 4.5
        reasons.append("technical_lexicon")

    # Portfolio
    if _has_any(
        norm,
        (
            "portfolio",
            "diversif",
            "rebalanc",
            "allocation",
            "add to my",
            "should i add",
            "my holdings",
            "position size",
        ),
    ):
        scores["portfolio_research"] += 4.7
        reasons.append("portfolio_lexicon")

    # Macro
    if _has_any(
        norm,
        (
            "rbi",
            "rate cut",
            "rates cut",
            "cuts rates",
            "inflation",
            "recession",
            "oil at",
            "fed ",
            "macro",
            "gdp",
            "cpi",
            "what happens if",
        ),
    ) or "Macro Variable" in types:
        scores["macro_research"] += 4.4
        reasons.append("macro_lexicon")

    # Index
    if "Index" in types or _has_any(norm, ("nifty", "sensex", "nasdaq", "s&p", "spx")):
        scores["index_research"] += 3.8
        reasons.append("index_entity")
        if _has_any(norm, ("expensive", "cheap", "overvalued", "undervalued", "versus history", "vs history")):
            scores["index_research"] += 1.5
            reasons.append("index_valuation_frame")

    # Sector
    if "Sector" in types or _has_any(norm, ("sector", "industry", "which sector")):
        scores["sector_research"] += 3.9
        reasons.append("sector_entity")

    # Risk primary
    if _has_any(
        norm,
        (
            "biggest risk",
            "biggest risks",
            "downside",
            "what breaks",
            "risks to",
            "tail risk",
            "drawdown",
        ),
    ):
        scores["risk"] += 4.6
        reasons.append("risk_primary_lexicon")

    # Valuation primary
    if _has_any(
        norm,
        (
            "fair value",
            "undervalued",
            "overvalued",
            "is expensive",
            "expensive versus",
            "pe vs",
            "p/e vs",
            "valuation of",
        ),
    ):
        # Prefer valuation when it's the core ask and not clearly index/sector framing
        if "Index" in types:
            scores["index_research"] += 1.2
        elif company_count == 1 and not _has_any(norm, ("should i buy", "should i add")):
            scores["valuation"] += 4.2
            reasons.append("valuation_primary_lexicon")
        else:
            scores["valuation"] += 2.0

    # Forecast primary
    if _has_any(
        norm,
        (
            "outlook",
            "forecast",
            "in two years",
            "in 2 years",
            "where will",
            "next five years",
            "next 5 years",
            "long-term outlook",
        ),
    ):
        if _has_any(norm, ("should i buy", "should i add", "analyse", "analyze")):
            scores["forecast"] += 1.5
        else:
            scores["forecast"] += 4.3
            reasons.append("forecast_primary_lexicon")

    # Company research defaults
    if company_count == 1:
        scores["company_research"] += 2.8
        reasons.append("single_company_entity")
    if _has_any(
        norm,
        (
            "should i buy",
            "should i invest",
            "analyse ",
            "analyze ",
            "explain ",
            "is reliance",
            "buy hdfc",
            "buy infosys",
        ),
    ) and company_count >= 1:
        scores["company_research"] += 2.5
        reasons.append("company_action_lexicon")

    # Educational explain company? keep company if "explain TCS" style with company entity and no concept
    if norm.startswith("explain ") and company_count == 1 and not any(e.get("concept") for e in entities):
        scores["company_research"] += 3.0
        scores["educational"] -= 2.0
        reasons.append("explain_company")

    # Tie-break preferences
    best_id = max(scores, key=lambda k: scores[k])
    best = scores[best_id]
    if best <= 0.5:
        # fallback by entity type
        if company_count >= 2:
            best_id, best = "company_comparison", 0.55
        elif "Index" in types:
            best_id, best = "index_research", 0.55
        elif "Sector" in types:
            best_id, best = "sector_research", 0.55
        elif "Macro Variable" in types:
            best_id, best = "macro_research", 0.55
        elif company_count == 1:
            best_id, best = "company_research", 0.55
        else:
            best_id, best = "company_research", 0.35
            reasons.append("low_signal_fallback")

    # Confidence calibration
    second = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0.0
    margin = best - second
    confidence = min(0.99, 0.55 + 0.08 * best + 0.1 * margin)
    if best_id == "educational" and any(e.get("concept") for e in entities):
        confidence = max(confidence, 0.97)
    if best_id == "company_comparison" and company_count >= 2:
        confidence = max(confidence, 0.96)
    if best >= 4.5 and margin >= 1.0:
        confidence = max(confidence, 0.95)

    return best_id, round(confidence, 4), reasons


def _secondary(norm: str, primary: str, entity_pack: dict[str, Any]) -> list[str]:
    sec: list[str] = []

    def add(x: str) -> None:
        if x and x not in sec and x != primary and x not in {
            # don't mirror primary id into secondary when same family name
        }:
            # map primary-like ids to secondary keys
            key = {
                "valuation": "valuation",
                "risk": "risk",
                "forecast": "forecast",
                "portfolio_research": "portfolio",
                "technical": "technical",
                "news": "news",
                "educational": "educational",
                "sector_research": "sector",
                "index_research": "index",
                "macro_research": "macro",
            }.get(x, x)
            if key not in sec and key != primary:
                sec.append(key)

    if _has_any(norm, ("valu", "expensive", "cheap", "fair value", "pe ", "p/e", "undervalued", "overvalued")):
        add("valuation")
    if _has_any(norm, ("risk", "downside", "what breaks", "drawdown")):
        add("risk")
    if _has_any(norm, ("forecast", "outlook", "years", "where will", "long-term", "long term", "five years", "2 years", "two years")):
        add("forecast")
    if _has_any(norm, ("five years", "5 years", "long-term", "long term", "multi-year")):
        add("long_term")
    if _has_any(norm, ("today", "this week", "short-term", "short term", "near term")):
        add("short_term")
    if _has_any(norm, ("portfolio", "allocation", "diversif", "rebalanc", "should i add")):
        add("portfolio")
    if _has_any(norm, ("versus history", "vs history", "historical", "vs its history", "against history")):
        add("historical_comparison")
    if _has_any(norm, ("rbi", "inflation", "recession", "macro", "rates")) and primary != "macro_research":
        add("macro")
    if _has_any(norm, ("peer", "vs ", "versus", "compare")) and primary != "company_comparison":
        add("peer")
    if _has_any(norm, ("earnings", "results", "quarterly")):
        add("earnings")

    # Primary-specific useful defaults for company buy questions
    if primary == "company_research" and _has_any(norm, ("should i buy", "should i invest")):
        for x in ("valuation", "risk", "forecast"):
            add(x)
    if primary == "portfolio_research" and any(
        e.get("entity_type") == "Company" for e in (entity_pack.get("entities") or [])
    ):
        for x in ("risk", "valuation"):
            add(x)
    if primary == "index_research" and _has_any(norm, ("expensive", "cheap", "history")):
        add("valuation")
        add("historical_comparison")

    return sec


def _ambiguous_tata(norm: str, entity_pack: dict[str, Any]) -> dict[str, Any] | None:
    if not re.search(r"(?<![a-z0-9])tata(?![a-z0-9])", norm):
        return None
    # longer forms already resolved
    for e in entity_pack.get("entities") or []:
        name = str(e.get("entity") or "").lower()
        alias = str(e.get("matched_alias") or "")
        if alias.startswith("tata ") or name in {"tcs", "titan", "tata motors", "tata power"}:
            if alias != "tata":
                return None
    if "tata" in norm and not any(
        x in norm for x in ("tata motors", "tata power", "tata steel", "tata consultancy", "tcs", "titan")
    ):
        return {
            "requires_clarification": True,
            "possible_matches": AMBIGUOUS_STEMS["tata"],
            "ambiguity": "tata",
            "confidence": 0.43,
        }
    return None


def classify_question(question: str) -> dict[str, Any]:
    q = (question or "").strip()
    norm = _norm(q)
    entity_pack = resolve_entities(q)

    amb = _ambiguous_tata(norm, entity_pack)
    if amb or entity_pack.get("requires_clarification"):
        matches = (amb or {}).get("possible_matches") or entity_pack.get("possible_matches") or []
        conf = float((amb or {}).get("confidence") or 0.43)
        primary = "company_research"
        return {
            "ok": True,
            "rq1_version": RQ1_VERSION,
            "sprint": SPRINT,
            "question": q,
            "question_type": intent_label(primary),
            "primary_intent": intent_label(primary),
            "primary_intent_id": primary,
            "secondary_intents": [],
            "entity": None,
            "entity_type": "Unknown",
            "ticker": None,
            "entities": [],
            "research_objective": intent_objective(primary),
            "confidence": conf,
            "confidence_pct": int(round(conf * 100)),
            "requires_clarification": True,
            "possible_matches": matches,
            "next_stage": NEXT_STAGE_CLARIFY,
            "blocked": True,
            "executed_layers": [],
            "executed_analysts": [],
            "no_layer_execution": NO_LAYER_EXECUTION,
            "no_analyst_execution": NO_ANALYST_EXECUTION,
            "reasons": ["ambiguous_entity"],
            "routing_decision": "No research begins until entity is clarified.",
        }

    primary_id, confidence, reasons = _score_primary(norm, entity_pack)
    secondary = _secondary(norm, primary_id, entity_pack)

    # Prefer primary company entity when multiple types present for company intents
    entities = entity_pack.get("entities") or []
    chosen = None
    if primary_id in {"company_research", "valuation", "risk", "news", "forecast", "portfolio_research"}:
        chosen = next((e for e in entities if e.get("entity_type") == "Company"), None)
    if primary_id == "company_comparison":
        cos = [e for e in entities if e.get("entity_type") == "Company"]
        # Preserve mention order in the question text
        cos = sorted(
            cos,
            key=lambda e: norm.find(str(e.get("matched_alias") or e.get("entity") or "").lower())
            if str(e.get("matched_alias") or e.get("entity") or "").lower() in norm
            else 10_000,
        )
        chosen = {
            "entity": " vs ".join(e["entity"] for e in cos[:3]) if cos else None,
            "entity_type": "Company",
            "ticker": ",".join(e.get("ticker") or "" for e in cos[:3]) if cos else None,
        }
    if primary_id == "index_research":
        chosen = next((e for e in entities if e.get("entity_type") == "Index"), None)
    if primary_id == "sector_research":
        chosen = next((e for e in entities if e.get("entity_type") == "Sector"), None)
    if primary_id == "macro_research":
        chosen = next((e for e in entities if e.get("entity_type") == "Macro Variable"), None)
    if primary_id == "educational":
        chosen = next((e for e in entities if e.get("concept")), None) or (entities[0] if entities else None)
    if primary_id == "screening":
        chosen = next((e for e in entities if e.get("entity_type") == "Sector"), None) or {
            "entity": "Screen Universe",
            "entity_type": "Sector",
            "ticker": None,
        }
    if chosen is None and entities:
        chosen = entities[0]

    entity = (chosen or {}).get("entity")
    entity_type = (chosen or {}).get("entity_type") or "Unknown"
    ticker = (chosen or {}).get("ticker")

    needs_clarify = False
    matches: list[Any] = []
    if primary_id in {"company_research", "valuation", "risk", "news"} and not entity:
        needs_clarify = True
        confidence = min(confidence, 0.45)

    next_stage = NEXT_STAGE_CLASSIFY_ONLY
    if needs_clarify:
        next_stage = NEXT_STAGE_BLOCKED

    return {
        "ok": True,
        "rq1_version": RQ1_VERSION,
        "sprint": SPRINT,
        "question": q,
        "question_type": intent_label(primary_id),
        "primary_intent": intent_label(primary_id),
        "primary_intent_id": primary_id,
        "secondary_intents": secondary,
        "entity": entity,
        "entity_type": entity_type,
        "ticker": ticker,
        "entities": entities,
        "research_objective": intent_objective(primary_id),
        "confidence": confidence,
        "confidence_pct": int(round(confidence * 100)),
        "requires_clarification": needs_clarify,
        "possible_matches": matches,
        "next_stage": next_stage,
        "blocked": needs_clarify,
        "executed_layers": [],
        "executed_analysts": [],
        "no_layer_execution": NO_LAYER_EXECUTION,
        "no_analyst_execution": NO_ANALYST_EXECUTION,
        "reasons": reasons,
        "routing_decision": (
            "Classification complete — Sprint 1 stops here (no analysts / layers)."
            if not needs_clarify
            else "Blocked — clarification required before research."
        ),
    }
