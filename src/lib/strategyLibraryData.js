/**
 * Strategy Research Library — content model.
 *
 * Each entry pairs a textbook strategy family (the education) with AGI's real
 * position on it (the honesty). The `agi` block is transcribed from
 * intelligence-engine/strategy_lab/production.py REGISTRY and the seven-stage
 * ladder in strategy_lab/validation_registry.py. If the registry changes,
 * update `agi.strategies` here — these are deliberately static so the page
 * never implies a live capability it cannot evidence.
 *
 * LIFECYCLE LADDER (validation_registry.py):
 *   1 EXPERIMENTAL  2 OPERATIONAL  3 BACKTESTABLE  4 RESEARCH_VALIDATED
 *   5 INVESTMENT_VALIDATED  6 PRODUCTION_CANDIDATE  7 PRODUCTION
 * Historical alpha claims require stage 4. Execution requires stage 7.
 */

export const LADDER = [
  'EXPERIMENTAL',
  'OPERATIONAL',
  'BACKTESTABLE',
  'RESEARCH_VALIDATED',
  'INVESTMENT_VALIDATED',
  'PRODUCTION_CANDIDATE',
  'PRODUCTION',
];

export const ALPHA_CLAIM_STAGE = 4;
export const EXECUTION_STAGE = 7;

/** Human-readable reasons, keyed by the registry's blocked_by codes. */
export const BLOCKER_COPY = {
  PIT_DATA_MISSING: 'Point-in-time filing dates are not recorded, so fundamentals cannot be aligned to what was knowable on the day.',
  BACKTEST_INSUFFICIENT: 'No accepted walk-forward backtest receipt exists for this strategy.',
  DERIVATIVES_DATA_MISSING: 'Options chains, implied volatility surfaces and open interest are not ingested.',
  RISK_LIMIT: 'Exposure, covariance and capacity controls are not validated for allocation decisions.',
  EVENT_TIMESTAMP_MISSING: 'Events are not timestamped to the minute they became public, so abnormal returns cannot be measured cleanly.',
  CORPORATE_ACTION_UNVERIFIED: 'No independent receipt confirms the adjusted-price history is complete.',
  COST_FAILURE: 'Modelled transaction costs exceed the gross edge at realistic size.',
  MACRO_VINTAGE_MISSING: 'Macro series are not stored as vintages, so revisions leak future information.',
  COMPONENT_VALIDATION_INSUFFICIENT: 'Component strategies have not independently cleared validation, so a composite cannot inherit their evidence.',
};

/**
 * Illustrative firm figures. PLACEHOLDERS — not audited, not represented as
 * fact. Anything numeric that could read as a track record lives here so it is
 * easy to find and remove.
 */
export const FIRM_PLACEHOLDER = {
  founded: '2024',
  researchUniverse: '2,714',
  factorLayer: 'research-factor-layer-v2.1.0',
  strategiesRegistered: 14,
  strategiesOperational: 5,
};

const strat = (id, name, stage, blockedBy = []) => ({ id, name, stage, blockedBy });

export const STRATEGIES = [
  {
    id: 'long-short-equity',
    number: '01',
    title: 'Long/Short Equity & Market Neutral',
    family: 'Equity',
    summary:
      'Buy securities expected to outperform, sell short those expected to underperform, and size the two books so that broad market direction is no longer the dominant driver of returns. What remains is the manager’s security selection.',
    mechanics: [
      'Rank a universe on some combination of quality, valuation, growth and momentum evidence.',
      'Take long positions in the top of the ranking and short positions in the bottom.',
      'Size the books so aggregate beta lands on target. A market-neutral book targets zero; a long-biased book runs a deliberate positive residual.',
      'Neutralise unintended sector and factor tilts, so the position reflects the intended view rather than an accidental bet on, say, rate sensitivity.',
    ],
    math: [
      {
        label: 'Single-factor decomposition',
        tex: 'r_i = \\alpha_i + \\beta_i r_m + \\varepsilon_i',
        note: 'Return splits into skill (α), market exposure (βrₘ) and idiosyncratic noise (ε). The entire point of hedging is to remove the middle term so α is what you are left holding.',
      },
      {
        label: 'Portfolio beta',
        tex: '\\beta_p = \\sum_{i \\in L} w_i \\beta_i - \\sum_{j \\in S} w_j \\beta_j',
        note: 'Market neutral means βₚ ≈ 0. Note this neutralises the estimate, not the realised exposure — betas drift, especially in stress.',
      },
      {
        label: 'Carhart four-factor model',
        tex: 'r_i - r_f = \\alpha_i + \\beta_i(r_m - r_f) + s_i\\,\\mathrm{SMB} + h_i\\,\\mathrm{HML} + m_i\\,\\mathrm{MOM} + \\varepsilon_i',
        note: 'Adds size (SMB), value (HML) and momentum (MOM). Most apparent alpha survives the single-factor model and dies here — which is precisely why allocators run it.',
      },
    ],
    widget: 'beta',
    risks: [
      ['Crowding', 'Popular shorts and longs are held by many funds at once. Forced unwinds become self-reinforcing.'],
      ['Residual factor exposure', 'A book neutral to beta can still be heavily long momentum or short value without anyone intending it.'],
      ['Short squeezes', 'Losses on the short book are unbounded, and borrow can be recalled at the worst moment.'],
      ['Beta instability', 'Estimated betas are backward-looking. Correlations converge toward one in a crisis, exactly when neutrality matters most.'],
    ],
    sources: ['CRSP', 'Compustat', 'I/B/E/S consensus', 'Bloomberg / FactSet', 'Alternative data: card panels, satellite, web traffic'],
    agi: {
      note: 'AGI has cross-sectional ranking working on price data. The fundamental factor layer that would drive the long book exists and computes, but has no validated strategy on top of it, and there is no short book of any kind.',
      strategies: [
        strat('cross_sectional_momentum', 'Cross-Sectional Momentum', 2),
        strat('quality_momentum', 'Quality + Momentum', 1, ['PIT_DATA_MISSING', 'BACKTEST_INSUFFICIENT']),
        strat('value_quality', 'Value + Quality', 1, ['PIT_DATA_MISSING', 'BACKTEST_INSUFFICIENT']),
        strat('accounting_quality', 'Accounting Quality', 1, ['PIT_DATA_MISSING', 'BACKTEST_INSUFFICIENT']),
      ],
    },
  },

  {
    id: 'stat-arb',
    number: '02',
    title: 'Statistical Arbitrage & Pairs Trading',
    family: 'Relative value',
    summary:
      'Two securities driven by the same economics should not drift apart indefinitely. When the spread between them stretches, take the convergent position and wait. The edge is statistical, not fundamental — it pays out across many small, uncorrelated bets.',
    mechanics: [
      'Test candidate pairs for cointegration — a stationary linear combination, not merely high correlation.',
      'Estimate the hedge ratio γ that makes the combination stationary.',
      'Model the residual spread as mean-reverting and standardise it into a z-score.',
      'Enter when the spread is stretched, exit as it reverts. Stop out when the relationship itself appears to have broken.',
    ],
    math: [
      {
        label: 'Cointegrating spread',
        tex: 's_t = \\ln P^{A}_{t} - \\gamma \\ln P^{B}_{t}',
        note: 'Log prices, so γ is a ratio rather than a currency amount. Stationarity of sₜ is the entire premise — test it, do not assume it.',
      },
      {
        label: 'Ornstein–Uhlenbeck dynamics',
        tex: 'ds_t = \\theta(\\mu - s_t)\\,dt + \\sigma\\,dW_t',
        note: 'θ is the pull toward the long-run mean μ; σ is the noise. Larger θ means faster reversion and shorter holds.',
      },
      {
        label: 'Half-life of reversion',
        tex: 't_{1/2} = \\frac{\\ln 2}{\\theta}',
        note: 'Sets the holding period and therefore the cost budget. A half-life longer than your patience is not a tradable signal.',
      },
      {
        label: 'Entry and exit rule',
        tex: 'z_t = \\frac{s_t - \\mu}{\\sigma_s} \\quad\\Rightarrow\\quad \\text{enter } |z_t| > 2,\\;\\; \\text{exit } z_t \\approx 0',
        note: 'Thresholds are a cost trade-off, not a constant. Tighter bands trade more often and hand more of the edge to the spread.',
      },
    ],
    widget: 'ou',
    risks: [
      ['Relationship breakdown', 'Cointegration is an empirical regularity, not a law. A merger, a regulatory change or a balance-sheet shock ends it permanently.'],
      ['Transaction costs', 'Gross edge per trade is small. Costs and slippage decide whether the strategy exists at all.'],
      ['Crowded unwinds', 'August 2007: quant books deleveraged simultaneously and supposedly uncorrelated spreads moved together violently.'],
      ['Borrow and financing', 'The short leg depends on availability and cost of borrow, neither of which is guaranteed.'],
    ],
    sources: ['Tick data (TAQ, Polygon)', 'Exchange order-book feeds', 'Corporate action histories', 'Securities lending / borrow rates'],
    agi: {
      note: 'Registered and specified, but blocked. The engine will not certify a spread strategy while corporate-action adjustment is unverified, because an unadjusted split looks exactly like a violent mean-reversion opportunity.',
      strategies: [
        strat('pairs_stat_arb', 'Pairs / Statistical Arbitrage', 1, ['CORPORATE_ACTION_UNVERIFIED', 'COST_FAILURE']),
        strat('mean_reversion', 'Medium-Term Mean Reversion', 2),
      ],
    },
  },

  {
    id: 'merger-arb',
    number: '03',
    title: 'Merger Arbitrage',
    family: 'Event-driven',
    summary:
      'After a deal is announced, the target trades below the offer price. That discount is payment for bearing the risk the deal does not close. The work is estimating the probability of completion better than the market does.',
    mechanics: [
      'A deal is announced at price K. The target trades at P < K.',
      'Buy the target. In a stock deal, short the acquirer at the exchange ratio to isolate deal risk from market direction.',
      'Collect the spread when the deal closes. Absorb the fall to the unaffected price D if it breaks.',
      'The return is a function of the spread and of time — a deal closing in one month at a 2% spread is very different from the same spread over a year.',
    ],
    math: [
      {
        label: 'Gross spread',
        tex: '\\text{Spread} = \\frac{K - P}{P}',
        note: 'K is the offer, P the current price. Headline number, and on its own close to meaningless without a timeline.',
      },
      {
        label: 'Annualised return',
        tex: 'R_{\\text{ann}} = \\left(\\frac{K}{P}\\right)^{365/t} - 1',
        note: 'Where t is days to expected close. Slipping the close date damages returns far more than most people expect.',
      },
      {
        label: 'Expected value',
        tex: '\\mathbb{E}[V] = pK + (1-p)D',
        note: 'p is probability of completion, D the unaffected downside price. The distribution is two-point and violently skewed.',
      },
      {
        label: 'Market-implied probability',
        tex: 'p^{*} = \\frac{P - D}{K - D}',
        note: 'Invert the pricing to recover the market’s implied odds. Your edge is a defensible view on why p differs from p*.',
      },
    ],
    widget: 'merger',
    risks: [
      ['Deal break', 'The defining risk. Small, frequent gains against rare large losses — returns look excellent right up until they do not.'],
      ['Regulatory block', 'Antitrust and national-security review are slow, political and hard to handicap from outside.'],
      ['Financing failure', 'Leveraged acquirers can lose funding between announcement and close.'],
      ['Negative skew', 'The payoff resembles a short option. Volatility understates the risk; drawdown and tail measures do not.'],
    ],
    sources: ['SEC EDGAR merger proxies', 'Bloomberg M&A', 'Regulatory dockets', 'Court filings', 'Borrow availability on acquirers'],
    agi: {
      note: 'Not separately registered. The nearest AGI entry is the general event framework, which is blocked before any merger-specific work could begin.',
      strategies: [strat('event_strategies', 'Event Strategies', 1, ['EVENT_TIMESTAMP_MISSING', 'CORPORATE_ACTION_UNVERIFIED'])],
    },
  },

  {
    id: 'vol-arb',
    number: '04',
    title: 'Convertible & Volatility Arbitrage',
    family: 'Derivatives',
    summary:
      'A convertible bond is debt with an embedded call option. Buy the bond, hedge away the equity exposure, and you hold the option cheaply. The position then profits from the difference between the volatility you paid for and the volatility that actually arrives.',
    mechanics: [
      'Decompose the convertible into a straight bond plus an equity call.',
      'Short the underlying equity in proportion to delta, so small moves in either direction net out.',
      'Re-hedge as delta changes. This is where the P&L is actually manufactured.',
      'A long-gamma position earns on realised movement and bleeds theta as time passes. The trade is a bet that movement exceeds the price paid for it.',
    ],
    math: [
      {
        label: 'Convertible decomposition',
        tex: 'V_{\\text{CB}} \\approx B + C(S, K, \\sigma, T, r)',
        note: 'Bond floor B plus a call on the equity. Credit quality moves B; volatility moves C.',
      },
      {
        label: 'Delta',
        tex: '\\Delta = \\frac{\\partial V}{\\partial S}',
        note: 'The hedge ratio. Not constant — its rate of change is gamma, and gamma is the whole strategy.',
      },
      {
        label: 'Gamma–theta trade-off',
        tex: '\\text{P\\&L} \\approx \\tfrac{1}{2}\\Gamma(\\delta S)^2 - \\Theta\\,\\delta t',
        note: 'Movement pays, time costs. Long gamma needs realised movement to exceed the daily decay bill.',
      },
      {
        label: 'Delta-hedged option P&L',
        tex: '\\Pi = \\int_{0}^{T} \\tfrac{1}{2}\\,\\Gamma_t\\, S_t^2\\,\\bigl(\\sigma^2_{\\text{real}} - \\sigma^2_{\\text{imp}}\\bigr)\\,dt',
        note: 'The cleanest statement of the trade: you are long the spread between realised and implied variance, weighted by dollar gamma.',
      },
    ],
    widget: 'gamma',
    risks: [
      ['Short volatility tails', 'February 2018 and March 2020 both destroyed short-vol books in days. Losses are convex against you.'],
      ['Credit risk', 'The bond floor is only a floor while the issuer is solvent. Credit and equity stress arrive together.'],
      ['Borrow recall', 'Losing the short leg unhedges the position at the worst possible time.'],
      ['Liquidity spirals', 'Convertibles are thin. Forced selling moves marks against everyone holding the same paper.'],
    ],
    sources: ['OPRA options data', 'OptionMetrics', 'CDS from ICE / Markit', 'Convertible terms and indentures', 'Borrow rates'],
    agi: {
      note: 'Registered as volatility premia and blocked at the first hurdle: AGI does not currently ingest options data at all, so implied volatility cannot be computed, let alone compared to realised.',
      strategies: [strat('volatility_premia', 'Volatility Premia', 1, ['DERIVATIVES_DATA_MISSING', 'BACKTEST_INSUFFICIENT'])],
    },
  },

  {
    id: 'fixed-income-rv',
    number: '05',
    title: 'Fixed Income Relative Value',
    family: 'Rates',
    summary:
      'Bonds that should be priced consistently sometimes are not. The mispricings are small, so the strategy runs leverage — which makes funding conditions, rather than the trade thesis, the thing most likely to end it.',
    mechanics: [
      'Butterflies (2s5s10s): trade the belly of the curve against the wings, duration-neutral, expressing a view on curvature rather than direction.',
      'Swap spreads: the gap between swap rates and government yields.',
      'On-the-run versus off-the-run: near-identical bonds priced apart by liquidity preference.',
      'Cash–futures basis: the deliverable bond against its future, financed in repo. Small edge, large leverage.',
    ],
    math: [
      {
        label: 'Duration–convexity approximation',
        tex: '\\frac{\\delta P}{P} \\approx -D\\,\\delta y + \\tfrac{1}{2}C(\\delta y)^2',
        note: 'First order gives duration, second order convexity. For large yield moves the convexity term stops being a rounding error.',
      },
      {
        label: 'Duration-neutral butterfly',
        tex: 'D_{5}w_{5} = D_{2}w_{2} + D_{10}w_{10}',
        note: 'Weights chosen so parallel shifts cancel, leaving only the curvature view.',
      },
      {
        label: 'Levered basis return',
        tex: 'R = \\frac{y_{\\text{bond}} - r_{\\text{repo}}}{h}, \\qquad h = \\text{haircut}',
        note: 'A handful of basis points multiplied by leverage. When the haircut rises, the position must shrink regardless of whether the thesis is intact.',
      },
    ],
    widget: 'curve',
    risks: [
      ['Funding and leverage', 'LTCM in 1998: the trades were largely right and the fund still failed, because it could not finance them long enough.'],
      ['Basis unwind', 'March 2020: the cash–futures basis gapped and levered holders were forced out simultaneously.'],
      ['Repo stress', 'Haircuts widen exactly when positions are underwater.'],
      ['Small edge, large size', 'Any structure that needs heavy leverage to be interesting is fragile by construction.'],
    ],
    sources: ['Tradeweb', 'BrokerTec', 'NY Fed repo data', 'CME futures', 'Central bank auction calendars'],
    agi: {
      note: 'Not registered in any form. AGI is an equity research platform today — there is no rates data, no curve infrastructure and no repo modelling.',
      strategies: [],
    },
  },

  {
    id: 'macro-trend',
    number: '06',
    title: 'Global Macro & Managed Futures',
    family: 'Directional',
    summary:
      'Take directional positions across equities, rates, currencies and commodities, sized by volatility rather than conviction. Systematic trend following is the most durable version: it gives up money in choppy markets and earns it back in sustained ones.',
    mechanics: [
      'Measure trend over one or more lookback windows.',
      'Size each position inversely to its own volatility, so no single market dominates the book.',
      'Diversify across dozens of uncorrelated markets — diversification, not signal quality, does most of the work.',
      'Accept a low hit rate. The return profile is many small losses and a few large gains.',
    ],
    math: [
      {
        label: 'Momentum signal',
        tex: '\\text{sig}_i = \\operatorname{sign}\\!\\left(\\frac{P_t}{P_{t-k}} - 1\\right)',
        note: 'Deliberately crude. Elaborate trend signals rarely survive out of sample better than this one.',
      },
      {
        label: 'Volatility-targeted sizing',
        tex: 'w_i = \\text{sig}_i \\cdot \\frac{\\sigma_{\\text{target}}}{\\hat{\\sigma}_i \\sqrt{N}}',
        note: 'Equalises risk contribution across N markets, so a quiet bond future and a violent commodity carry comparable weight.',
      },
      {
        label: 'Carry approximation',
        tex: 'R_{\\text{carry}} \\approx (i_{\\text{foreign}} - i_{\\text{domestic}}) + \\Delta s',
        note: 'Rate differential plus spot move. Carry earns steadily and then gives it back abruptly — the classic negative-skew profile.',
      },
    ],
    widget: 'trend',
    risks: [
      ['Whipsaw', 'Rangebound markets generate repeated false signals and a long, grinding drawdown.'],
      ['Carry crashes', 'Positions unwind together across currencies when risk appetite turns.'],
      ['Crowding at the turn', 'Trend followers hold similar positions and reverse them at similar times.'],
      ['Low hit rate', 'Psychologically hard to hold. Most of the return arrives in a small number of months.'],
    ],
    sources: ['CME / ICE / Eurex futures', 'CFTC Commitments of Traders', 'Macro release calendars', 'PMI and survey data'],
    agi: {
      note: 'This is where AGI is genuinely furthest along. Four trend and breakout strategies compute on live end-of-day data and sit at OPERATIONAL — stage two of seven. They are single-market Indian equity signals, not a diversified multi-asset futures programme, and none has a validated backtest.',
      strategies: [
        strat('time_series_momentum', 'Time-Series Momentum', 2),
        strat('trend_following', 'Trend Following', 2),
        strat('volatility_breakout', 'Volatility Breakout', 2),
        strat('macro_equity', 'Macro-to-Equity', 1, ['MACRO_VINTAGE_MISSING', 'PIT_DATA_MISSING']),
        strat('sector_rotation', 'Sector Rotation', 1, ['PIT_DATA_MISSING', 'RISK_LIMIT']),
      ],
    },
  },

  {
    id: 'event-driven',
    number: '07',
    title: 'Event-Driven, Distressed & Activist',
    family: 'Credit & special situations',
    summary:
      'Returns come from a process running to conclusion rather than from a price forecast: a restructuring completing, a spin-off separating, a board being replaced. Legal and structural analysis matters more than statistics here.',
    mechanics: [
      'Distressed debt: buy claims below expected recovery. The fulcrum security — the one that converts to equity in a reorganisation — is where control is decided.',
      'Activist: build a stake, publish a thesis, push for a change in capital allocation, strategy or management.',
      'Special situations: spin-offs, rights issues, index deletions and other structural dislocations that force non-economic selling.',
      'Position sizing is dominated by the fact that outcomes are binary and timing is controlled by courts and boards.',
    ],
    math: [
      {
        label: 'Recovery value',
        tex: 'R_c = \\min\\!\\left(F_c,\\; \\max\\!\\left(0,\\; V_{\\text{EV}} - \\textstyle\\sum_{k \\prec c} F_k\\right)\\right)',
        note: 'Claim c recovers only what enterprise value remains after every more senior claim is paid in full. This is the waterfall, stated compactly.',
      },
      {
        label: 'Expected return on a claim',
        tex: '\\mathbb{E}[r] = \\frac{\\sum_j p_j R_c^{(j)}}{P_c} - 1',
        note: 'Probability-weighted recovery across restructuring scenarios j, against the current claim price.',
      },
    ],
    widget: 'waterfall',
    risks: [
      ['Illiquidity', 'Positions can take years to exit and may not be marketable at all in between.'],
      ['Legal process duration', 'Bankruptcy timelines slip. Returns are annualised over a denominator you do not control.'],
      ['Binary outcomes', 'A claim recovers well or recovers nothing. Average-case analysis is actively misleading.'],
      ['Adversarial counterparties', 'Other creditors are sophisticated and their interests are directly opposed to yours.'],
    ],
    sources: ['Bankruptcy dockets (PACER)', '13D / 13G filings', 'Indenture and credit agreements', 'Trade claim brokers', 'Court transcripts'],
    agi: {
      note: 'Blocked. Event work requires knowing the minute information became public; AGI stores event dates but not publication timestamps, which makes abnormal-return measurement unreliable.',
      strategies: [strat('event_strategies', 'Event Strategies', 1, ['EVENT_TIMESTAMP_MISSING', 'CORPORATE_ACTION_UNVERIFIED'])],
    },
  },

  {
    id: 'multi-strat',
    number: '08',
    title: 'Multi-Strategy Platform',
    family: 'Platform',
    summary:
      'Run many independent teams under one risk framework, hold each to tight limits, and reallocate capital quickly. The product is not any single strategy — it is the diversification arithmetic across all of them.',
    mechanics: [
      'Independent teams trade separate books with individually modest Sharpe ratios.',
      'Each operates under hard drawdown and exposure limits, enforced centrally rather than by the team.',
      'Capital moves toward what is working and away from what is not, on a short cycle.',
      'Central risk nets exposures across the platform so the firm is not accidentally concentrated.',
    ],
    math: [
      {
        label: 'Diversification identity',
        tex: 'S_{\\text{platform}} \\approx S \\sqrt{N}',
        note: 'N genuinely independent books each of Sharpe S combine to S√N. Ten books at 0.5 give roughly 1.6 — better than any one of them.',
      },
      {
        label: 'With realistic correlation',
        tex: 'S_{\\text{platform}} = \\frac{S\\sqrt{N}}{\\sqrt{1 + (N-1)\\rho}}',
        note: 'The honest version. At ρ = 0.2 the benefit saturates quickly, which is why platforms fight so hard over genuine independence.',
      },
    ],
    widget: 'pods',
    risks: [
      ['Correlation underestimated', 'Books that appear independent share factor exposures that only surface under stress.'],
      ['Simultaneous deleveraging', 'Tight stops across many pods can force the whole platform to sell at once.'],
      ['Fee drag', 'Paying for many teams requires the diversification benefit to be real, not assumed.'],
      ['Talent concentration', 'A departing team can remove a meaningful share of returns.'],
    ],
    sources: ['Internal position and P&L systems', 'Barra / Axioma risk models', 'Prime broker exposure reporting', 'Cross-pod netting infrastructure'],
    agi: {
      note: 'Registered as the composite research strategy and blocked by design: the registry refuses to let a composite inherit evidence its components have not independently earned. With no component above stage two, the composite cannot rise above stage one.',
      strategies: [strat('composite_research', 'Composite Research Strategy', 1, ['COMPONENT_VALIDATION_INSUFFICIENT', 'BACKTEST_INSUFFICIENT'])],
    },
  },
];

export const DISCLAIMER =
  'For informational purposes only. Not an offer to sell or a solicitation of an offer to buy any security. Past performance is not indicative of future results. All figures shown are illustrative simulations, not actual results.';
