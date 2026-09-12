"""Business Quality Concepts — moats, pricing power, and competitive dynamics.

Not one of the 8 numbered modules in the Phase 2.6 brief verbatim, but
required to answer several of the concept-shaped questions the brief itself
lists as Module 13 examples (Economic Moat, Network Effect, Switching Cost)
and the AFI Acceptance Test's Business Intelligence section (pricing power,
network effects, competitive moats, operating leverage via airlines) —
these are concept/definition questions, not company-specific analysis, so
they belong in financial_concepts rather than being left to generic
retrieval.
"""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "business_quality"

BUSINESS_QUALITY_CONCEPTS: dict[str, ConceptCard] = {
    "network_effect": ConceptCard(
        "network_effect", M, "Network Effect",
        "A dynamic where a product or platform becomes more valuable to each user as more users join it.",
        business_meaning=(
            "Network effects create a powerful, self-reinforcing moat and flywheel: the market "
            "leader's product or platform improves faster than a smaller rival's simply because "
            "it has more users — each new user raises value for existing users — making it very "
            "hard to dislodge once critical mass and scale are reached."
        ),
        interpretation="Direct network effects (users value connecting with other users, e.g. social/communication platforms) are typically stronger and more durable than indirect ones (more users attract more third-party complements, e.g. app stores, marketplaces).",
        common_mistakes="Assuming any large user base implies a network effect — a network effect requires that MORE users make the product BETTER for existing users, not just that the company has scale.",
        related_concepts=("economic_moat", "switching_cost", "winner_take_all"),
    ),
    "switching_cost": ConceptCard(
        "switching_cost", M, "Switching Cost",
        "The friction — financial, operational, or psychological — a customer would incur by moving from one supplier or product to a competitor's.",
        business_meaning="High switching costs let a company retain customers and pricing power even without a superior product, because the pain of switching outweighs the benefit of a marginally better/cheaper alternative.",
        interpretation="Switching costs are strongest when they combine multiple dimensions at once — integrated enterprise software (data migration + retraining + workflow risk) has much higher switching costs than a simple consumer subscription.",
        related_concepts=("economic_moat", "pricing_power", "customer_lifetime_value"),
    ),
    "pricing_power": ConceptCard(
        "pricing_power", M, "Pricing Power",
        "A company's ability to raise prices without a proportionate loss of sales volume or customers.",
        business_meaning="Pricing power comes from differentiation, brand strength, switching costs, scarcity, or a lack of viable substitutes — it lets a company pass through cost inflation and expand margins over time.",
        interpretation="The clearest empirical test of pricing power is whether a company can raise prices during an inflationary period without losing volume/market share — commodity businesses generally cannot, brand and moat-protected businesses often can.",
        common_mistakes="Confusing pricing power with simply having high prices — a luxury brand and a monopoly utility can both have high prices for very different structural reasons, only one of which may be durable.",
        related_concepts=("economic_moat", "brand_value", "switching_cost", "barriers_to_entry"),
    ),
    "brand_value": ConceptCard(
        "brand_value", M, "Brand Value",
        "The premium a company can command in price, loyalty, or trust purely from the reputation and associations of its brand, independent of the physical product itself.",
        business_meaning="A strong brand allows a company to charge more than an otherwise-similar unbranded competitor and to launch new products with lower customer-acquisition friction.",
        interpretation="Brand value shows up quantitatively as sustained gross margin and pricing power advantages over private-label or generic competitors selling functionally similar products.",
        related_concepts=("pricing_power", "economic_moat", "intangible_assets"),
    ),
    "barriers_to_entry": ConceptCard(
        "barriers_to_entry", M, "Barriers to Entry",
        "Structural obstacles — capital requirements, regulation, licensing, scale economies, network effects, brand — that make it difficult for new competitors to enter an industry and compete effectively.",
        business_meaning="High barriers to entry protect incumbents' returns on capital over the long run by limiting the supply-side response to attractive profitability.",
        interpretation="The most durable barriers combine structural (hard to replicate with capital alone, e.g. regulatory licenses, network effects) and economic (require patient capital and years to build, e.g. brand, distribution) elements together.",
        related_concepts=("economic_moat", "scale_economies", "efficient_scale"),
    ),
    "scale_economies": ConceptCard(
        "scale_economies", M, "Scale Economies (Economies of Scale)",
        "Cost advantages a company gains as its output/volume increases, because fixed costs are spread over more units.",
        business_meaning="A scale leader can profitably match or undercut smaller rivals' prices while still earning superior margins — this cost advantage widens as the leader continues to grow relative to competitors.",
        interpretation="Scale economies are a genuine moat source only if they translate into a durable cost gap that smaller/new entrants cannot close even after they, too, achieve meaningful (but still smaller) scale.",
        related_concepts=("operating_leverage", "barriers_to_entry", "efficient_scale"),
    ),
    "efficient_scale": ConceptCard(
        "efficient_scale", M, "Efficient Scale",
        "A market that is only large enough to profitably support one or a small number of players — a second entrant would drive returns for everyone below the cost of capital.",
        business_meaning="Common in niche infrastructure businesses (a single regional airport, pipeline, or utility) where the addressable market naturally limits sustainable competition.",
        interpretation="This moat source is defined by market size relative to the minimum efficient scale of the business, not by any action the incumbent takes — it is a structural, geography/demand-driven barrier.",
        related_concepts=("barriers_to_entry", "economic_moat", "scale_economies"),
    ),
    "winner_take_all": ConceptCard(
        "winner_take_all", M, "Winner-Take-All (Winner-Take-Most) Dynamics",
        "A competitive dynamic, common in network-effect-driven markets, where the market leader captures a disproportionate — sometimes near-total — share of profit and value, leaving rivals with little.",
        business_meaning="Occurs when network effects, scale economies, and switching costs all reinforce each other, so a small early lead compounds into a dominant, hard-to-contest position.",
        interpretation="Investors should distinguish genuine winner-take-all markets (where the structural dynamics guarantee this outcome) from markets merely dominated by a current leader that remains genuinely contestable.",
        related_concepts=("network_effect", "economic_moat", "scale_economies"),
    ),
    "customer_lifetime_value": ConceptCard(
        "customer_lifetime_value", M, "Customer Lifetime Value (LTV)",
        "The total profit a business expects to earn from a customer over the entire duration of the relationship.",
        formula="LTV ≈ Average Revenue Per Customer × Gross Margin × Average Customer Lifespan",
        business_meaning="A business with high LTV relative to its Customer Acquisition Cost (CAC) can profitably spend more to acquire customers than competitors with a weaker LTV/CAC ratio, compounding a growth advantage.",
        interpretation="LTV/CAC materially above 3x is often cited as a healthy benchmark for subscription/recurring-revenue businesses, though the right ratio varies significantly by industry payback expectations.",
        related_concepts=("switching_cost", "unit_economics", "churn"),
    ),
    "unit_economics": ConceptCard(
        "unit_economics", M, "Unit Economics",
        "The direct revenues and costs associated with a single unit of a company's business model — one customer, one order, one store — independent of fixed corporate overhead.",
        business_meaning="A business can scale total revenue rapidly while unit economics remain unprofitable, meaning growth is actually compounding losses rather than value — a critical check for early-stage or heavily-subsidized businesses.",
        interpretation="Positive and improving unit economics as a company scales (better than fixed-cost leverage alone would suggest) signals a genuinely efficient, durable business model, not just growth funded by capital.",
        related_concepts=("customer_lifetime_value", "contribution_margin", "operating_leverage"),
    ),
    "churn": ConceptCard(
        "churn", M, "Churn (Rate)",
        "The percentage of customers (or recurring revenue) a business loses over a given period.",
        formula="Customer Churn Rate = Customers Lost in Period / Customers at Start of Period",
        business_meaning="High churn directly shortens average customer lifespan, reducing Customer Lifetime Value and forcing a business to spend more continuously just to replace lost revenue/customers.",
        interpretation="A business with strong switching costs or network effects should show structurally low and improving churn over time; rising churn despite stable pricing often signals eroding competitive position.",
        related_concepts=("customer_lifetime_value", "switching_cost", "unit_economics"),
    ),
    "intangible_assets": ConceptCard(
        "intangible_assets", M, "Intangible Assets",
        "Non-physical assets — brands, patents, licenses, customer relationships, proprietary technology — that generate economic value but often are not fully reflected on the balance sheet.",
        business_meaning="Businesses with valuable, self-generated (not acquired) intangible assets often trade at valuations that look expensive on simple book-value multiples, because the accounting balance sheet understates their true asset base.",
        interpretation="Acquired intangibles (via M&A, recorded as goodwill/identified intangibles) DO appear on the balance sheet, while internally-generated intangibles (built organically, like a homegrown brand) generally do not — this asymmetry is a key reason P/B is unreliable for asset-light, brand/IP-driven businesses.",
        related_concepts=("brand_value", "goodwill_and_intangibles", "p_b"),
    ),
}
