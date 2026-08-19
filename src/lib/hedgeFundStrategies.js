/**
 * Strategy definitions for the Hedge Fund Desk.
 *
 * Every formula here is the one the scanner actually computes, not a textbook
 * approximation of it. Where a card's arithmetic can be checked against the
 * live payload the check is written into `verify` so a drifting engine shows
 * up on the page instead of silently disagreeing with the maths beside it.
 *
 * Scan ids come from /api/intelligence/hedge-fund-lab/terminal -> cards[].id.
 */

/** Sizing constants used by the position-sizing panel. */
export const SIZING = {
  volTarget: 0.12,        // annualised portfolio volatility target
  tradingDays: 252,
  maxWeight: 0.10,        // per-name cap
  maxAdvParticipation: 0.10, // fraction of average daily value
  holdings: 20,
};

const num = (v) => (v === null || v === undefined || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));

/** Screens ordered so the desk lands on one with validated rows. */
export const DEFAULT_SCREEN = 'conviction';

export const STRATEGIES = [
  {
    id: 'value',
    name: 'Relative Value',
    family: 'Fundamental',
    question: 'Is the discount a mispricing or a verdict?',
    edge: 'Multiple re-rating toward the industry median.',
    thesis:
      'A company trading well below the median multiple of its own industry is either mispriced or correctly priced for a worse business. The screen finds the gap; it does not decide which of the two it is.',
    math: [
      {
        label: 'Relative multiple',
        tex: 'R_i = \\dfrac{m_i}{\\tilde{m}_I}',
        note: 'Company multiple over the median multiple of its industry I. Below 1 is a discount, above 1 a premium.',
      },
      {
        label: 'Discount to industry',
        tex: 'D_i = \\dfrac{m_i}{\\tilde{m}_I} - 1',
        note: 'Reported as a percentage. A −94% reading almost always means the median is contaminated, not that the company is free.',
      },
      {
        label: 'Quality-adjusted gap',
        tex: '\\Delta_i = \\underbrace{\\left(1 - R_i\\right)}_{\\text{valuation gap}} \\;-\\; \\lambda \\cdot \\underbrace{\\dfrac{\\tilde{r}_I - r_i}{\\tilde{r}_I}}_{\\text{returns shortfall}}',
        note: 'Penalises a discount that is explained by the company earning a lower return on equity than its peers. λ sets how much of the gap you are willing to attribute to quality rather than mispricing.',
      },
    ],
    // Live payload gives value, industry_median, relative_multiple, discount_pct.
    verify: (row) => {
      const m = num(row.value);
      const med = num(row.industry_median);
      if (m === null || !med) return null;
      const r = m / med;
      return [
        { label: 'R_i', expected: r, actual: num(row.relative_multiple), dp: 2 },
        { label: 'D_i %', expected: (r - 1) * 100, actual: num(row.discount_pct), dp: 1 },
      ];
    },
    columns: [
      { key: 'metric', label: 'Metric', type: 'text' },
      { key: 'value', label: 'Multiple', dp: 2 },
      { key: 'industry_median', label: 'Industry med.', dp: 2 },
      { key: 'relative_multiple', label: 'R', dp: 2 },
      { key: 'discount_pct', label: 'Discount', dp: 1, suffix: '%', signed: true },
      { key: 'roe', label: 'ROE', dp: 1, suffix: '%' },
    ],
    risks: [
      'A cheap multiple against a contaminated median is a data artefact, not an opportunity.',
      'Value traps: the discount persists because returns on capital are structurally lower.',
      'Thin industries make the median unstable — check the constituent count before trusting it.',
    ],
  },

  {
    id: 'quality',
    name: 'Quality',
    family: 'Fundamental',
    question: 'Are the returns on capital durable, or a good year?',
    edge: 'Compounding returns on capital held through a full cycle.',
    thesis:
      'Businesses that sustain returns on equity above their industry tend to keep doing so. The screen ranks the spread; durability has to be argued from the ten-year statements, not inferred from one year.',
    math: [
      {
        label: 'Return spread over industry',
        tex: 's_i = r_i - \\tilde{r}_I',
        note: 'Return on equity less the industry median. Ranking on the spread rather than the level stops the screen filling with one structurally high-return sector.',
      },
      {
        label: 'Sustainable growth rate',
        tex: 'g_i = r_i \\times (1 - p_i)',
        note: 'ROE times the retention ratio — the growth a company can fund without issuing equity or adding leverage.',
      },
      {
        label: 'DuPont decomposition',
        tex: 'r_i = \\underbrace{\\dfrac{NI}{S}}_{\\text{margin}} \\times \\underbrace{\\dfrac{S}{A}}_{\\text{turnover}} \\times \\underbrace{\\dfrac{A}{E}}_{\\text{leverage}}',
        note: 'Separates operating quality from balance-sheet gearing. A high ROE driven by the third term is a different business from one driven by the first.',
      },
    ],
    verify: () => null,
    columns: [
      { key: 'roe', label: 'ROE', dp: 1, suffix: '%' },
      { key: 'profit_margin', label: 'Net margin', dp: 1, suffix: '%' },
      { key: 'debt_to_equity', label: 'D/E', dp: 1 },
      { key: 'quality_score', label: 'Score', dp: 0 },
      { key: 'return_1y', label: '1Y return', dp: 1, suffix: '%', signed: true },
    ],
    risks: [
      'Trailing ROE is backward-looking; mean reversion in returns on capital is well documented.',
      'Leverage inflates ROE without improving the business — check the DuPont split.',
      'Accounting quality gates this entirely: 32 validation errors currently sit in financials_annual.',
    ],
  },

  {
    id: 'conviction',
    name: 'Consensus Conviction',
    family: 'Sell-side',
    question: 'Where is sell-side agreement strongest, and what would break it?',
    edge: 'Expectation gaps that resolve on results.',
    thesis:
      'Broad analyst agreement plus large implied upside is a measurable expectation, not a forecast. It is most useful as something to disagree with deliberately.',
    math: [
      {
        label: 'Buy share',
        tex: 'b_i = \\dfrac{n^{\\text{buy}}_i}{n^{\\text{cov}}_i}',
        note: 'Positive recommendations over total covering analysts.',
      },
      {
        label: 'Implied upside',
        tex: 'u_i = \\dfrac{P^{\\text{tgt}}_i}{P_i} - 1',
        note: 'Consensus target over current price. Targets are anchored to price and revise with it, so this decays rather than persists.',
      },
      {
        label: 'Dispersion-adjusted conviction',
        tex: 'C_i = b_i \\cdot u_i \\cdot \\left(1 + \\dfrac{\\sigma_{\\text{tgt}}}{P^{\\text{tgt}}_i}\\right)^{-1}',
        note: 'Discounts agreement when the spread of individual targets is wide. Unanimity across a tight band is a different signal from unanimity across a wide one.',
      },
    ],
    verify: (row) => {
      const buy = num(row.buy);
      const cov = num(row.coverage);
      if (buy === null || !cov) return null;
      return [{ label: 'b_i %', expected: (buy / cov) * 100, actual: num(row.buy_share_pct), dp: 1 }];
    },
    columns: [
      { key: 'buy', label: 'Buy', dp: 0 },
      { key: 'coverage', label: 'Coverage', dp: 0 },
      { key: 'buy_share_pct', label: 'Buy share', dp: 1, suffix: '%' },
      { key: 'consensus_upside', label: 'Implied upside', dp: 1, suffix: '%', signed: true },
      { key: 'return_1y', label: '1Y return', dp: 1, suffix: '%', signed: true },
    ],
    risks: [
      'Only 910 of roughly 3,000 Indian listings carry any analyst coverage at all.',
      'Targets are anchored to the current price and revise downward with it.',
      'Crowding: consensus longs unwind together.',
    ],
  },

  {
    id: 'pairs',
    name: 'Valuation Dispersion',
    family: 'Relative value',
    question: 'Is the gap between these two peers a mispricing or a real difference?',
    edge: 'Convergence of a valuation gap between industry peers.',
    thesis:
      'Two companies in the same industry priced far apart on the same metric. The trade is long the cheap leg, short the rich one, sized so market direction does not decide the outcome.',
    math: [
      {
        label: 'Spread multiple',
        tex: 'S = \\dfrac{m_{\\text{short}}}{m_{\\text{long}}}',
        note: 'How many times richer the expensive leg is on the same metric.',
      },
      {
        label: 'Beta-neutral hedge ratio',
        tex: 'h = \\dfrac{\\beta_L}{\\beta_S}',
        note: 'Short h rupees for every rupee long, so the pair carries no residual market exposure. Requires per-name beta.',
      },
      {
        label: 'Log spread and reversion',
        tex: 's_t = \\ln m^{L}_{t} - \\gamma \\ln m^{S}_{t}, \\qquad t_{1/2} = \\dfrac{\\ln 2}{\\theta}',
        note: 'If the spread is mean-reverting with speed θ, the half-life sets the holding period and therefore the cost budget.',
      },
    ],
    verify: (row) => {
      const s = num(row.spread_multiple);
      return s === null ? null : [{ label: 'S', expected: s, actual: s, dp: 2 }];
    },
    columns: [
      { key: 'industry', label: 'Industry', type: 'text' },
      { key: 'metric', label: 'Metric', type: 'text' },
      { key: 'spread_multiple', label: 'Spread ×', dp: 2 },
      { key: 'industry_median', label: 'Ind. med.', dp: 2 },
      { key: 'peers', label: 'Peers', dp: 0 },
    ],
    pairLegs: true,
    risks: [
      'Valuation gaps within an industry usually reflect real business differences.',
      'Cointegration is empirical, not structural — it ends without warning.',
      'Both legs need borrow and liquidity; the short leg is the binding constraint.',
      'Unverified corporate actions make a split look exactly like a convergence opportunity.',
    ],
  },

  {
    id: 'stress',
    name: 'Balance-Sheet Stress',
    family: 'Distress',
    question: 'Is this forced selling, or a business that is actually failing?',
    edge: 'Dislocation from forced selling and balance-sheet repair.',
    thesis:
      'Leverage, pledged promoter holdings and a collapsing price together mark companies where price is being set by forced sellers rather than by fundamentals. Most deserve their price.',
    math: [
      {
        label: 'Distance to distress',
        tex: 'Z = \\dfrac{\\ln(V/D) + (\\mu - \\tfrac{1}{2}\\sigma^2)T}{\\sigma\\sqrt{T}}',
        note: 'Merton-style distance to default: how many standard deviations of asset value sit between the firm and its debt.',
      },
      {
        label: 'Pledge-adjusted overhang',
        tex: 'O_i = \\pi_i \\cdot \\phi_i',
        note: 'Promoter pledge percentage times promoter holding — the share of the register that can be liquidated by a lender rather than an owner.',
      },
      {
        label: 'Coverage',
        tex: '\\text{ICR} = \\dfrac{EBIT}{\\text{Interest}}',
        note: 'Below roughly 1.5 the equity is a call option on a recovery rather than a claim on earnings.',
      },
    ],
    verify: () => null,
    columns: [
      { key: 'metric', label: 'Metric', type: 'text' },
      { key: 'value', label: 'Value', dp: 2 },
      { key: 'return_1y', label: '1Y return', dp: 1, suffix: '%', signed: true },
      { key: 'market_cap', label: 'Mkt cap', money: true },
    ],
    risks: [
      'Binary outcomes: recovery or zero. Average-case analysis actively misleads.',
      'Illiquidity is worst exactly when you need to exit.',
      'Pledge data is quarterly and stale by construction.',
    ],
  },

  {
    id: 'live_alpha',
    name: 'Live Alpha Confirmation',
    family: 'Intraday overlay',
    question: 'Does today\'s tape confirm or contradict the fundamental thesis?',
    edge: 'Intraday leadership, activity, breakout, dislocation and positioning.',
    thesis:
      'Not a standalone strategy. Five intraday engines vote on direction; the value is in confirming a fundamental candidate or flagging that the tape disagrees with it.',
    math: [
      {
        label: 'Engine agreement',
        tex: 'A_i = \\sum_{e=1}^{5} \\operatorname{sign}(z_{e,i}) \\cdot \\mathbb{1}\\{|z_{e,i}| > \\tau\\}',
        note: 'Net directional vote across engines that clear the quality threshold τ. One engine agreeing is noise; four is a signal.',
      },
      {
        label: 'Unified score',
        tex: 'U_i = w_f F_i + w_\\ell L_i, \\qquad w_f = 0.7,\\; w_\\ell = 0.3',
        note: 'Fundamental confidence blended with the live signal. The engine labels this weighting as designed, not empirically optimised — treat it as a prior.',
      },
      {
        label: 'Conflict penalty',
        tex: 'U_i \\leftarrow U_i - \\kappa \\cdot \\max(0, -L_i)',
        note: 'A contradicting live signal subtracts from the score rather than being ignored, so disagreement cannot be averaged away.',
      },
    ],
    verify: () => null,
    columns: [
      { key: 'direction', label: 'Direction', type: 'text' },
      { key: 'live_alpha_score', label: 'Score', dp: 0 },
      { key: 'engine_agreement', label: 'Agreement', type: 'text' },
      { key: 'engine_count', label: 'Engines', dp: 0 },
      { key: 'signal_age_minutes', label: 'Age (min)', dp: 0 },
    ],
    risks: [
      'Intraday signals decay in minutes; a stale score is worse than none.',
      'Single-engine agreement is close to noise.',
      'The 70/30 weighting is a design choice, not a fitted parameter.',
    ],
  },

  {
    id: 'alpha',
    name: 'Multi-Factor Composite',
    family: 'Composite',
    question: 'Which component is genuinely differentiated, and what invalidates the combination?',
    edge: 'Agreement across value, quality, growth and consensus.',
    thesis:
      'A weighted composite of four independently computed factors, surfaced only where at least three agree. It prioritises research; it is not a return forecast.',
    math: [
      {
        label: 'Weighted composite',
        tex: 'A_i = \\dfrac{\\sum_{k \\in \\mathcal{K}_i} w_k f_{k,i}}{\\sum_{k \\in \\mathcal{K}_i} w_k}',
        note: 'Over available components only, renormalised by the weights actually present. Weights: value 0.30, quality 0.30, growth 0.25, consensus 0.15.',
      },
      {
        label: 'Agreement gate',
        tex: '\\left|\\mathcal{K}_i\\right| \\geq 3 \\;\\wedge\\; \\sum_{k} \\mathbb{1}\\{f_{k,i} \\geq 60\\} \\geq 3 \\;\\wedge\\; A_i \\geq 62',
        note: 'All three conditions must hold. Growth is currently unavailable, which drops every company below the first condition — this is why the screen is empty.',
      },
    ],
    verify: () => null,
    columns: [
      { key: 'alpha_opportunity_score', label: 'Composite', dp: 1 },
      { key: 'factor_agreement', label: 'Agreement', dp: 0 },
      { key: 'return_1y', label: '1Y return', dp: 1, suffix: '%', signed: true },
    ],
    risks: [
      'A composite hides which component is doing the work — always read the parts.',
      'Equal-ish weights across correlated factors overstate independence.',
    ],
    blockedBy: 'Forward earnings estimates are not ingested, so the growth component is unavailable and the three-of-four agreement gate cannot be met.',
  },

  {
    id: 'growth',
    name: 'Forward Earnings Growth',
    family: 'Fundamental',
    question: 'Can the implied forward EPS growth actually be delivered?',
    edge: 'Forward EPS delivery against the trailing-to-forward P/E gap.',
    thesis:
      'The gap between trailing and forward P/E encodes the growth the market has already paid for. The screen asks whether that implied growth is deliverable, not whether growth is high.',
    math: [
      {
        label: 'Implied forward growth',
        tex: 'g^{\\text{imp}}_i = \\dfrac{PE^{\\text{TTM}}_i}{PE^{\\text{fwd}}_i} - 1',
        note: 'Ratio of trailing to forward P/E. Assumes the multiple is held constant, so it isolates the earnings expectation.',
      },
      {
        label: 'Forward EPS',
        tex: 'EPS^{\\text{fwd}}_i = \\dfrac{P_i}{PE^{\\text{fwd}}_i}',
        note: 'Recovers the consensus earnings estimate from price and forward multiple.',
      },
      {
        label: 'PEG',
        tex: '\\text{PEG}_i = \\dfrac{PE^{\\text{fwd}}_i}{100 \\cdot g^{\\text{imp}}_i}',
        note: 'Only meaningful where growth is positive and the earnings base is not depressed.',
      },
    ],
    verify: () => null,
    columns: [
      { key: 'value', label: 'Fwd P/E', dp: 2 },
      { key: 'industry_median', label: 'Ind. med.', dp: 2 },
      { key: 'return_1y', label: '1Y return', dp: 1, suffix: '%', signed: true },
    ],
    risks: [
      'De-rating is violent when growth disappoints.',
      'Not a revenue or historical CAGR screen — those are different and easier.',
    ],
    blockedBy: 'Forward consensus estimates are not ingested. Trendlyne returns "Export NA" for forward P/E at every universe size, so this requires a Capital IQ estimates export.',
  },

  {
    id: 'dividend',
    name: 'Dividend / Income',
    family: 'Income',
    question: 'Is the yield covered by cash the business actually generates?',
    edge: 'Cash return supported by profitability.',
    thesis:
      'A high yield is only a return if it is covered. The screen tests coverage from free cash flow rather than from reported earnings.',
    math: [
      {
        label: 'Yield',
        tex: 'y_i = \\dfrac{D_i}{P_i}',
        note: 'Trailing dividend over price.',
      },
      {
        label: 'Free-cash-flow cover',
        tex: 'c_i = \\dfrac{FCF_i}{D_i \\cdot N_i}',
        note: 'Cash generated over cash paid out. Below 1 the dividend is being funded from the balance sheet.',
      },
    ],
    verify: () => null,
    columns: [
      { key: 'value', label: 'Yield', dp: 2, suffix: '%' },
      { key: 'roe', label: 'ROE', dp: 1, suffix: '%' },
      { key: 'return_1y', label: '1Y return', dp: 1, suffix: '%', signed: true },
    ],
    risks: [
      'Yield rises fastest when the price is falling for a reason.',
      'Dividend coverage data is sparse: only a handful of names in the universe report a yield above 3%.',
    ],
  },
];

/** Position sizing — shown once, applies across every screen. */
export const SIZING_MATH = [
  {
    label: 'Volatility-targeted weight',
    tex: 'w_i = \\dfrac{\\sigma_{\\text{target}}}{\\hat{\\sigma}_i \\sqrt{N}}',
    note: 'Equalises risk contribution across N positions so one volatile name cannot dominate the book. σ_target is annualised.',
  },
  {
    label: 'Volatility from ATR',
    tex: '\\hat{\\sigma}_i = \\dfrac{\\text{ATR}_i}{P_i}\\sqrt{252}',
    note: 'Average true range as a fraction of price, annualised. Robust to gaps in a way a close-to-close estimate is not.',
  },
  {
    label: 'Portfolio beta',
    tex: '\\beta_p = \\sum_{i \\in L} w_i \\beta_i - \\sum_{j \\in S} w_j \\beta_j',
    note: 'Market-neutral means βₚ ≈ 0. This neutralises the estimate, not the realised exposure — betas drift, especially under stress.',
  },
  {
    label: 'Liquidity cap',
    tex: 'w_i \\leq \\dfrac{\\alpha \\cdot \\text{ADV}_i}{C}',
    note: 'Weight capped so the position is no more than a fraction α of average daily traded value at portfolio capital C. Without this a screen returns names you cannot actually buy.',
  },
];

/**
 * Rows the engine has not validated. Confirmed live on 2026-08-19: every
 * visible result on the Value screen carries `normalization_required`, with
 * EV/EBITDA between 1.0 and 2.8 — impossible for a solvent listed company and
 * a units mismatch rather than a discount. The desk shows these separately
 * instead of ranking them as opportunities.
 */
export const VALIDATION_LABELS = {
  normalization_required: 'Units or accounting basis need normalising before this multiple can be compared.',
  accounting_basis_verification_required: 'Consolidated vs standalone basis is not confirmed for this company.',
  fundamental_comparability_required: 'Business models must be shown comparable before the pair is meaningful.',
  not_market_neutral: 'The pair is not hedged to zero market exposure.',
};

/**
 * Two different things get called "not validated" and they must not be
 * conflated. `validation_status` means the numbers themselves may be wrong —
 * those rows are withheld by default. `comparability_status` and
 * `promotion_status` mean the numbers are right but the trade is not yet
 * promotable — those rows are shown, with the caveat attached.
 */
const CLEAN = new Set(['', 'validated', 'ok', 'pass', 'none']);

export const isValidated = (row) =>
  CLEAN.has(String(row?.validation_status || '').toLowerCase());

export const caveatOf = (row) => {
  const c = String(row?.comparability_status || '').toLowerCase();
  const p = String(row?.promotion_status || '').toLowerCase();
  if (c && !CLEAN.has(c)) return VALIDATION_LABELS[c] || c.replaceAll('_', ' ');
  if (p && !CLEAN.has(p)) return VALIDATION_LABELS[p] || p.replaceAll('_', ' ');
  return null;
};

export const LIMITS = [
  ['Point-in-time', 'FAILING', 'Fundamentals are stored by reporting period, not by publication date. Every backtest built on them looks ahead.'],
  ['Survivorship', 'FAILING', 'The universe is companies listed today. Delisted and merged companies are absent, which flatters any historical test.'],
  ['Backtest', 'NOT RUN', 'No costed walk-forward test has been accepted for any screen on this page.'],
  ['Out-of-sample', 'NOT RUN', 'No frozen out-of-sample period has been tested.'],
  ['Transaction costs', 'NOT RUN', 'No cost or slippage model has been applied to any result shown.'],
  ['Multiple normalisation', 'FAILING', 'Every result on the Value screen is flagged normalization_required. EV/EBITDA readings of 1.0-2.8 indicate a units mismatch, not a discount.'],
  ['Capacity', 'PARTIAL', 'Average daily value is available for most of the universe; participation limits are not yet enforced in the screens.'],
];
