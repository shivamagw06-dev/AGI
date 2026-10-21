"""Phase 3.4 — Research Intelligence Engine schemas.

Institutional research workspace: structured memory, not summarization.
Never issues BUY/SELL. Does not modify Core. Ask unwired until Acceptance 100%.

Knowledge authority: Research Intelligence is the only Phase-3 layer allowed
to create new long-lived research memory; other layers consume it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

RI_VERSION = "3.4.0"
PROGRAMME = "Phase 3.4 — Research Intelligence Engine"
SPEC = "AGI-RESEARCH-INTELLIGENCE-3.4"
ASK_WIRED = True  # Phase 3.4.5 — wired via KUL provider only (Acceptance = 100%)
ASK_WIRED_VIA = "knowledge_unification.providers.research_intelligence"
RECOMMENDATION_POLICY = "observations_only_no_buy_sell"
KNOWLEDGE_AUTHORITY = "research_intelligence_only_long_lived_memory"


@dataclass
class ResearchPackage:
    ok: bool
    question: str
    entity: Optional[str] = None
    company: Optional[str] = None
    modules_used: list[str] = field(default_factory=list)
    executive_summary: str = ""
    whats_new: list[str] = field(default_factory=list)
    business_impact: str = ""
    financial_impact: str = ""
    industry_impact: str = ""
    investment_implications: str = ""
    evidence: Optional[dict[str, Any]] = None
    unknowns: list[str] = field(default_factory=list)
    monitoring_points: list[str] = field(default_factory=list)
    research_object: Optional[dict[str, Any]] = None
    annual_report: Optional[dict[str, Any]] = None
    transcript: Optional[dict[str, Any]] = None
    management: Optional[dict[str, Any]] = None
    guidance: Optional[dict[str, Any]] = None
    estimates: Optional[dict[str, Any]] = None
    events: Optional[dict[str, Any]] = None
    memory: Optional[dict[str, Any]] = None
    cross_document: Optional[dict[str, Any]] = None
    timeline: Optional[dict[str, Any]] = None
    quality: Optional[dict[str, Any]] = None
    knowledge_evolution: Optional[dict[str, Any]] = None
    deep_research: Optional[dict[str, Any]] = None
    confidence: float = 0.0
    fabricated: bool = False
    recommendation: None = None
    recommendation_policy: str = RECOMMENDATION_POLICY
    ask_wired: bool = ASK_WIRED
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recommendation"] = None
        d["summary"] = self.executive_summary or self.summary
        d["knowledge_authority"] = KNOWLEDGE_AUTHORITY
        return d
