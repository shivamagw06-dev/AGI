"""AGI Causal Research Engine foundation."""

from causal_research_engine.adapters import from_cig_edge, from_ieri_relationship
from causal_research_engine.governance import transition_status
from causal_research_engine.schema import (
    CausalEvent,
    CausalRelationship,
    ContradictionGroup,
    EvidenceReference,
    FinancialImpact,
    OutcomeRecord,
    ScenarioResult,
    ThesisUpdateProposal,
)
from causal_research_engine.validation import validate_financial_impact, validate_relationship

__all__ = [
    "CausalEvent", "CausalRelationship", "ContradictionGroup", "EvidenceReference", "FinancialImpact",
    "OutcomeRecord", "ScenarioResult", "ThesisUpdateProposal",
    "from_cig_edge", "from_ieri_relationship", "transition_status",
    "validate_financial_impact", "validate_relationship",
]
