"""Universal institutional questions — 10 domains × 10 questions.

Company-agnostic templates use {company} placeholder where applicable.
"""

from __future__ import annotations

from typing import Any

from institutional_investor_curriculum.schema import DECISION_DOMAINS, DOMAIN_EDITORIAL_OBJECTIVES

# Each entry: (domain, template, uses_company)
_UNIVERSAL_TEMPLATES: tuple[tuple[str, str, bool], ...] = (
    # Domain 1 — Idea Generation
    ("idea_generation", "Does {company} deserve research today?", True),
    ("idea_generation", "Why is {company} interesting?", True),
    ("idea_generation", "What changed recently at {company}?", True),
    ("idea_generation", "Which sector dynamics make {company} worth attention?", True),
    ("idea_generation", "What would make you initiate coverage on {company}?", True),
    ("idea_generation", "What catalyst could bring {company} onto a research desk?", True),
    ("idea_generation", "Is {company} under-researched relative to its importance?", True),
    ("idea_generation", "What would disqualify {company} from further research?", True),
    ("idea_generation", "How does {company} rank against other research priorities?", True),
    ("idea_generation", "What single fact would make {company} immediately interesting?", True),
    # Domain 2 — Business Understanding
    ("business_understanding", "How does {company} make money?", True),
    ("business_understanding", "Why do customers stay with {company}?", True),
    ("business_understanding", "What competitive advantages exist at {company}?", True),
    ("business_understanding", "What is changing in {company}'s business model?", True),
    ("business_understanding", "Which business segment creates the most value at {company}?", True),
    ("business_understanding", "What are the primary revenue drivers for {company}?", True),
    ("business_understanding", "How capital-intensive is {company}'s business model?", True),
    ("business_understanding", "What would break {company}'s business model?", True),
    ("business_understanding", "How does {company} create value for customers?", True),
    ("business_understanding", "Which part of {company}'s business is most misunderstood?", True),
    # Domain 3 — Competitive Advantage
    ("competitive_advantage", "Does {company} possess a durable moat?", True),
    ("competitive_advantage", "Why is {company}'s moat sustainable?", True),
    ("competitive_advantage", "Can competitors replicate {company}'s business?", True),
    ("competitive_advantage", "Where is competitive pressure increasing for {company}?", True),
    ("competitive_advantage", "How has {company}'s competitive position evolved?", True),
    ("competitive_advantage", "What would it cost a competitor to replicate {company}?", True),
    ("competitive_advantage", "Where is {company}'s moat widening or narrowing?", True),
    ("competitive_advantage", "What substitutes threaten {company}?", True),
    ("competitive_advantage", "How does {company}'s advantage translate to returns?", True),
    ("competitive_advantage", "What would prove {company}'s moat has eroded?", True),
    # Domain 4 — Management Quality
    ("management_quality", "Can {company} management be trusted?", True),
    ("management_quality", "Has {company}'s capital allocation created value?", True),
    ("management_quality", "Has {company} guidance historically been accurate?", True),
    ("management_quality", "What decisions strengthened {company}'s business?", True),
    ("management_quality", "Where has {company} management underperformed?", True),
    ("management_quality", "How does {company} management communicate with shareholders?", True),
    ("management_quality", "Has {company} management made value-destructive decisions?", True),
    ("management_quality", "How does {company} balance growth and returns?", True),
    ("management_quality", "Is {company} management's incentive structure aligned?", True),
    ("management_quality", "What would indicate a management quality inflection at {company}?", True),
    # Domain 5 — Financial Quality
    ("financial_quality", "Can {company}'s earnings be trusted?", True),
    ("financial_quality", "How strong is {company}'s cash generation?", True),
    ("financial_quality", "Is {company}'s leverage appropriate?", True),
    ("financial_quality", "Are {company}'s margins sustainable?", True),
    ("financial_quality", "What financial trends matter most for {company}?", True),
    ("financial_quality", "How cyclical are {company}'s earnings?", True),
    ("financial_quality", "What is the quality of {company}'s revenue recognition?", True),
    ("financial_quality", "How does {company}'s free cash flow compare to reported earnings?", True),
    ("financial_quality", "What balance sheet risks exist at {company}?", True),
    ("financial_quality", "Which financial metric best captures {company}'s health?", True),
    # Domain 6 — Valuation
    ("valuation", "What assumptions are priced into {company}'s valuation?", True),
    ("valuation", "Does {company}'s valuation reflect business quality?", True),
    ("valuation", "What could justify a rerating of {company}?", True),
    ("valuation", "What could compress {company}'s multiples?", True),
    ("valuation", "Which valuation metrics matter most for {company}?", True),
    ("valuation", "How does {company}'s valuation compare to history?", True),
    ("valuation", "What growth is implied by {company}'s current price?", True),
    ("valuation", "What would make {company} look expensive in hindsight?", True),
    ("valuation", "What would make {company} look cheap in hindsight?", True),
    ("valuation", "Which peer comparison is most relevant for {company}'s valuation?", True),
    # Domain 7 — Investment Debate
    ("investment_debate", "Why do bulls like {company}?", True),
    ("investment_debate", "Why are bears cautious on {company}?", True),
    ("investment_debate", "What is the market missing about {company}?", True),
    ("investment_debate", "Which assumptions about {company} are controversial?", True),
    ("investment_debate", "What evidence would change the debate on {company}?", True),
    ("investment_debate", "What is the bull case for {company}?", True),
    ("investment_debate", "What is the bear case for {company}?", True),
    ("investment_debate", "Where is consensus wrong on {company}?", True),
    ("investment_debate", "What data would resolve the {company} debate?", True),
    ("investment_debate", "How balanced is current market sentiment on {company}?", True),
    # Domain 8 — Portfolio Construction
    ("portfolio_construction", "What role should {company} play in a portfolio?", True),
    ("portfolio_construction", "Which holdings overlap with {company}?", True),
    ("portfolio_construction", "Which alternatives exist to {company}?", True),
    ("portfolio_construction", "Would {company} improve diversification?", True),
    ("portfolio_construction", "What is the opportunity cost of owning {company}?", True),
    ("portfolio_construction", "How correlated is {company} with typical portfolio holdings?", True),
    ("portfolio_construction", "What macro exposure does {company} introduce?", True),
    ("portfolio_construction", "Is {company} a core or satellite position candidate?", True),
    ("portfolio_construction", "What position size would {company} warrant and why?", True),
    ("portfolio_construction", "What would you sell to fund a {company} position?", True),
    # Domain 9 — Monitoring
    ("monitoring", "What should investors monitor at {company}?", True),
    ("monitoring", "Which KPIs matter most for {company}?", True),
    ("monitoring", "What events would strengthen the thesis on {company}?", True),
    ("monitoring", "What events would weaken the thesis on {company}?", True),
    ("monitoring", "When should {company} research be updated?", True),
    ("monitoring", "What quarterly metrics should be tracked for {company}?", True),
    ("monitoring", "What external signals matter for {company}?", True),
    ("monitoring", "How often should {company} research be refreshed?", True),
    ("monitoring", "What would trigger a full thesis review on {company}?", True),
    ("monitoring", "What are early warning signs for {company}?", True),
    # Domain 10 — Decision Review
    ("decision_review", "What changed since research on {company} began?", True),
    ("decision_review", "Which assumptions about {company} proved wrong?", True),
    ("decision_review", "Which assumptions about {company} proved correct?", True),
    ("decision_review", "Would today's evidence change the thesis on {company}?", True),
    ("decision_review", "What lessons were learned from {company}?", True),
    ("decision_review", "What did we get wrong about {company}?", True),
    ("decision_review", "What did we get right about {company}?", True),
    ("decision_review", "How has the investment case for {company} evolved?", True),
    ("decision_review", "What would we do differently researching {company} again?", True),
    ("decision_review", "What institutional lesson does {company} teach?", True),
)


def _build_universal_questions() -> tuple[dict[str, Any], ...]:
    assert len(_UNIVERSAL_TEMPLATES) == 100
    items: list[dict[str, Any]] = []
    domain_counts: dict[str, int] = {}

    for idx, (domain, template, uses_company) in enumerate(_UNIVERSAL_TEMPLATES, start=1):
        domain_num = DECISION_DOMAINS.index(domain) + 1
        q_in_domain = domain_counts.get(domain, 0) + 1
        domain_counts[domain] = q_in_domain

        items.append({
            "id": f"IICQ_{idx:03d}",
            "template": template,
            "question_universal": template.replace("{company}", "the company"),
            "domain": domain,
            "domain_number": domain_num,
            "question_in_domain": q_in_domain,
            "uses_company": uses_company,
            "editorial_objective": DOMAIN_EDITORIAL_OBJECTIVES[domain],
            "company_specific": False,
        })
    return tuple(items)


UNIVERSAL_QUESTIONS: tuple[dict[str, Any], ...] = _build_universal_questions()
