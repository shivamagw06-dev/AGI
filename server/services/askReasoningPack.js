const clean = (value = '') => String(value).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

const INDUSTRIES = [
  { key: 'telecom', pattern: /\b(telecom|airtel|jio|vodafone|arpu|subscriber|tariff|spectrum|churn)\b/i },
  { key: 'defence', pattern: /\b(defence|defense|zen technologies|simulator|anti-drone|armed forces|ministry of defence)\b/i },
  { key: 'banking', pattern: /\b(bank|banking|nim|casa|deposit|loan|credit cost|gnpa|nnpa)\b/i },
  { key: 'information_technology', pattern: /\b(it services|software|saas|deal wins?|attrition|billing rate)\b/i },
  { key: 'consumer', pattern: /\b(fmcg|consumer|volume growth|distribution|same-store|pricing power)\b/i },
  { key: 'industrials', pattern: /\b(order book|epc|capital goods|engineering|execution|working capital)\b/i },
];

const EVENT_TYPES = [
  { key: 'pricing', pattern: /\b(tariff|price increase|pricing|realisation|asp)\b/i },
  { key: 'order_win', pattern: /\b(order|contract|tender|award|win)\b/i },
  { key: 'earnings', pattern: /\b(results?|earnings|revenue|ebitda|margin|profit|guidance)\b/i },
  { key: 'policy', pattern: /\b(policy|regulation|rbi|sebi|government|ministry|rate cut|rate hike)\b/i },
  { key: 'capital_allocation', pattern: /\b(capex|acquisition|buyback|dividend|debt|fundrais)\w*\b/i },
];

const QUESTION_TYPES = [
  { key: 'causal_analysis', pattern: /\b(why|how|impact|affect|change|mean for|so what)\b/i },
  { key: 'risk_analysis', pattern: /\b(risk|downside|wrong|break|concern)\b/i },
  { key: 'investment_view', pattern: /\b(view|thesis|outlook|opportunity|invest)\w*\b/i },
  { key: 'factual', pattern: /\b(what happened|how much|when|where)\b/i },
];

const TRANSMISSION = {
  'telecom:pricing': {
    chain: ['Tariff or plan-price change', 'Realised ARPU', 'Revenue per subscriber', 'Operating leverage and EBITDA', 'Free cash flow and valuation'],
    condition: 'The benefit depends on customer retention, competitor response and the mix of customers migrating to higher-priced plans.',
    counter: 'Higher customer cost can increase churn or slow subscriber additions, offsetting part of the ARPU benefit.',
    metrics: ['ARPU', 'subscriber additions', 'churn', 'competitor pricing', 'EBITDA margin', 'free cash flow'],
  },
  'defence:order_win': {
    chain: ['Contract award', 'Executable order book', 'Revenue conversion', 'Project margin and working capital', 'Cash conversion, earnings and valuation'],
    condition: 'The award creates value only as milestones are executed on time, accepted by the customer and converted into cash.',
    counter: 'Delivery delays, lower project margins, receivable build-up or a non-recurring order mix can weaken the apparent benefit.',
    metrics: ['order book', 'execution schedule', 'revenue conversion', 'EBITDA margin', 'receivables', 'operating cash flow'],
  },
  'banking:policy': {
    chain: ['Policy or liquidity change', 'Funding and lending rates', 'Credit demand and net interest margin', 'Credit costs and profit', 'ROA, ROE and price-to-book valuation'],
    condition: 'Deposit repricing, loan mix, liquidity and asset quality determine the magnitude and timing of transmission.',
    counter: 'Faster deposit repricing or weaker borrower quality can offset the benefit from stronger credit demand.',
    metrics: ['deposit growth', 'CASA', 'loan growth', 'NIM', 'slippages', 'credit cost', 'ROA'],
  },
  'industrials:order_win': {
    chain: ['Order intake', 'Order book visibility', 'Execution and revenue recognition', 'Margin and working-capital absorption', 'Cash flow, ROIC and valuation'],
    condition: 'Value depends on execution capacity, contract terms, input costs and payment milestones.',
    counter: 'A growing order book can destroy value when margins are weak or receivables and inventory absorb cash.',
    metrics: ['order inflow', 'book-to-bill', 'execution', 'gross margin', 'receivable days', 'operating cash flow'],
  },
};

function firstMatch(rows, text, fallback) {
  return rows.find(({ pattern }) => pattern.test(text))?.key || fallback;
}

export function planPublishedResearchQuestion(question, article = {}) {
  const source = clean(`${question} ${article.title || ''} ${article.tags || ''} ${article.section || ''} ${article.excerpt || ''} ${article.content_md || article.content || ''}`);
  const industry = firstMatch(INDUSTRIES, source, 'general_corporate');
  const eventType = firstMatch(EVENT_TYPES, source, 'company_development');
  const questionType = firstMatch(QUESTION_TYPES, question, 'investment_view');
  return {
    question_type: questionType,
    industry,
    event_type: eventType,
    time_horizon: /\b(today|current|latest|recent|now)\b/i.test(question) ? 'current' : 'medium_term',
    required_analysis: ['what_happened', 'why_it_matters', 'transmission_mechanism', 'financial_impact', 'counter_case', 'what_to_watch'],
  };
}

export function buildPublishedReasoningPack(question, article = {}, analysis = {}) {
  const plan = planPublishedResearchQuestion(question, article);
  const template = TRANSMISSION[`${plan.industry}:${plan.event_type}`] || {
    chain: ['Company development', 'Operating driver', 'Revenue or cost impact', 'Cash flow and balance-sheet impact', 'Earnings and valuation'],
    condition: 'The magnitude and timing depend on execution, competitive response and the company’s financial starting point.',
    counter: 'The headline may not create economic value if it does not improve sustainable cash flow or returns on capital.',
    metrics: ['revenue growth', 'margin', 'working capital', 'operating cash flow', 'ROIC', 'valuation'],
  };
  const summary = clean(analysis.summary || article.excerpt || article.title);
  return {
    planner: plan,
    reasoning_framework: {
      what: summary,
      why: template.condition,
      how: template.chain,
      so_what: `The investment relevance depends on whether the operating change reaches cash flow and sustainable earnings, rather than remaining only a headline development.`,
      what_next: `Test the thesis against ${template.metrics.slice(0, 4).join(', ')} as new disclosures arrive.`,
      what_could_go_wrong: template.counter,
    },
    financial_transmission: template.chain,
    affected_metrics: template.metrics,
    conditions: [template.condition],
    counter_case: [template.counter],
    evidence_boundary: {
      facts: [summary],
      inferences: [...template.chain.slice(1), template.condition, template.counter],
      quantified_impact_available: false,
      note: 'The causal pathway is an AGI analytical framework. A quantified impact requires company inputs and must not be inferred from the headline alone.',
    },
  };
}
