PROGRAMME = "AGIB_INVESTMENT_DECISION_ENGINE"
PROGRAMME_SHORT = "IDE"
IDE_VERSION = "ide-v1.0.0"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"

# Weighted scoring layers (sum = 100). Catalysts / probability / ER / decision are output layers.
LAYER_WEIGHTS = {
    "macro": 15,
    "industry": 15,
    "company_quality": 20,
    "financial_quality": 15,
    "management": 10,
    "valuation": 10,
    "market_expectations": 5,
    "technical": 5,
    "risk": 5,
}

LAYER_ORDER = [
    "macro",
    "industry",
    "company_quality",
    "financial_quality",
    "management",
    "valuation",
    "market_expectations",
    "technical",
    "risk",
    "catalysts",
    "probability",
    "expected_return",
    "decision",
]

LAYER_QUESTIONS = {
    "macro": "Is this the right macro environment to own this stock?",
    "industry": "Is the industry improving or deteriorating?",
    "company_quality": "Is this a high-quality business?",
    "financial_quality": "Is the business getting stronger?",
    "management": "Can management create shareholder wealth?",
    "valuation": "Is it attractive relative to quality and growth?",
    "market_expectations": "What is already priced into the stock?",
    "technical": "What are buyers and sellers doing?",
    "risk": "What can impair the thesis before the base case arrives?",
    "catalysts": "Why should this stock move?",
    "probability": "What is the probability distribution of outcomes?",
    "expected_return": "Does expected return compensate for identified risks?",
    "decision": "What is the institutional investment conclusion?",
}
