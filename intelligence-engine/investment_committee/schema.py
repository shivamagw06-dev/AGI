"""Investment Committee Intelligence V1 — constants (not an engine)."""

PROGRAMME = "AGIB_INVESTMENT_COMMITTEE_INTELLIGENCE_V1"
PROGRAMME_SHORT = "ICI"
ICI_VERSION = "ici-v1.0.0"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"

ANALYST_ROLES = [
    "business",
    "financial",
    "valuation",
    "market",
    "sector",
    "macro",
    "risk",
    "management",
    "ownership",
]

VOTE_LABELS = {
    "Bullish": "Constructive",
    "Constructive": "Constructive",
    "Neutral": "Neutral",
    "Bearish": "Cautious",
    "Cautious": "Cautious",
    "Missing": "Abstain",
}

OBJECT_TYPES = [
    "CommitteeConsensus",
    "CommitteeConflict",
    "CommitteeQuestion",
    "CommitteeChallenge",
    "CommitteeVote",
    "CommitteeMinutes",
    "CommitteeDecision",
    "CommitteeAccuracy",
    "MinorityOpinion",
    "OpenEvidenceRequest",
]
