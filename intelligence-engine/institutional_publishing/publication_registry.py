"""PUB-01 Publication Registry — pluggable publication types (like UAG/CCI registries)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from institutional_publishing.schema import (
    DEFAULT_TEMPLATE_VERSION,
    PUBLICATION_TYPES,
    REQUIRED_SOURCES,
    TYPE_TO_CATEGORY,
)


@dataclass(frozen=True)
class PublicationRegistration:
    publication_type: str
    builder: str
    template: str
    category: str
    description: str = ""
    template_version: str = DEFAULT_TEMPLATE_VERSION
    required_sources: tuple[str, ...] = ()
    build: Optional[Callable[..., dict[str, Any]]] = field(default=None, compare=False, hash=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "publication_type": self.publication_type,
            "builder": self.builder,
            "template": self.template,
            "category": self.category,
            "description": self.description,
            "template_version": self.template_version,
            "required_sources": list(self.required_sources),
            "has_builder": self.build is not None,
        }


_REGISTRY: dict[str, PublicationRegistration] = {}


def reset_registry_for_tests() -> None:
    _REGISTRY.clear()
    bootstrap_default_registry()


def register_publication(
    publication_type: str,
    *,
    builder: str,
    template: str = "",
    category: str = "",
    description: str = "",
    template_version: str = DEFAULT_TEMPLATE_VERSION,
    required_sources: list[str] | tuple[str, ...] | None = None,
    build: Optional[Callable[..., dict[str, Any]]] = None,
) -> None:
    key = str(publication_type).strip()
    _REGISTRY[key] = PublicationRegistration(
        publication_type=key,
        builder=builder,
        template=template or key,
        category=category or TYPE_TO_CATEGORY.get(key, "market"),
        description=description,
        template_version=template_version,
        required_sources=tuple(required_sources or REQUIRED_SOURCES.get(key, ())),
        build=build,
    )


def get(publication_type: str) -> Optional[PublicationRegistration]:
    return _REGISTRY.get(str(publication_type).strip())


def all_publications() -> list[PublicationRegistration]:
    return list(_REGISTRY.values())


def catalog() -> list[dict[str, Any]]:
    return [r.to_dict() for r in sorted(_REGISTRY.values(), key=lambda x: x.publication_type)]


def types_by_category() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in all_publications():
        out.setdefault(r.category, []).append(r.publication_type)
    return out


def _default_build(ctx: dict[str, Any]) -> dict[str, Any]:
    """Marker — actual composition lives in builder.py using registry metadata."""
    return {"ok": True, "delegated": True, "context_keys": sorted(ctx.keys())}


def bootstrap_default_registry() -> None:
    if _REGISTRY:
        return
    descriptions = {
        "MorningBrief": "Market morning brief composed from observations, risk, macro",
        "EveningBrief": "Market evening brief",
        "MarketWrap": "End-of-day market wrap",
        "MacroUpdate": "Macro update composition",
        "CompanyResearchNote": "Company research note from decision + evidence + observation",
        "InvestmentSnapshot": "Compact investment snapshot",
        "DecisionUpdate": "Decision update bulletin",
        "ObservationBulletin": "Observation bulletin",
        "PortfolioReview": "Portfolio review from decision, risk, policy",
        "RiskSummary": "Portfolio risk summary",
        "PolicyReview": "Mandate / policy review",
        "AllocationChanges": "Allocation changes composition",
        "InvestmentCommitteePack": "Full IC pack",
        "MeetingAgenda": "Committee meeting agenda",
        "ResolutionSummary": "Committee resolution summary",
        "ActionRegister": "Committee action register",
        "WeeklyClientReport": "Weekly client report",
        "MonthlyReview": "Monthly review letter pack",
        "QuarterlyLetter": "Quarterly client letter",
        "MandateReport": "Mandate compliance report",
    }
    for ptype in PUBLICATION_TYPES:
        register_publication(
            ptype,
            builder=f"{ptype}_builder",
            template=ptype,
            category=TYPE_TO_CATEGORY.get(ptype, "market"),
            description=descriptions.get(ptype, ptype),
            required_sources=REQUIRED_SOURCES.get(ptype, ()),
            build=_default_build,
        )


bootstrap_default_registry()
