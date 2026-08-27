"""Run all extractors over document bundles → BusinessFact list."""

from __future__ import annotations

import re
from typing import Any

from business_intelligence.evidence import dedupe_facts, fact_from_match, make_fact
from business_intelligence.extractors.patterns import (
    CAPITAL_RULES,
    GOVERNANCE_RULES,
    GUIDANCE_RULES,
    OPPORTUNITY_RULES,
    PROFILE_RULES,
    SEGMENT_RULES,
    STRATEGY_RULES,
    apply_rules,
    extract_list_items,
    extract_risk_themes,
)
from business_intelligence.schema import (
    CAT_RISK,
    CAT_SEGMENT_ANALYSIS,
    CAT_SEGMENTS,
)


_SEGMENT_LIST_LEAD = re.compile(
    r"(?:verticals?|segments?|include|remained|were|are)\s+([A-Z][^.]{10,200})",
    re.I,
)
_RISK_LIST_LEAD = re.compile(
    r"(?:key\s+)?risks?\s+include\s+([^.]+)",
    re.I,
)


def _iter_chunks(bundles: list[dict[str, Any]]):
    for bundle in bundles:
        doc = bundle.get("document") or {}
        period = bundle.get("reporting_period") or doc.get("reporting_period")
        for chunk in bundle.get("chunks") or []:
            yield doc, chunk, period


def _facts_from_rules(
    *,
    rules,
    bundles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for doc, chunk, period in _iter_chunks(bundles):
        text = str(chunk.get("text") or "")
        for category, statement, match, hints in apply_rules(text, rules):
            facts.append(
                fact_from_match(
                    category=category,
                    statement=statement,
                    text=text,
                    match=match,
                    chunk=chunk,
                    document=doc,
                    reporting_period=period,
                    fkb_hints=list(hints),
                )
            )
    return facts


def extract_profile(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _facts_from_rules(rules=PROFILE_RULES, bundles=bundles)


def extract_segments(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = _facts_from_rules(rules=SEGMENT_RULES, bundles=bundles)
    # Atomic segment names from lists
    for doc, chunk, period in _iter_chunks(bundles):
        section = str(chunk.get("section") or "")
        if section not in {"BUSINESS_SEGMENTS", "MANAGEMENT_DISCUSSION", "STRATEGY", "OTHER", "TABLES"}:
            continue
        text = str(chunk.get("text") or "")
        for item in extract_list_items(text, _SEGMENT_LIST_LEAD):
            # Skip if looks like a full sentence fragment without a segment cue
            if len(item.split()) > 6:
                continue
            facts.append(
                make_fact(
                    category=CAT_SEGMENTS,
                    statement=f"Segment / vertical: {item}",
                    evidence=item,
                    page=chunk.get("page"),
                    section=chunk.get("section"),
                    heading=chunk.get("heading"),
                    document=doc.get("title") or doc.get("type"),
                    document_id=doc.get("document_id"),
                    document_type=doc.get("type"),
                    reporting_period=period,
                    chunk_id=chunk.get("chunk_id"),
                )
            )
        if re.search(r"versus\s+previous\s+year|year.?over.?year|yoy\s+change", text, re.I):
            facts.append(
                fact_from_match(
                    category=CAT_SEGMENT_ANALYSIS,
                    statement="Segment change versus previous year disclosed",
                    text=text,
                    match=re.search(r"versus\s+previous\s+year|year.?over.?year|yoy\s+change", text, re.I),
                    chunk=chunk,
                    document=doc,
                    reporting_period=period,
                )
            )
    return facts


def extract_strategy(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _facts_from_rules(rules=STRATEGY_RULES, bundles=bundles)


def extract_capital(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _facts_from_rules(rules=CAPITAL_RULES, bundles=bundles)


def extract_risks(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for doc, chunk, period in _iter_chunks(bundles):
        text = str(chunk.get("text") or "")
        section = str(chunk.get("section") or "")
        # Prefer RISK_FACTORS but allow disclosed risks elsewhere
        themes = extract_risk_themes(text)
        for label, match in themes:
            if section not in {"RISK_FACTORS", "MANAGEMENT_DISCUSSION", "OTHER", "NOTES", "STRATEGY"}:
                # Still allow if explicit risk wording nearby
                window = text[max(0, match.start() - 40) : match.end() + 40].lower()
                if "risk" not in window and "threat" not in window:
                    continue
            facts.append(
                fact_from_match(
                    category=CAT_RISK,
                    statement=f"Disclosed risk: {label}",
                    text=text,
                    match=match,
                    chunk=chunk,
                    document=doc,
                    reporting_period=period,
                )
            )
        for item in extract_list_items(text, _RISK_LIST_LEAD):
            facts.append(
                make_fact(
                    category=CAT_RISK,
                    statement=f"Disclosed risk: {item}",
                    evidence=item,
                    page=chunk.get("page"),
                    section=chunk.get("section"),
                    heading=chunk.get("heading"),
                    document=doc.get("title") or doc.get("type"),
                    document_id=doc.get("document_id"),
                    document_type=doc.get("type"),
                    reporting_period=period,
                    chunk_id=chunk.get("chunk_id"),
                )
            )
    return facts


def extract_opportunities(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _facts_from_rules(rules=OPPORTUNITY_RULES, bundles=bundles)


def extract_guidance(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _facts_from_rules(rules=GUIDANCE_RULES, bundles=bundles)


def extract_governance(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _facts_from_rules(rules=GOVERNANCE_RULES, bundles=bundles)


def extract_all_facts(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    facts.extend(extract_profile(bundles))
    facts.extend(extract_segments(bundles))
    facts.extend(extract_strategy(bundles))
    facts.extend(extract_capital(bundles))
    facts.extend(extract_risks(bundles))
    facts.extend(extract_opportunities(bundles))
    facts.extend(extract_guidance(bundles))
    facts.extend(extract_governance(bundles))
    return dedupe_facts(facts)
