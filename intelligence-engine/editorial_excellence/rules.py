"""Append-only editorial rules — improve writing, never reasoning."""

from __future__ import annotations

from typing import Any

# Rules are append-only. Never modify reasoning architecture.
EDITORIAL_RULES: tuple[dict[str, Any], ...] = (
    {"id": "ER-001", "rule": "Executive Summary must explain why this matters.", "category": "executive_summary"},
    {"id": "ER-002", "rule": "Never summarize — explain meaning.", "category": "philosophy"},
    {"id": "ER-003", "rule": "Never list facts without connecting them.", "category": "philosophy"},
    {"id": "ER-004", "rule": "Never report numbers without explaining implications.", "category": "philosophy"},
    {"id": "ER-005", "rule": "The Investment Debate must identify what investors disagree about.", "category": "investment_debate"},
    {"id": "ER-006", "rule": "What Matters Most must answer: if I'm a PM, what should I focus on?", "category": "prioritization"},
    {"id": "ER-014", "rule": "Never classify without reasoning.", "category": "language"},
    {"id": "ER-021", "rule": "Evidence bullets must vary sentence structure.", "category": "evidence"},
    {"id": "ER-022", "rule": "Never begin more than one consecutive bullet with the same phrase.", "category": "evidence"},
    {"id": "ER-034", "rule": "Research Conclusion must identify remaining uncertainty.", "category": "conclusion"},
    {"id": "ER-035", "rule": "Research Conclusion never recommends Buy, Sell, or Hold.", "category": "conclusion"},
    {"id": "ER-040", "rule": "Key Uncertainties must explain what would change the view.", "category": "uncertainty"},
    {"id": "ER-041", "rule": "Questions Before You Decide must improve investor thinking.", "category": "questions"},
    {"id": "ER-050", "rule": "Rotate openings, evidence phrasing, transitions, and conclusions.", "category": "diversity"},
    {"id": "ER-051", "rule": "Maintain institutional tone without becoming formulaic.", "category": "diversity"},
    {"id": "ER-060", "rule": "Avoid marketing language, hype, and recommendation leakage.", "category": "tone"},
    {"id": "ER-061", "rule": "Prefer: The central investment debate, Current evidence indicates, The primary uncertainty.", "category": "style"},
    {"id": "ER-070", "rule": "Never answer the literal question only — answer the underlying investment question.", "category": "principles"},
    {"id": "ER-071", "rule": "Never explain facts without implications.", "category": "principles"},
    {"id": "ER-072", "rule": "Never present valuation without expectations.", "category": "principles"},
    {"id": "ER-073", "rule": "Never discuss risk without monitoring.", "category": "principles"},
    {"id": "ER-074", "rule": "Never conclude without uncertainty.", "category": "principles"},
    {"id": "ER-075", "rule": "Never summarize without teaching.", "category": "principles"},
)


def list_rules(*, category: str | None = None) -> list[dict[str, Any]]:
    if not category:
        return list(EDITORIAL_RULES)
    return [r for r in EDITORIAL_RULES if r.get("category") == category]


def rule_count() -> int:
    return len(EDITORIAL_RULES)
