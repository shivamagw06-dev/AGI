"""PUB-01 templates — presentation layouts only; no analytical content generation."""

from __future__ import annotations

from typing import Any

from institutional_publishing.schema import DEFAULT_TEMPLATE_VERSION, LINEAGE_VIEW

TEMPLATES: dict[str, dict[str, Any]] = {
    "MorningBrief": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Morning Brief — {as_of_date}",
        "section_order": ("overview", "macro", "observations", "risk", "lineage"),
    },
    "EveningBrief": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Evening Brief — {as_of_date}",
        "section_order": ("overview", "observations", "risk", "lineage"),
    },
    "MarketWrap": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Market Wrap — {as_of_date}",
        "section_order": ("overview", "macro", "observations", "lineage"),
    },
    "MacroUpdate": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Macro Update — {as_of_date}",
        "section_order": ("macro", "observations", "lineage"),
    },
    "CompanyResearchNote": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "{ticker} — Company Research Note",
        "section_order": ("overview", "decision", "observations", "evidence", "lineage"),
    },
    "InvestmentSnapshot": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "{ticker} — Investment Snapshot",
        "section_order": ("overview", "decision", "evidence", "lineage"),
    },
    "DecisionUpdate": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "{ticker} — Decision Update",
        "section_order": ("decision", "observations", "lineage"),
    },
    "ObservationBulletin": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Observation Bulletin — {as_of_date}",
        "section_order": ("observations", "evidence", "lineage"),
    },
    "PortfolioReview": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Portfolio Review — {portfolio_id}",
        "section_order": ("overview", "decision", "risk", "policy", "lineage"),
    },
    "RiskSummary": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Risk Summary — {portfolio_id}",
        "section_order": ("risk", "lineage"),
    },
    "PolicyReview": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Policy Review — {portfolio_id}",
        "section_order": ("policy", "lineage"),
    },
    "AllocationChanges": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Allocation Changes — {portfolio_id}",
        "section_order": ("decision", "risk", "lineage"),
    },
    "InvestmentCommitteePack": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Investment Committee Pack — {as_of_date}",
        "section_order": ("committee", "decision", "risk", "policy", "lineage"),
    },
    "MeetingAgenda": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "IC Meeting Agenda — {as_of_date}",
        "section_order": ("committee", "decision", "lineage"),
    },
    "ResolutionSummary": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Resolution Summary — {as_of_date}",
        "section_order": ("committee", "lineage"),
    },
    "ActionRegister": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Action Register — {as_of_date}",
        "section_order": ("committee", "lineage"),
    },
    "WeeklyClientReport": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Weekly Client Report — {as_of_date}",
        "section_order": ("overview", "decision", "risk", "observations", "lineage"),
    },
    "MonthlyReview": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Monthly Review — {as_of_date}",
        "section_order": ("overview", "decision", "risk", "policy", "committee", "lineage"),
    },
    "QuarterlyLetter": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Quarterly Letter — {as_of_date}",
        "section_order": ("overview", "decision", "committee", "macro", "lineage"),
    },
    "MandateReport": {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": "Mandate Report — {portfolio_id}",
        "section_order": ("policy", "risk", "lineage"),
    },
}


def get_template(name: str) -> dict[str, Any]:
    tpl = TEMPLATES.get(name) or {
        "version": DEFAULT_TEMPLATE_VERSION,
        "title_pattern": name,
        "section_order": ("overview", "lineage"),
    }
    return {
        **tpl,
        "presentation_only": True,
        "controls_formatting_not_content": True,
        "lineage_view": list(LINEAGE_VIEW),
    }


def render_title(template_name: str, ctx: dict[str, Any]) -> str:
    tpl = get_template(template_name)
    pattern = str(tpl.get("title_pattern") or template_name)
    try:
        return pattern.format(**{k: (v or "—") for k, v in ctx.items()})
    except Exception:
        return pattern
