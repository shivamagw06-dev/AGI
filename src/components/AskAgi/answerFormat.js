const FORMATS = {
  comparison: { label: 'Comparison', evidenceTitle: 'Verified comparison evidence', thesis: false, scenarios: false, bottomLine: 'Comparison takeaway' },
  financials: { label: 'Financial performance', evidenceTitle: 'Financial evidence', thesis: true, scenarios: false, bottomLine: 'Financial takeaway' },
  valuation: { label: 'Valuation', evidenceTitle: 'Valuation evidence', thesis: true, scenarios: false, bottomLine: 'Valuation takeaway' },
  catalysts: { label: 'Catalysts & risks', evidenceTitle: 'Catalysts and risks', thesis: false, scenarios: true, bottomLine: 'What to monitor' },
  sector: { label: 'Sector & macro', evidenceTitle: 'Sector and macro evidence', thesis: false, scenarios: true, bottomLine: 'Sector takeaway' },
  portfolio: { label: 'Portfolio context', evidenceTitle: 'Portfolio evidence', thesis: false, scenarios: true, bottomLine: 'Portfolio takeaway' },
  trading: { label: 'Market setup', evidenceTitle: 'Market evidence', thesis: false, scenarios: true, bottomLine: 'Risk controls' },
  company: { label: 'Company quality', evidenceTitle: 'Company evidence', thesis: true, scenarios: true, bottomLine: 'Investment takeaway' },
};

export function answerFormatFor(question = '', intent = '') {
  const q = `${question} ${intent}`.toLowerCase();
  if (/compare|\bvs\b|versus/.test(q)) return { key: 'comparison', ...FORMATS.comparison };
  if (/p\/?e|p\/?b|valuation|expensive|cheap|priced|multiple/.test(q)) return { key: 'valuation', ...FORMATS.valuation };
  if (/quarter|result|earnings|revenue|profit|margin|cash flow|debt|financial/.test(q)) return { key: 'financials', ...FORMATS.financials };
  if (/catalyst|risk|what could|upcoming|event/.test(q)) return { key: 'catalysts', ...FORMATS.catalysts };
  if (/sector|macro|rates|inflation|rbi|market outlook/.test(q)) return { key: 'sector', ...FORMATS.sector };
  if (/portfolio|allocation|exposure|diversif|concentration/.test(q)) return { key: 'portfolio', ...FORMATS.portfolio };
  if (/trade|momentum|technical|support|resistance|timing/.test(q)) return { key: 'trading', ...FORMATS.trading };
  return { key: 'company', ...FORMATS.company };
}
