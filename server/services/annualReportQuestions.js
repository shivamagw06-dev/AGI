/**
 * The hundred questions an underwriter asks of an annual report.
 *
 * Written down as a register rather than a pipeline, because the honest answer
 * to most of them today is "not from this document, and here is what it would
 * take". A page that shows ninety-three blanks with reasons is worth more than
 * one that shows a hundred answers, seventy of which were guessed.
 *
 * Three kinds, because three different machines answer them.
 *
 *   stated    - the document says it in a sentence. The existing chain finds
 *               these, and each answer carries the sentence it came from.
 *   computed  - arithmetic over financial-statement line items across years.
 *               Deterministic and checkable once the statements are stored,
 *               and impossible before: AGI holds one snapshot per ticker
 *               (revenue, EBITDA, market cap, enterprise value) and no
 *               receivables, inventories, capex, debt schedule or share count.
 *   judgment  - a conclusion drawn across disclosures, which no sentence
 *               states and no formula yields. Needs a model and a reviewer.
 *
 * Question 100 is the whole point and the reason the order matters: it is a
 * function of the other ninety-nine, so it cannot be answered first, and a
 * system that answers it without them is guessing with a confident voice.
 */

const stated = (n, ask, note) => ({ n, ask, kind: 'stated', note: note || null });
const computed = (n, ask, needs, formula) => ({ n, ask, kind: 'computed', needs, formula: formula || null });
const judgment = (n, ask, note) => ({ n, ask, kind: 'judgment', note });

export const QUESTIONS = [
  stated(1, 'What does the company actually sell?'),
  stated(2, 'How does the company make money?'),
  stated(3, 'What are the major business segments?'),
  computed(4, 'Which segment is the largest contributor to revenue?', ['segment_revenue']),
  computed(5, 'Which segment is the largest contributor to EBIT/EBITDA?', ['segment_ebit']),
  computed(6, 'Which segment is growing fastest?', ['segment_revenue'], 'yoy by segment'),
  computed(7, 'Which segment is shrinking?', ['segment_revenue'], 'yoy by segment'),
  computed(8, 'Which segment earns the highest margins?', ['segment_revenue', 'segment_ebit'], 'segment_ebit / segment_revenue'),
  computed(9, 'What percentage of revenue is recurring?', ['revenue', 'recurring_revenue']),
  stated(10, 'How concentrated is the revenue base?'),
  computed(11, 'What was revenue growth this year?', ['revenue'], 'revenue / prior_revenue - 1'),
  computed(12, 'What is the 3-year and 5-year revenue CAGR?', ['revenue'], '(revenue / revenue_n)^(1/n) - 1'),
  stated(13, 'Was growth organic or acquisition-driven?'),
  computed(14, 'How much growth came from price increases?', ['price_volume_bridge']),
  computed(15, 'How much growth came from volume?', ['price_volume_bridge']),
  computed(16, 'How much came from mix changes?', ['price_volume_bridge']),
  computed(17, 'How much growth came from FX translation?', ['fx_effect']),
  stated(18, "What is management's explanation for revenue growth/decline?", 'the why step answers this directly'),
  computed(19, 'Are reported sales accelerating or decelerating?', ['revenue'], 'growth this year vs growth last year'),
  stated(20, 'How seasonal is revenue?'),
  computed(21, 'What is gross margin?', ['revenue', 'cost_of_sales'], '(revenue - cost_of_sales) / revenue'),
  computed(22, 'How has gross margin changed YoY?', ['revenue', 'cost_of_sales']),
  computed(23, 'What is EBITDA margin?', ['revenue', 'ebitda'], 'ebitda / revenue'),
  computed(24, 'What is EBIT margin?', ['revenue', 'ebit'], 'ebit / revenue'),
  computed(25, 'What is net profit margin?', ['revenue', 'net_income'], 'net_income / revenue'),
  computed(26, 'Which costs are rising faster than revenue?', ['revenue', 'cost_lines']),
  computed(27, 'What proportion of costs are fixed versus variable?', ['cost_lines'], 'regression across periods'),
  computed(28, 'Does operating leverage exist?', ['revenue', 'ebit']),
  computed(29, 'What is incremental EBITDA margin?', ['revenue', 'ebitda'], 'delta ebitda / delta revenue'),
  stated(30, 'What does management say caused margin expansion/contraction?', 'the why step answers this directly'),
  computed(31, 'What is reported EBITDA?', ['ebitda']),
  judgment(32, 'What is normalized EBITDA?', 'requires deciding which charges recur, which is question 33'),
  judgment(33, 'Which "exceptional" costs should actually be treated as recurring?',
    'a judgement about management\'s framing, not a fact the document states'),
  computed(34, 'What share-based compensation has been excluded from adjusted earnings?', ['share_based_comp', 'adjustments']),
  stated(35, 'What restructuring charges occurred?'),
  stated(36, 'What acquisition-related costs occurred?'),
  stated(37, 'Were there asset impairments?', 'impairment is already a named metric'),
  stated(38, 'Were there one-time gains boosting profit?'),
  computed(39, 'Is adjusted EBITDA materially higher than statutory operating profit?', ['ebitda', 'adjusted_ebitda', 'operating_profit']),
  judgment(40, 'How aggressively does management use non-GAAP/adjusted metrics?',
    'a characterisation of a pattern across the document'),
  computed(41, 'How much operating cash flow did the company generate?', ['operating_cash_flow']),
  computed(42, 'How much free cash flow did it generate?', ['operating_cash_flow', 'capex'], 'operating_cash_flow - capex'),
  computed(43, 'What is EBITDA-to-FCF conversion?', ['ebitda', 'operating_cash_flow', 'capex']),
  computed(44, 'What is PAT-to-CFO conversion?', ['net_income', 'operating_cash_flow'], 'operating_cash_flow / net_income'),
  stated(45, 'Why does cash flow differ from accounting earnings?', 'the why step answers this where management explains it'),
  computed(46, 'How much cash is tied up in working capital?', ['receivables', 'inventories', 'payables']),
  computed(47, 'Are receivables growing faster than sales?', ['receivables', 'revenue']),
  computed(48, 'Are inventories growing faster than sales?', ['inventories', 'revenue']),
  computed(49, 'Are payables being stretched?', ['payables', 'cost_of_sales'], 'days payable outstanding'),
  computed(50, 'Is working capital structurally improving or deteriorating?', ['receivables', 'inventories', 'payables', 'revenue']),
  stated(51, 'What is maintenance capex?', 'rarely disclosed; where it is not, this becomes a judgement'),
  stated(52, 'What is growth capex?'),
  computed(53, 'What percentage of revenue is capex?', ['capex', 'revenue'], 'capex / revenue'),
  stated(54, 'Where is capex being spent?'),
  stated(55, 'What capacity is being added?'),
  stated(56, 'When will new capacity become operational?', 'the expectations step answers this where management states a date'),
  stated(57, 'What utilization is existing capacity running at?'),
  stated(58, 'What returns does management expect from new capex?', 'the expectations step answers this where management states a number'),
  computed(59, 'Is depreciation materially below capex?', ['depreciation', 'capex']),
  judgment(60, 'Is the company underinvesting to artificially boost FCF?',
    'a conclusion from questions 51, 53 and 59 read against the business'),
  computed(61, 'How much gross debt does the company have?', ['gross_debt']),
  computed(62, 'How much cash does it have?', ['cash']),
  computed(63, 'What is net debt?', ['gross_debt', 'cash'], 'gross_debt - cash'),
  computed(64, 'What is Net Debt/EBITDA?', ['gross_debt', 'cash', 'ebitda'], '(gross_debt - cash) / ebitda'),
  computed(65, 'What is interest coverage?', ['ebit', 'interest_expense'], 'ebit / interest_expense'),
  stated(66, 'What is the weighted-average interest rate?'),
  stated(67, 'What proportion of debt is floating-rate?'),
  stated(68, 'When does the debt mature?'),
  computed(69, 'Are there significant maturities within 1-3 years?', ['debt_schedule']),
  stated(70, 'What financial covenants apply to the debt?'),
  computed(71, 'What has management done with free cash flow?', ['capex', 'acquisitions', 'dividends', 'buybacks']),
  computed(72, 'How much was reinvested into the core business?', ['capex']),
  computed(73, 'How much was spent on acquisitions?', ['acquisitions']),
  computed(74, 'How much was returned through dividends?', ['dividends']),
  computed(75, 'How much was used for share buybacks?', ['buybacks']),
  computed(76, 'Were shares issued despite buybacks?', ['shares_issued', 'buybacks']),
  computed(77, 'Has the share count increased or decreased?', ['share_count']),
  judgment(78, 'What historical returns has management generated on acquisitions?',
    'requires tracking each acquisition against later segment results, across years of documents'),
  computed(79, 'What is ROIC?', ['ebit', 'tax_rate', 'invested_capital'], 'ebit * (1 - tax_rate) / invested_capital'),
  computed(80, "Is ROIC above the company's cost of capital?", ['ebit', 'tax_rate', 'invested_capital', 'cost_of_capital']),
  stated(81, 'Who are the company\'s major customers?'),
  stated(82, 'What percentage of sales comes from the largest customer?'),
  stated(83, 'How concentrated are the top 5/top 10 customers?'),
  stated(84, 'Are important contracts coming up for renewal?'),
  stated(85, 'What is customer retention/churn where disclosed?'),
  stated(86, 'Who are the major suppliers?'),
  stated(87, 'Is the company dependent on any single supplier?'),
  stated(88, 'Does the company possess pricing power?', 'stated where management claims it; proving it is question 90'),
  stated(89, 'What competitive advantage does management claim?'),
  judgment(90, 'Is there evidence supporting that competitive advantage?',
    'weighing a claim against the numbers elsewhere in the document'),
  stated(91, "What are management's stated strategic priorities?"),
  judgment(92, 'What KPIs does management emphasize - and have those KPIs changed?',
    'requires the prior year\'s document to compare against'),
  judgment(93, 'What targets did management previously promise, and did they deliver?',
    'requires the prior year\'s stated expectations read against this year\'s results'),
  stated(94, 'What are the biggest risks disclosed by management?', 'the risks step answers this directly'),
  stated(95, 'What litigation, regulatory, tax or contingent liabilities exist?'),
  stated(96, 'What related-party transactions exist?'),
  stated(97, 'How much are executives paid and how are incentives structured?'),
  stated(98, 'How much stock do insiders/promoters own, pledge, buy, or sell?'),
  stated(99, 'What assumptions in accounting policies could materially change earnings?'),
  judgment(100, 'After normalizing earnings, debt, capex and risks, what is the business actually worth?',
    'a function of the other ninety-nine; answering it first is guessing in a confident voice'),
];

/** Every line item the computed questions need, deduplicated. */
export function lineItemsNeeded() {
  const needed = new Set();
  for (const question of QUESTIONS) {
    for (const item of question.needs || []) needed.add(item);
  }
  return [...needed].sort();
}

/** How the hundred divide. */
export function byKind() {
  const counts = { stated: 0, computed: 0, judgment: 0 };
  for (const question of QUESTIONS) counts[question.kind] += 1;
  return counts;
}
