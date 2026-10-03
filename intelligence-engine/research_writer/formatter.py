"""Publication-ready formatting for the institutional research note."""

from __future__ import annotations

from typing import Any

from research_writer.language_quality import dedupe_paragraphs, scrub_leaks
from research_writer.schema import SECTION_ORDER


def format_report(
    *,
    report_type: str,
    company: str,
    ticker: str | None,
    query: str,
    sections: dict[str, Any],
    risks: list[dict[str, str]],
    scenarios: dict[str, Any],
    tables: list[dict[str, Any]],
    charts: list[dict[str, str]],
    citations: list[dict[str, str]],
    quality: dict[str, Any],
    immutable: dict[str, Any],
) -> dict[str, Any]:
    # Dedupe prose sections against each other (repetition detector)
    prose_keys = [k for k in SECTION_ORDER if isinstance(sections.get(k), str)]
    paras = [sections[k] for k in prose_keys if sections.get(k)]
    deduped = dedupe_paragraphs(paras)
    # Map back in order — if dropped, keep shorter unique residual
    used = set()
    clean_sections: dict[str, Any] = {}
    di = 0
    for k in prose_keys:
        original = scrub_leaks(sections.get(k) or "", limit=1200)
        if not original:
            continue
        if di < len(deduped) and deduped[di] and deduped[di] not in used:
            clean_sections[k] = deduped[di]
            used.add(deduped[di])
            di += 1
        elif original not in used:
            clean_sections[k] = original
            used.add(original)

    # Non-prose
    clean_sections["risk_register"] = risks
    clean_sections["scenarios"] = scenarios

    return {
        "title": f"{company} — Institutional Research Note",
        "report_type": report_type,
        "company": company,
        "ticker": ticker,
        "query": query,
        "voice": "Institutional Equity Research",
        "sections": clean_sections,
        "section_order": [k for k in SECTION_ORDER if k in clean_sections or k in {"risks", "scenarios"}],
        "tables": tables,
        "chart_recommendations": charts,
        "citations": citations,
        "quality": quality,
        # Pass-through immutable intelligence — never rewritten as new facts
        "intelligence_unchanged": immutable,
    }
