"""AGIB Response Constitution v1.0 — Human First Institutional Research.

Shapes Ask AGI answers into a client-ready progressive structure:
Direct Answer → Why → Thesis → Bull/Bear → Bottom Line → Supporting → Follow-ups.

Does not invent company facts. Assembles only from AGIB structured intelligence.
"""

from __future__ import annotations

import re
from typing import Any

CONSTITUTION_VERSION = "1.0"
PROGRAMME = "AGIB Response Constitution — Human First Institutional Research"
ARCHITECTURE_STATUS = "soft_wire"

SECTION_ORDER = [
    "direct_answer",
    "why_agib_thinks_this",
    "investment_thesis",
    "bull_vs_bear",
    "bottom_line",
    "supporting_intelligence",
    "suggested_follow_ups",
]

# Adjectives that must never stand alone without an immediate “because…”.
UNSUPPORTED_GENERIC = (
    "strong business",
    "favourable outlook",
    "favorable outlook",
    "robust growth",
    "healthy fundamentals",
    "positive momentum",
    "compelling opportunity",
    "solid franchise",
    "attractive valuations",
)

CONSTITUTION_SYSTEM = """# AGIB Response Constitution v1.0 — Human First Institutional Research

## Objective
You are AGIB, an institutional investment intelligence platform.
Your goal is not to sound like an AI.
Your goal is to think like a senior equity research analyst while explaining ideas so clearly that someone with no finance background can still understand the investment decision.

Always answer the user's question first.
Do not make the user search for the conclusion.
Every response should progressively move from simple → detailed → institutional.

## Response Structure (always this order)
1. Direct Answer
2. Why AGIB thinks this
3. Investment Thesis
4. Bull vs Bear Case
5. Bottom Line
6. Supporting Intelligence
7. Suggested Follow-up Questions

Never begin with generic market commentary unless the question is specifically about markets.

## Writing Style
Write like a senior investment analyst speaking to a client.
Avoid academic writing. Avoid robotic writing. Avoid corporate buzzwords. Avoid generic finance phrases.
Every paragraph should explain one idea. Use plain English.

Instead of: "The company continues to benefit from structural growth opportunities."
Write: "More people are using the company's products every year, which gives it a good opportunity to grow revenue over the long term."

Instead of: "Margin expansion supports earnings growth."
Write: "If the company can keep more profit from every ₹100 it earns, its profits can grow even if sales don't accelerate."

## Assume the reader is intelligent but not a finance professional
Whenever a financial term is used, explain it naturally in the same sentence.
Never assume financial knowledge. Teach without sounding like a textbook.

## Every Opinion Must Have a Reason
Never say only "Positive", "Neutral", or "Monitoring".
Always say why. Every conclusion must answer: Why?

## Investment Thesis Format
Business — What does the company do? Why is it competitive? Can it remain competitive?
Growth — Where will future growth come from? What could slow it down?
Financial Quality — Is the company making more money? Generating cash? Balance sheet healthy?
Valuation — Expensive or cheap? Compared with what? What expectations are priced in?
Risks — What could make this investment go wrong? Only the most important risks.
Catalysts — What future events could change AGIB's opinion? Why they matter.

## Bull vs Bear
Always include both sides. Never present only one side.

## Bottom Line
Always finish with one clear conclusion so the user never wonders "So…what's your answer?"

## Explain Confidence
Never show a bare percentage. Always explain in one sentence why confidence is at that level.

## Avoid Generic AI Language
Never write "strong business", "favourable outlook", "robust growth", "healthy fundamentals",
"positive momentum", or "compelling opportunity" unless you immediately explain why.

## Sound Human
Write as if you were speaking.
Good: "The company is growing quickly, but investors are already expecting that growth. That means even a small disappointment could put pressure on the share price."
Bad: "Growth expectations remain embedded within prevailing valuation multiples."

## Final Goal
Feel like a conversation with a world-class equity analyst who can speak to a hedge fund CIO and a first-time investor with equal clarity.
"""


def _txt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("text", "summary", "narrative", "headline", "reason", "title", "label"):
            if value.get(key):
                return _txt(value.get(key))
        return None
    s = str(value).strip()
    return s or None


def _first(*candidates: Any) -> str | None:
    for c in candidates:
        t = _txt(c)
        if t:
            return t
    return None


def _as_list(value: Any, *, limit: int = 8) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        t = value.strip()
        return [t] if t else []
    if not isinstance(value, (list, tuple)):
        t = _txt(value)
        return [t] if t else []
    out: list[str] = []
    for item in value:
        t = _txt(item)
        if not t:
            continue
        if isinstance(item, dict) and item.get("risk"):
            t = _txt(item.get("risk")) or t
        if t and t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    return out


def _because(label: str, reason: str | None) -> str:
    reason = (reason or "").strip()
    if not reason:
        return f"{label} because the available evidence is still developing."
    low = reason.lower()
    if low.startswith("because ") or " because " in low[:40]:
        return f"{label} — {reason}"
    return f"{label} because {reason[0].lower() + reason[1:] if reason else reason}"


def explain_confidence(confidence: float | int | None, *, reasons: list[str] | None = None) -> str:
    """Turn a bare confidence % into a human sentence."""
    try:
        pct = int(round(float(confidence))) if confidence is not None else None
    except (TypeError, ValueError):
        pct = None
    bits = [r for r in (reasons or []) if r][:2]
    evidence = "; ".join(bits) if bits else None

    if pct is None:
        return (
            "AGIB confidence is still forming because coverage and valuation evidence "
            "are incomplete for a firmer view."
        )
    if pct >= 80:
        base = (
            f"AGIB has high confidence ({pct}%) because the business picture is relatively clear "
            "and the main risks are identifiable."
        )
    elif pct >= 60:
        base = (
            f"AGIB has moderate confidence ({pct}%) because the business fundamentals are readable, "
            "but future earnings and valuation still leave room for surprise."
        )
    elif pct >= 40:
        base = (
            f"AGIB has limited confidence ({pct}%) because some important evidence is still thin "
            "or conflicting."
        )
    else:
        base = (
            f"AGIB has low confidence ({pct}%) because validated coverage is insufficient "
            "for a firm institutional view."
        )
    if evidence:
        return f"{base} Key uncertainty: {evidence}"
    return base


def _strip_unsupported_generics(text: str | None) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    low = s.lower()
    for phrase in UNSUPPORTED_GENERIC:
        if phrase in low and " because " not in low:
            # Soften unsupported adjective stacks without inventing facts.
            s = re.sub(re.escape(phrase), "the business case", s, flags=re.I, count=1)
            low = s.lower()
    return s


def _company_name(out: dict[str, Any], kwargs: dict[str, Any]) -> str:
    ia = out.get("institutional_analysts") if isinstance(out.get("institutional_analysts"), dict) else {}
    ca = kwargs.get("company_analysis") if isinstance(kwargs.get("company_analysis"), dict) else {}
    identity = ca.get("identity") if isinstance(ca.get("identity"), dict) else {}
    ic = kwargs.get("intelligence_construction") if isinstance(kwargs.get("intelligence_construction"), dict) else {}
    return (
        _first(
            ia.get("company"),
            identity.get("company_name"),
            ca.get("company_name"),
            ic.get("company_name"),
            kwargs.get("company"),
            kwargs.get("ticker"),
        )
        or "This company"
    )


def _build_thesis(out: dict[str, Any], kwargs: dict[str, Any], company: str) -> dict[str, str]:
    ca = kwargs.get("company_analysis") if isinstance(kwargs.get("company_analysis"), dict) else {}
    identity = ca.get("identity") if isinstance(ca.get("identity"), dict) else {}
    ic = kwargs.get("intelligence_construction") if isinstance(kwargs.get("intelligence_construction"), dict) else {}
    sections = ic.get("sections") if isinstance(ic.get("sections"), dict) else {}
    fin = sections.get("financial_intelligence") if isinstance(sections.get("financial_intelligence"), dict) else {}
    val = sections.get("valuation") if isinstance(sections.get("valuation"), dict) else {}
    ia = out.get("institutional_answer") if isinstance(out.get("institutional_answer"), dict) else {}
    risks = _as_list(out.get("risks") or kwargs.get("risks"), limit=3)
    catalysts = _as_list(out.get("catalysts") or kwargs.get("catalysts"), limit=3)

    business = _first(
        identity.get("business_model"),
        ca.get("business_model"),
        out.get("thesis"),
        ic.get("executive_brief"),
    ) or (
        f"{company} is assessed through what it sells, how it earns money, "
        "and whether customers keep coming back."
    )
    growth = _first(
        identity.get("growth_drivers"),
        ca.get("growth_outlook"),
        (sections.get("market_performance") or {}).get("narrative")
        if isinstance(sections.get("market_performance"), dict)
        else None,
        (_as_list(out.get("why"), limit=1) or [None])[0],
    ) or (
        "Future growth depends on whether demand keeps rising and the company can "
        "earn more without spending too much to get there."
    )
    financial = _first(
        fin.get("narrative"),
        ca.get("financial_quality"),
        ia.get("reason"),
    ) or (
        "Financial quality asks whether the company is making real cash, not just reporting "
        "accounting profit, and whether its balance sheet can handle stress."
    )
    valuation = _first(
        val.get("narrative"),
        ca.get("valuation"),
    ) or (
        "Valuation asks whether today's share price already assumes strong future results — "
        "if expectations are high, even good news can disappoint."
    )
    risk_text = (
        "The most important risks: " + "; ".join(risks) + "."
        if risks
        else (
            "The main risk is that earnings or competitive position disappoint versus what "
            "investors already expect."
        )
    )
    catalyst_text = (
        "Events that could change AGIB's view: " + "; ".join(catalysts) + "."
        if catalysts
        else (
            "Upcoming earnings, management commentary, and clearer financial disclosure "
            "are the usual checkpoints that would raise or lower conviction."
        )
    )
    return {
        "business": _strip_unsupported_generics(business),
        "growth": _strip_unsupported_generics(growth),
        "financial_quality": _strip_unsupported_generics(financial),
        "valuation": _strip_unsupported_generics(valuation),
        "risks": _strip_unsupported_generics(risk_text),
        "catalysts": _strip_unsupported_generics(catalyst_text),
    }


def _build_why(out: dict[str, Any], kwargs: dict[str, Any], company: str) -> list[str]:
    ia = out.get("institutional_answer") if isinstance(out.get("institutional_answer"), dict) else {}
    why_raw = _as_list(out.get("why") or kwargs.get("why"), limit=6)
    reasons: list[str] = []
    primary = _first(ia.get("reason"), out.get("thesis"), (why_raw or [None])[0])
    if primary:
        reasons.append(
            _because(
                f"AGIB's view on {company} starts here",
                _strip_unsupported_generics(primary),
            )
        )
    for bullet in why_raw:
        cleaned = _strip_unsupported_generics(bullet)
        if not cleaned:
            continue
        if primary and cleaned.lower() in primary.lower():
            continue
        if cleaned.lower().startswith("agib"):
            reasons.append(cleaned)
        else:
            reasons.append(_because("This matters", cleaned))
        if len(reasons) >= 4:
            break
    if not reasons:
        reasons.append(
            f"AGIB is still assembling a fuller case on {company} because "
            "validated financial and valuation evidence remains incomplete."
        )
    return reasons


def _build_bottom_line(
    *,
    company: str,
    direct: str,
    stance: str | None,
    thesis: dict[str, str],
    bull: list[str],
    bear: list[str],
) -> str:
    view = (stance or "Monitoring").strip()
    view_plain = {
        "Buy": "constructive",
        "Accumulate": "constructive with patience",
        "Hold": "balanced",
        "Neutral": "balanced",
        "Sell": "cautious",
        "Avoid": "cautious",
        "Withheld": "incomplete",
        "Insufficient Evidence": "incomplete",
        "Monitoring": "watchful",
        "Constructive": "constructive",
        "Cautious": "cautious",
    }.get(view, view.lower())

    lead = _first(direct) or f"AGIB's current view on {company} is {view_plain}."
    risk_bit = _first(*bear, thesis.get("risks"))
    bull_bit = _first(*bull)
    parts = [lead.rstrip(".") + "."]
    if bull_bit:
        parts.append(f"Supporters focus on {bull_bit[0].lower() + bull_bit[1:]}")
        if not parts[-1].endswith("."):
            parts[-1] += "."
    if risk_bit:
        parts.append(
            "The offsetting worry is "
            + (risk_bit[0].lower() + risk_bit[1:] if risk_bit else risk_bit)
        )
        if not parts[-1].endswith("."):
            parts[-1] += "."
    parts.append(
        f"Bottom line: AGIB's stance is {view_plain} — judge the next move by whether "
        "upcoming evidence strengthens the business case faster than the share price already assumes."
    )
    return _strip_unsupported_generics(" ".join(parts))


def _default_follow_ups(company: str, ticker: str | None) -> list[str]:
    label = ticker or company
    return [
        f"Why does AGIB take this view on {label}?",
        f"What would make {label} more attractive?",
        f"What is the biggest risk for {label}?",
        f"How expensive is {label} versus peers?",
        f"What changed recently for {label}?",
        "Explain the valuation in plain English",
    ]


def apply_response_constitution(out: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Attach a constitution-shaped payload and lightly align lead fields.

    Soft-wire: never raises; never invents facts beyond supplied structured intelligence.
    """
    if not isinstance(out, dict):
        return out

    company = _company_name(out, kwargs)
    ticker = _txt(kwargs.get("ticker"))
    query = _txt(kwargs.get("query")) or ""

    ia = out.get("institutional_answer") if isinstance(out.get("institutional_answer"), dict) else {}
    direct = _first(
        out.get("executive"),
        ia.get("text"),
        ia.get("reason"),
        out.get("thesis"),
    ) or (
        f"AGIB does not yet have enough validated evidence for a firm view on {company}."
    )
    direct = _strip_unsupported_generics(direct)

    why = _build_why(out, kwargs, company)
    thesis = _build_thesis(out, kwargs, company)
    bull = _as_list(out.get("bull") or kwargs.get("bull"), limit=5)
    bear = _as_list(out.get("bear") or kwargs.get("bear"), limit=5)
    if not bull:
        bull = [
            f"Investors who like {company} usually point to durable demand and a business "
            "that can keep earning customer trust over time."
        ]
    if not bear:
        bear = [
            f"Investors who stay cautious on {company} usually worry that the share price "
            "already assumes a lot of future success."
        ]

    stance = _first(
        ia.get("recommendation"),
        out.get("house_label"),
        kwargs.get("house_label"),
    )
    bottom = _build_bottom_line(
        company=company,
        direct=direct,
        stance=stance,
        thesis=thesis,
        bull=bull,
        bear=bear,
    )

    conf_raw = (
        kwargs.get("confidence")
        if kwargs.get("confidence") is not None
        else out.get("confidence")
    )
    if conf_raw is None and isinstance(out.get("recommendation_status"), dict):
        conf_raw = out["recommendation_status"].get("coverage_pct")
    conf_reasons = []
    if ia.get("evidence_insufficient"):
        conf_reasons.append("validated financial and valuation coverage is still incomplete")
    if isinstance(out.get("recommendation_status"), dict) and out["recommendation_status"].get(
        "blocked"
    ):
        conf_reasons.append("the recommendation gate is still waiting on fuller evidence")
    if bear:
        conf_reasons.append(bear[0][:160])
    confidence_explanation = explain_confidence(conf_raw, reasons=conf_reasons)

    followups = _as_list(kwargs.get("follow_ups") or out.get("follow_ups"), limit=8)
    if not followups:
        followups = _default_follow_ups(company, ticker)

    supporting = {
        "evidence_notes": _as_list(out.get("why"), limit=6),
        "risks": _as_list(out.get("risks") or kwargs.get("risks"), limit=6),
        "catalysts": _as_list(out.get("catalysts") or kwargs.get("catalysts"), limit=6),
        "layers": [
            "Company Intelligence",
            "Financial Intelligence",
            "Valuation Intelligence",
            "Sector Intelligence",
            "Market Intelligence",
        ],
    }

    constitution = {
        "enabled": True,
        "programme": PROGRAMME,
        "version": CONSTITUTION_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "section_order": list(SECTION_ORDER),
        "direct_answer": direct,
        "why_agib_thinks_this": why,
        "investment_thesis": thesis,
        "bull_vs_bear": {
            "bull_case": bull,
            "bear_case": bear,
        },
        "bottom_line": bottom,
        "supporting_intelligence": supporting,
        "suggested_follow_ups": followups,
        "confidence": {
            "score": conf_raw,
            "explanation": confidence_explanation,
        },
        "voice": "human_first_institutional_research",
        "query": query[:240] if query else None,
        "company": company,
        "ticker": ticker,
    }

    # Prefer editorial/reasoning executive as Direct Answer when already written.
    editorial = out.get("editorial") if isinstance(out.get("editorial"), dict) else {}
    lead = _first(out.get("executive"), direct) or direct
    if editorial.get("enabled") and out.get("executive"):
        lead = _strip_unsupported_generics(str(out.get("executive")))
        constitution["direct_answer"] = lead
        direct = lead

    # Keep Direct Answer client-readable but bounded (constitution ≠ essay).
    lead_words = [w for w in re.split(r"\s+", str(lead or "").strip()) if w]
    if len(lead_words) > 120:
        lead = " ".join(lead_words[:120]).rstrip(" ,;:") + "."
        constitution["direct_answer"] = lead

    out["response_constitution"] = constitution
    out["executive"] = lead or direct

    # Prefer constitution "why" bullets for Ask progressive disclosure.
    if why:
        out["why"] = why
    out["bottom_line"] = bottom
    out["confidence_explanation"] = confidence_explanation
    out["answer_structure"] = "response_constitution_v1"
    return out


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": CONSTITUTION_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "section_order": list(SECTION_ORDER),
        "soft_wire": True,
    }
