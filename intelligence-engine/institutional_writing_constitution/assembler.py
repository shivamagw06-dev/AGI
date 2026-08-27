"""Deterministic writing scaffold — narrative IRE hierarchy with template support."""

from __future__ import annotations

from typing import Any

from institutional_writing_constitution.schema import (
    EVIDENCE_OBSERVATIONS_MAX,
    EVIDENCE_OBSERVATIONS_MIN,
    EVIDENCE_PHRASE_TEMPLATES,
    EXECUTIVE_SUMMARY_MAX_WORDS,
    QUESTIONS_MAX,
    QUESTIONS_MIN,
    RESPONSE_HIERARCHY,
    SECTION_LABELS,
)
from institutional_writing_constitution.templates import DEFAULT_TEMPLATE, template_sections


def _word_count(text: str) -> int:
    return len((text or "").split())


def _truncate_words(text: str, max_words: int) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip() + "…"


def _supported_assertions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    assertions = pack.get("institutional_assertions") or []
    if not assertions:
        sel = pack.get("ikr_selection") or {}
        assertions = sel.get("assertions") or []
    return [
        a for a in assertions
        if isinstance(a, dict) and str(a.get("status") or a.get("state")) in {"SUPPORTED", "PARTIAL", "ANSWERED"}
    ]


def _unknowns(pack: dict[str, Any]) -> list[str]:
    unknowns = pack.get("institutional_unknowns") or []
    out: list[str] = []
    for u in unknowns:
        if isinstance(u, dict):
            stmt = u.get("statement") or u.get("reason")
            if stmt:
                out.append(str(stmt))
        elif isinstance(u, str):
            out.append(u)
    return out[:5]


def _what_matters_most_bullets(pack: dict[str, Any], company: str) -> list[str]:
    """Portfolio-manager focus — what should I pay attention to?"""
    bullets: list[str] = []
    rc = pack.get("response_constitution") or {}
    if rc.get("direct_answer"):
        bullets.append(
            "The immediate focus is whether recent developments change the investment case "
            "or merely confirm what institutional investors already assumed."
        )
    quality = (pack.get("knowledge_quality") or {}).get("metrics") or {}
    if quality.get("evidence_coverage", 0) >= 50:
        bullets.append(
            f"For {company}, the highest-signal areas are business quality durability, "
            "earnings trajectory versus expectations, and whether valuation already prices the thesis."
        )
    else:
        bullets.append(
            "Material evidence gaps remain — treat directional conclusions cautiously until "
            "institutional knowledge is fully compiled."
        )
    bullets.append(
        "Institutional investors would likely focus on what could change earnings power "
        "over the next 12–18 months, not headline noise."
    )
    return bullets[:4]


def _investment_debate_narrative(pack: dict[str, Any], company: str) -> dict[str, Any]:
    """The central investment debate — what great research notes lead with."""
    thesis = pack.get("investment_thesis") or {}
    debate_topic = str(thesis.get("current_thesis") or "business quality versus valuation").lower()
    paragraphs = [
        "The investment debate has shifted.",
        f"Few investors question {company}'s underlying franchise quality at a headline level.",
        (
            f"The real debate is whether {debate_topic.replace(company.lower(), 'the franchise')} "
            "can sustain institutional attention while justifying today's market expectations."
        ),
        "Current evidence supports the quality of the franchise.",
        "Future returns depend more on earnings execution than on discovering a better business.",
    ]
    return {
        "label": SECTION_LABELS["investment_debate"],
        "narrative": paragraphs,
        "text": " ".join(paragraphs),
    }


def _evidence_observations(assertions: list[dict[str, Any]]) -> list[str]:
    """Varied institutional phrasing — not repetitive 'Evidence suggests...'."""
    observations: list[str] = []
    templates = EVIDENCE_PHRASE_TEMPLATES
    for i, a in enumerate(assertions[:EVIDENCE_OBSERVATIONS_MAX]):
        stmt = str(a.get("statement") or "").strip()
        if not stmt:
            continue
        prefix = templates[i % len(templates)]
        conf = a.get("confidence")
        line = f"{prefix} {stmt.rstrip('.')}."
        if conf is not None:
            line = f"{line} (confidence: {conf}%)"
        observations.append(line)
    if not observations:
        placeholders = (
            ("Current evidence indicates", "institutional assertions are not yet compiled for this entity"),
            ("Available evidence does not currently support", "drawing firm conclusions without fuller knowledge compilation"),
            ("Operating trends indicate", "monitoring should focus on thesis drivers once knowledge objects are populated"),
        )
        for prefix, rest in placeholders[:EVIDENCE_OBSERVATIONS_MIN]:
            observations.append(f"{prefix} {rest}.")
    return observations[:EVIDENCE_OBSERVATIONS_MAX]


def _key_uncertainties(pack: dict[str, Any], company: str) -> list[str]:
    items: list[str] = []
    thesis = pack.get("investment_thesis") or {}
    for inv in (thesis.get("invalidation_conditions") or [])[:3]:
        items.append(str(inv))
    contradictions = (pack.get("institutional_knowledge_runtime") or {}).get("contradiction_count", 0)
    if contradictions:
        items.append(f"Resolution of {contradictions} contradicted assertion(s) would materially change the view.")
    items.extend([
        f"Operating margins deteriorate persistently at {company}.",
        "Competitive intensity increases without corresponding pricing power.",
        "Capital allocation weakens relative to historical standards.",
    ])
    return items[:5]


def _research_conclusion(pack: dict[str, Any], company: str) -> dict[str, Any]:
    supported = _supported_assertions(pack)
    unknowns = _unknowns(pack)
    return {
        "label": SECTION_LABELS["research_conclusion"],
        "current_evidence_indicates": (
            f"Current evidence indicates {company} warrants continued institutional research "
            f"with {len(supported)} supported institutional assertion(s) and {len(unknowns)} open unknown(s)."
        ),
        "strongest_evidence_supports": (
            supported[0].get("statement") if supported else "Insufficient compiled assertions — compile Company DNA first."
        ),
        "largest_uncertainty_remains": unknowns[0] if unknowns else "Valuation versus growth expectations alignment.",
        "next_research_priority": (
            (pack.get("next_best_research_question") or {}).get("question")
            or (pack.get("institutional_review") or {}).get("what_research_should_be_updated", [None])[0]
            or f"Validate thesis drivers and monitoring triggers for {company}."
        ),
        "never_recommends": True,
        "user_decides": True,
    }


def _questions_before_you_decide(company: str, ticker: str | None) -> list[str]:
    label = ticker or company
    return [
        f"Is today's valuation on {label} already pricing in expected growth?",
        "What evidence would invalidate today's thesis?",
        f"How does {label} compare with the best alternative investment?",
        f"Would this still be an attractive business after one disappointing quarter?",
        "Does the risk/reward fit portfolio concentration limits?",
    ][:QUESTIONS_MAX]


def _executive_summary(pack: dict[str, Any], company: str) -> dict[str, Any]:
    rc = pack.get("response_constitution") or {}
    exec_src = (
        rc.get("direct_answer")
        or pack.get("executive")
        or pack.get("summary")
        or f"{company} — institutional research summary pending fuller evidence compilation."
    )
    executive = _truncate_words(str(exec_src), EXECUTIVE_SUMMARY_MAX_WORDS)
    return {
        "label": SECTION_LABELS["executive_summary"],
        "text": executive,
        "word_count": _word_count(executive),
        "max_words": EXECUTIVE_SUMMARY_MAX_WORDS,
    }


# --- Template-specific section builders ---

def _what_changed(pack: dict[str, Any], company: str) -> dict[str, Any]:
    rc = pack.get("response_constitution") or {}
    return {
        "label": SECTION_LABELS["what_changed"],
        "bullets": [
            rc.get("direct_answer") or f"Recent results at {company} warrant interpretation against prior expectations.",
            "Management commentary and segment trends are the primary signals for what genuinely changed.",
        ],
    }


def _what_didnt_change(pack: dict[str, Any], company: str) -> dict[str, Any]:
    thesis = pack.get("investment_thesis") or {}
    return {
        "label": SECTION_LABELS["what_didnt_change"],
        "bullets": [
            f"The core franchise characteristics of {company} appear intact unless evidence suggests otherwise.",
            str(thesis.get("current_thesis") or "Long-term competitive positioning remains the anchor for institutional views."),
        ],
    }


def _market_implications(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["market_implications"],
        "bullets": [
            "Market expectations may re-rate the business if results confirm or contradict the prevailing narrative.",
            f"For {company}, the implication is whether today's print changes the earnings trajectory investors are underwriting.",
        ],
    }


def _monitoring(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["monitoring"],
        "bullets": [
            f"Track order intake, margin trajectory, and management guidance revisions for {company}.",
            "Watch for evidence that would confirm or invalidate the current institutional thesis.",
        ],
    }


def _current_expectations(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["current_expectations"],
        "bullets": [
            f"Market expectations on {company} embed assumptions about growth, margins, and capital returns.",
            "The investment question is whether current pricing leaves room for positive surprise.",
        ],
    }


def _historical_context(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["historical_context"],
        "bullets": [
            f"Historical valuation and earnings multiples provide context for whether {company} trades at a premium or discount.",
            "Institutional investors compare today's setup against prior cycle peaks and troughs.",
        ],
    }


def _business_comparison(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["business_comparison"],
        "bullets": [
            f"Business model durability and competitive positioning differentiate {company} from peers.",
            "Compare franchise quality, not just financial metrics, when assessing relative attractiveness.",
        ],
    }


def _financial_comparison(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["financial_comparison"],
        "bullets": [
            "Growth, margins, return on capital, and cash conversion are the primary financial comparison axes.",
            "Normalize for one-offs before drawing conclusions on relative financial strength.",
        ],
    }


def _competitive_position(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["competitive_position"],
        "bullets": [
            f"{company}'s competitive position depends on pricing power, share trends, and capital allocation discipline.",
            "Peer leadership is sustained only when advantages compound over time.",
        ],
    }


def _primary_risks(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["primary_risks"],
        "bullets": _key_uncertainties(pack, company)[:4],
    }


def _probability(pack: dict[str, Any], company: str) -> dict[str, Any]:
    return {
        "label": SECTION_LABELS["probability"],
        "bullets": [
            "Institutional investing is probabilistic — risks should be weighted by likelihood and impact.",
            f"For {company}, the highest-probability risks are those tied to earnings power and competitive dynamics.",
        ],
    }


_SECTION_BUILDERS = {
    "executive_summary": lambda p, c, t, a: _executive_summary(p, c),
    "what_matters_most": lambda p, c, t, a: {
        "label": SECTION_LABELS["what_matters_most"],
        "bullets": _what_matters_most_bullets(p, c),
        "guidance": "If I'm a portfolio manager, what should I focus on?",
    },
    "investment_debate": lambda p, c, t, a: _investment_debate_narrative(p, c),
    "supporting_evidence": lambda p, c, t, a: {
        "label": SECTION_LABELS["supporting_evidence"],
        "observations": _evidence_observations(a),
        "min_observations": EVIDENCE_OBSERVATIONS_MIN,
        "assertion_backed": bool(a),
    },
    "key_uncertainties": lambda p, c, t, a: {
        "label": SECTION_LABELS["key_uncertainties"],
        "items": _key_uncertainties(p, c),
    },
    "research_conclusion": lambda p, c, t, a: _research_conclusion(p, c),
    "questions_before_you_decide": lambda p, c, t, a: {
        "label": SECTION_LABELS["questions_before_you_decide"],
        "questions": _questions_before_you_decide(c, t)[:QUESTIONS_MAX],
        "min_questions": QUESTIONS_MIN,
    },
    "what_changed": lambda p, c, t, a: _what_changed(p, c),
    "what_didnt_change": lambda p, c, t, a: _what_didnt_change(p, c),
    "market_implications": lambda p, c, t, a: _market_implications(p, c),
    "monitoring": lambda p, c, t, a: _monitoring(p, c),
    "current_expectations": lambda p, c, t, a: _current_expectations(p, c),
    "historical_context": lambda p, c, t, a: _historical_context(p, c),
    "business_comparison": lambda p, c, t, a: _business_comparison(p, c),
    "financial_comparison": lambda p, c, t, a: _financial_comparison(p, c),
    "competitive_position": lambda p, c, t, a: _competitive_position(p, c),
    "primary_risks": lambda p, c, t, a: _primary_risks(p, c),
    "probability": lambda p, c, t, a: _probability(p, c),
    "trade_offs": lambda p, c, t, a: {
        "label": SECTION_LABELS["trade_offs"],
        "items": _key_uncertainties(p, c),
    },
}


def assemble_writing_sections(
    pack: dict[str, Any],
    *,
    company: str,
    ticker: str | None = None,
    template_id: str | None = None,
    section_order: list[str] | None = None,
) -> dict[str, Any]:
    """Build template-aware writing hierarchy from knowledge + constitution packs."""
    assertions = _supported_assertions(pack)
    order = section_order or list(template_sections(template_id or DEFAULT_TEMPLATE))

    sections: dict[str, Any] = {}
    for key in order:
        builder = _SECTION_BUILDERS.get(key)
        if builder:
            sections[key] = builder(pack, company, ticker, assertions)

    return sections


def infer_answer_length(query: str) -> str:
    q = (query or "").lower()
    if any(w in q for w in ("deep dive", "comprehensive", "full research", "detailed")):
        return "deep_research"
    if any(w in q for w in ("compare", "explain", "analyze", "analyse", "should i", "thesis", "invest")):
        return "research_request"
    return "simple_question"
