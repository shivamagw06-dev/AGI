"""Extended Module — Investing Philosophy & Market Structure Concepts.

Legitimate extensions of Module 8 (Market Concepts) and Module 6 (Capital
Allocation) covering the vocabulary of investment decision-making itself —
value vs. growth framing, behavioral finance, and market-efficiency
debates — which analysts and portfolio managers use constantly but which
were not individually enumerated in the Phase 2.6 brief's module lists.
"""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "market"

INVESTING_PHILOSOPHY_CONCEPTS: dict[str, ConceptCard] = {
    "value_investing": ConceptCard(
        "value_investing", M, "Value Investing",
        "An investment philosophy that seeks securities trading below their estimated intrinsic value, typically identified via low valuation multiples (P/E, P/B) relative to fundamentals.",
        business_meaning="Rests on the premise that markets can misprice securities in the short run due to sentiment, neglect, or temporary problems, and that price eventually converges toward intrinsic value.",
        interpretation="A statistically 'cheap' stock (low multiple) is not automatically a value opportunity — it may be a 'value trap' if the low multiple correctly reflects a genuinely deteriorating business.",
        related_concepts=("margin_of_safety", "growth_investing", "intrinsic_value"),
    ),
    "growth_investing": ConceptCard(
        "growth_investing", M, "Growth Investing",
        "An investment philosophy that prioritizes companies with above-average revenue/earnings growth prospects, typically accepting higher valuation multiples in exchange for that growth.",
        business_meaning="Rests on the premise that a business compounding earnings at a high rate for many years can justify (and grow into) a valuation that looks expensive on current-year metrics alone.",
        interpretation="Growth investing's biggest risk is paying for growth that doesn't materialize or doesn't persist as long as assumed — multiple compression on a growth disappointment can be severe.",
        related_concepts=("value_investing", "peg", "terminal_growth"),
    ),
    "margin_of_safety": ConceptCard(
        "margin_of_safety", M, "Margin of Safety",
        "Buying a security at a meaningful discount to a conservative estimate of its intrinsic value, to protect against errors in analysis or unforeseen adverse events.",
        business_meaning="A core risk-management principle: the larger the gap between price paid and estimated value, the more room for error before the investment actually loses money.",
        interpretation="Margin of safety is fundamentally about acknowledging the analyst's own uncertainty — it does not eliminate the risk of being wrong, but it reduces the cost of being wrong.",
        related_concepts=("value_investing", "intrinsic_value"),
    ),
    "intrinsic_value": ConceptCard(
        "intrinsic_value", M, "Intrinsic Value",
        "An estimate of a company's true underlying worth, based on its fundamentals (cash flow generation, assets, growth prospects) rather than its current market price.",
        business_meaning="The anchor against which 'cheap' or 'expensive' is judged — market price and intrinsic value can diverge for extended periods before eventually converging.",
        interpretation="Intrinsic value is always an estimate with a range of uncertainty, not a single precise number — sound analysis focuses on a reasonable range and the key assumptions driving it, not false precision.",
        related_concepts=("dcf", "margin_of_safety", "value_investing"),
    ),
    "circle_of_competence": ConceptCard(
        "circle_of_competence", M, "Circle of Competence",
        "The principle of investing only within areas a person genuinely understands well enough to judge with confidence, rather than across every possible opportunity.",
        business_meaning="Acknowledges that no investor can deeply understand every industry — staying within one's circle reduces the risk of missing crucial, non-obvious risks in an unfamiliar business model.",
        interpretation="The size of one's circle matters less than accurately knowing its boundaries — the biggest risk is misjudging what one actually understands.",
        related_concepts=("margin_of_safety", "value_investing"),
    ),
    "mean_reversion": ConceptCard(
        "mean_reversion", M, "Mean Reversion",
        "The tendency for a metric (a valuation multiple, a margin, a return) that has moved unusually far from its long-run average to eventually move back toward that average.",
        business_meaning="Applied to valuation, it underlies the idea that abnormally high or low multiples, margins, or returns tend to normalize over time as competitive forces or market sentiment shift.",
        interpretation="Mean reversion is a probabilistic tendency, not a guarantee — a genuine structural change (a new moat, a permanently altered cost structure) can prevent reversion to an old 'mean' that no longer applies.",
        related_concepts=("momentum", "efficient_market_hypothesis"),
    ),
    "momentum": ConceptCard(
        "momentum", M, "Momentum (Investing)",
        "An investment approach/factor based on the empirical observation that securities which have recently performed well tend to continue performing well over the following months, and vice versa.",
        business_meaning="One of the most persistent, well-documented factors in academic finance, seemingly in tension with mean reversion — the two operate over different time horizons and are driven by different mechanisms (underreaction/trend-following vs. long-run fundamentals).",
        interpretation="Momentum strategies are vulnerable to sharp, sudden reversals ('momentum crashes'), particularly when a crowded trade unwinds quickly.",
        related_concepts=("mean_reversion", "efficient_market_hypothesis"),
    ),
    "efficient_market_hypothesis": ConceptCard(
        "efficient_market_hypothesis", M, "Efficient Market Hypothesis (EMH)",
        "A theory holding that asset prices fully reflect all available information at any given time, making it impossible to consistently 'beat the market' through analysis alone.",
        business_meaning="Comes in weak, semi-strong, and strong forms depending on what information is assumed to already be reflected in price (past prices only; all public information; all information including private/insider).",
        interpretation="The persistence of documented factors like value and momentum, and the existence of some long-term successful active investors, are frequently cited as evidence against the strongest forms of EMH — but market efficiency in most conditions still makes consistent outperformance genuinely difficult.",
        related_concepts=("behavioral_finance", "momentum", "mean_reversion"),
    ),
    "behavioral_finance": ConceptCard(
        "behavioral_finance", M, "Behavioral Finance",
        "A field studying how psychological biases (overconfidence, loss aversion, herding, anchoring, recency bias) cause investors to deviate from purely rational decision-making, and how this affects asset prices.",
        business_meaning="Explains market phenomena — bubbles, panics, momentum, post-earnings drift — that pure rational-expectations models struggle to account for.",
        interpretation="Awareness of one's own behavioral biases (e.g. anchoring on a purchase price, or herding into a crowded consensus trade) is itself a practical risk-management tool for any investor.",
        related_concepts=("efficient_market_hypothesis", "contrarian_investing"),
    ),
    "contrarian_investing": ConceptCard(
        "contrarian_investing", M, "Contrarian Investing",
        "An approach that deliberately takes positions opposite to prevailing market sentiment, on the premise that consensus views tend to be overextended (too optimistic near tops, too pessimistic near bottoms).",
        business_meaning="Requires independent, evidence-based conviction, since being early to a contrarian view can look identical to being simply wrong for an extended period.",
        interpretation="Genuine contrarian investing is grounded in fundamental analysis that differs from consensus, not merely in reflexively opposing whatever is popular.",
        related_concepts=("behavioral_finance", "margin_of_safety", "value_investing"),
    ),
    "total_addressable_market": ConceptCard(
        "total_addressable_market", M, "TAM (Total Addressable Market)",
        "The total revenue opportunity available if a company achieved 100% market share of the market it could theoretically serve.",
        business_meaning="Used to frame the ceiling on a growth company's long-run potential — a large TAM alone says nothing about whether the company can actually capture a meaningful share of it profitably.",
        interpretation="TAM estimates are frequently overstated by including adjacent markets a company cannot realistically serve — cross-check against Serviceable Addressable Market (SAM) and realistic achievable share.",
        related_concepts=("serviceable_addressable_market", "growth_capex"),
    ),
    "serviceable_addressable_market": ConceptCard(
        "serviceable_addressable_market", M, "SAM (Serviceable Addressable Market)",
        "The portion of the Total Addressable Market that a company can realistically serve today given its current product, geography, and business model.",
        business_meaning="A more grounded, near-term growth-ceiling estimate than TAM, since it excludes segments the company cannot practically reach without major new investment or capability.",
        related_concepts=("total_addressable_market",),
    ),
    "first_mover_advantage": ConceptCard(
        "first_mover_advantage", M, "First-Mover Advantage",
        "The competitive benefits an early entrant into a market can capture — brand recognition, customer relationships, learning-curve/scale head start, or de facto standard-setting — before competitors arrive.",
        business_meaning="Not automatic or universal — first movers can also bear the highest costs of market education and can be leapfrogged by fast-following competitors who learn from the pioneer's mistakes.",
        interpretation="First-mover advantage is durable mainly when it compounds into a genuine moat (network effects, switching costs, scale economies) rather than being merely a temporary head start.",
        related_concepts=("economic_moat", "network_effect", "barriers_to_entry"),
    ),
    "disruptive_innovation": ConceptCard(
        "disruptive_innovation", M, "Disruptive Innovation",
        "A theory describing how a simpler, cheaper, or more accessible product/technology can enter a market at the low end and progressively move upmarket, eventually displacing established incumbents.",
        business_meaning="Incumbents often ignore disruptive entrants initially because the new offering looks inferior by the incumbent's existing performance metrics and initially targets a segment the incumbent is happy to cede.",
        interpretation="Not every new technology or low-cost entrant is genuinely 'disruptive' in this specific sense — the theory applies specifically to a trajectory of improving from below, not simply competing directly at the high end.",
        related_concepts=("economic_moat", "first_mover_advantage"),
    ),
    "vertical_integration": ConceptCard(
        "vertical_integration", M, "Vertical Integration",
        "A company expanding control over multiple stages of its supply chain — e.g. a manufacturer acquiring its raw-material suppliers (backward integration) or its distribution/retail channel (forward integration).",
        business_meaning="Can improve margin capture, supply security, and quality control, but increases capital intensity and reduces flexibility to switch suppliers/channels if conditions change.",
        interpretation="Vertical integration is a genuine moat-builder mainly when it creates a cost or quality advantage a non-integrated competitor genuinely cannot replicate, not merely when it captures more margin on paper.",
        related_concepts=("economic_moat", "capital_intensity", "barriers_to_entry"),
    ),
}
