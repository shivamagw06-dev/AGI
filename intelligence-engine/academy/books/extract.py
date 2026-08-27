"""Heuristic extraction of concepts, formulas, frameworks — AGI-owned objects only."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from academy.books.classify import classify_academy
from academy.books.copyright import scrub_definition, scrub_example, scrub_explanation
from academy.books.schema import BookConcept, FormulaObject, FrameworkObject


_DEF_RE = re.compile(
    r"(?i)\b([A-Z][A-Za-z0-9 /\-]{2,60})\s+(?:is defined as|means|refers to|is)\s+(.{20,220})"
)
_FORMULA_LINE_RE = re.compile(
    r"(?i)\b(WACC|CAPM|DCF|ROE|ROCE|ROIC|FCF|NPV|IRR|EVA|PEG|EPS|EBITDA)\b[^\n]{0,80}[=:]([^\n]{3,120})"
)
_NAMED_FORMULAS = {
    "wacc": ("WACC", "r_e*E/V + r_d*(1-t)*D/V", {"r_e": "cost of equity", "r_d": "cost of debt", "E": "equity value", "D": "debt value", "V": "E+D", "t": "tax rate"}),
    "capm": ("CAPM", "r_f + beta*(r_m - r_f)", {"r_f": "risk-free rate", "beta": "systematic risk", "r_m": "market return"}),
    "roe": ("ROE", "Net Income / Equity", {"Net Income": "owners' earnings", "Equity": "book equity"}),
    "roa": ("ROA", "Net Income / Assets", {"Net Income": "earnings", "Assets": "total assets"}),
    "roic": ("ROIC", "NOPAT / Invested Capital", {"NOPAT": "net operating profit after tax", "Invested Capital": "operating capital"}),
    "roce": ("ROCE", "EBIT / Capital Employed", {"EBIT": "operating profit", "Capital Employed": "equity + interest-bearing debt"}),
    "fcf": ("Free Cash Flow", "CFO - Capex", {"CFO": "operating cash flow", "Capex": "maintenance/growth capex"}),
    "dcf": ("DCF", "Σ CF_t / (1+r)^t + TV/(1+r)^n", {"CF_t": "expected cash flow", "r": "discount rate", "TV": "terminal value"}),
    "terminal value": ("Terminal Value", "FCF_(n+1) / (r - g)", {"FCF_(n+1)": "steady-state FCF", "r": "discount rate", "g": "perpetual growth"}),
    "intrinsic value": ("Intrinsic Value", "Σ CF_t/(1+r)^t + TV/(1+r)^n", {"CF_t": "cash flow", "r": "discount rate", "TV": "terminal value"}),
    "dividend discount": ("Dividend Discount Model", "DPS_1 / (r - g)", {"DPS_1": "next dividend", "r": "required return", "g": "growth"}),
    "gordon": ("Gordon Growth", "DPS_1 / (r - g)", {"DPS_1": "next dividend", "r": "required return", "g": "growth"}),
    "economic profit": ("Economic Profit", "NOPAT - WACC * Capital", {"NOPAT": "after-tax operating profit", "WACC": "cost of capital", "Capital": "invested capital"}),
    "residual income": ("Residual Income", "NI - r_e * Equity", {"NI": "net income", "r_e": "cost of equity", "Equity": "book equity"}),
    "eva": ("EVA", "NOPAT - WACC * Capital", {"NOPAT": "after-tax operating profit", "WACC": "cost of capital"}),
    "nopat": ("NOPAT", "EBIT * (1 - t)", {"EBIT": "operating profit", "t": "tax rate"}),
}

_FRAMEWORK_HINTS = {
    "porter's five forces": ("porters_five_forces", "Porter's Five Forces", "competitive_structure"),
    "five forces": ("porters_five_forces", "Porter's Five Forces", "competitive_structure"),
    "swot": ("swot", "SWOT", "strategic_scan"),
    "economic moat": ("economic_moat", "Economic Moat", "durable_advantage"),
    "moat analysis": ("economic_moat", "Economic Moat", "durable_advantage"),
    "margin of safety": ("margin_of_safety", "Margin of Safety", "valuation_buffer"),
    "intrinsic value": ("intrinsic_value", "Intrinsic Value", "fundamental_worth"),
    "capital allocation": ("capital_allocation", "Capital Allocation", "reinvestment_payout"),
    "value investing": ("value_investing", "Value Investing", "price_vs_value"),
    "growth investing": ("growth_investing", "Growth Investing", "future_cash_compounding"),
    "quality investing": ("quality_investing", "Quality Investing", "durable_returns"),
    "business life cycle": ("business_life_cycle", "Business Life Cycle", "stage_analysis"),
    "competitive advantage": ("competitive_advantage", "Competitive Advantage", "returns_above_cost"),
    "narrative investing": ("narrative_investing", "Narrative Investing", "story_vs_numbers"),
    "risk analysis": ("risk_analysis", "Risk Analysis", "downside_mapping"),
    "scenario analysis": ("scenario_analysis", "Scenario Analysis", "alternate_states"),
    "sensitivity analysis": ("sensitivity_analysis", "Sensitivity Analysis", "assumption_impact"),
    "earnings quality": ("earnings_quality", "Earnings Quality", "cash_vs_accruals"),
}


def extract_from_text(
    *,
    book_id: str,
    text: str,
    chapter_title: str | None = None,
) -> dict[str, list]:
    concepts = _extract_concepts(book_id, text, chapter_title)
    formulas = _extract_formulas(book_id, text, chapter_title)
    frameworks = _extract_frameworks(book_id, text, chapter_title)
    return {"concepts": concepts, "formulas": formulas, "frameworks": frameworks}


def _cid(prefix: str, *parts: str) -> str:
    h = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "_", parts[0].lower()).strip("_")[:40]
    return f"{prefix}_{slug}_{h}"


def _extract_concepts(book_id: str, text: str, chapter: str | None) -> list[BookConcept]:
    out: list[BookConcept] = []
    seen: set[str] = set()
    for m in _DEF_RE.finditer(text or ""):
        title = m.group(1).strip(" :.-")
        body = m.group(2).strip().rstrip(".")
        if len(title) < 3 or title.lower() in seen:
            continue
        if title.lower() in {"this", "that", "there", "it", "chapter", "section"}:
            continue
        seen.add(title.lower())
        academy = classify_academy(f"{title} {body}")
        out.append(
            BookConcept(
                concept_id=_cid("bkc", title, book_id),
                title=title[:80],
                definition=scrub_definition(body),
                explanation=scrub_explanation(f"{title}: {body}"),
                academy=academy,
                source_book_id=book_id,
                source_chapter=chapter,
                confidence=0.62,
            )
        )
        if len(out) >= 40:
            break
    return out


def _extract_formulas(book_id: str, text: str, chapter: str | None) -> list[FormulaObject]:
    blob = (text or "").lower()
    out: list[FormulaObject] = []
    for key, (name, expr, variables) in _NAMED_FORMULAS.items():
        if key in blob or name.lower() in blob:
            out.append(
                FormulaObject(
                    formula_id=_cid("bkf", name, book_id),
                    name=name,
                    expression=expr,
                    explanation=scrub_explanation(f"Institutional formula for {name} used in investment analysis."),
                    variables=variables,
                    use_cases=[f"Evaluate {name} in company analysis"],
                    academy=classify_academy(name),
                    source_book_id=book_id,
                    source_chapter=chapter,
                    confidence=0.78,
                )
            )
    for m in _FORMULA_LINE_RE.finditer(text or ""):
        name = m.group(1).upper()
        expr = m.group(2).strip()
        if any(f.name.upper() == name for f in out):
            continue
        out.append(
            FormulaObject(
                formula_id=_cid("bkf", name, book_id, expr[:20]),
                name=name,
                expression=scrub_definition(expr)[:120],
                explanation=scrub_explanation(f"{name} relationship extracted as institutional formula object."),
                academy=classify_academy(name),
                source_book_id=book_id,
                source_chapter=chapter,
                confidence=0.7,
            )
        )
    return out[:24]


def _extract_frameworks(book_id: str, text: str, chapter: str | None) -> list[FrameworkObject]:
    blob = (text or "").lower()
    out: list[FrameworkObject] = []
    for hint, (fid, name, purpose) in _FRAMEWORK_HINTS.items():
        if hint in blob:
            out.append(
                FrameworkObject(
                    framework_id=f"bkfw_{fid}_{book_id}"[:64],
                    name=name,
                    purpose=scrub_explanation(purpose.replace("_", " ")),
                    inputs=["business context", "industry structure", "financial evidence"],
                    outputs=["structured judgment", "decision questions"],
                    decision_logic=[
                        "Map evidence to framework inputs",
                        "Identify constraints and competitive position",
                        "Translate into investment implications without quoting source text",
                    ],
                    applications=["company analysis", "sector comparison", "research writing"],
                    academy=classify_academy(name),
                    source_book_id=book_id,
                    source_chapter=chapter,
                    confidence=0.8,
                )
            )
    return out
