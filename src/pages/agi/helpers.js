/** Product-facing helpers — never expose engine module IDs in UI copy. */

export const NAV_ITEMS = [
  { to: '/agi', label: 'Dashboard', end: true },
  { to: '/agi/ask', label: 'Ask AGI' },
  { to: '/agi/companies', label: 'Companies' },
  { to: '/agi/portfolio', label: 'Investment Office' },
  { to: '/agi/committee', label: 'Committee' },
  { to: '/agi/markets', label: 'Markets' },
  { to: '/agi/research', label: 'Research' },
  { to: '/agi/watchlists', label: 'Watchlists' },
  { to: '/agi/screeners', label: 'Screeners' },
  { to: '/agi/notebook', label: 'Notebook' },
  { to: '/agi/alerts', label: 'Alerts' },
  { to: '/agi/settings', label: 'Settings' },
];

export const COMPANY_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'decision', label: 'Decision' },
  { id: 'knowledge_graph', label: 'Knowledge Graph' },
  { id: 'forecast', label: 'Forecast' },
  { id: 'observations', label: 'Observations' },
  { id: 'business_quality', label: 'Business Quality' },
  { id: 'financial_trends', label: 'Financials' },
  { id: 'business_strategy', label: 'Strategy' },
  { id: 'management_execution', label: 'Execution' },
  { id: 'evidence_references', label: 'Evidence' },
  { id: 'research_notes', label: 'Research Notes' },
  { id: 'historical_timeline', label: 'Timeline' },
  { id: 'portfolio_references', label: 'Portfolio' },
  { id: 'watchlist_status', label: 'Watchlists' },
];

export const ASK_PROMPTS = [
  'Should I worry about Kotak?',
  'Explain TCS margins.',
  'Compare ICICI with HDFC.',
  "Summarise today's market.",
  'What changed since yesterday?',
  'Explain RBI policy.',
];

export function greetingForNow(date = new Date()) {
  const h = date.getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export function sectionByKey(workspace, key) {
  const sections = workspace?.sections || workspace?.response?.sections || [];
  if (!Array.isArray(sections)) return null;
  return sections.find((s) => String(s?.key || '').toLowerCase() === String(key).toLowerCase()) || null;
}

export function boardOf(section) {
  return section?.board && typeof section.board === 'object' ? section.board : {};
}

export function firstBlockText(section) {
  const blocks = section?.blocks;
  if (!Array.isArray(blocks) || !blocks.length) return '';
  return String(blocks[0]?.text || blocks[0]?.content || '').trim();
}

export function formatPct(value, digits = 0) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  if (n <= 1 && n >= 0) return `${(n * 100).toFixed(digits)}%`;
  return `${n.toFixed(digits)}%`;
}

export function formatConfidence(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  if (n <= 1) return n.toFixed(2);
  return String(n);
}

export function coverageLabel(coverage) {
  if (!coverage || typeof coverage !== 'object') return 'Unknown';
  const ratio = Number(coverage.ratio);
  if (Number.isNaN(ratio)) return 'Unknown';
  if (ratio >= 0.85) return 'Full coverage';
  if (ratio >= 0.5) return 'Partial coverage';
  if (ratio > 0) return 'Limited coverage';
  return 'No coverage';
}

export function researchStatusTone(status) {
  const s = String(status || '').toLowerCase();
  if (!s || s.includes('no research')) return 'muted';
  if (s.includes('complete') || s.includes('available') || s.includes('published')) return 'ok';
  return 'warn';
}

/** Strip engine jargon from user-visible strings. */
export function productizeText(text) {
  return String(text || '')
    .replace(/\bFIRE-\d+\b/gi, 'intelligence')
    .replace(/\b(CW|IO|WO|PO|PEB|FSE|FKB)-\d+\b/gi, 'module')
    .replace(/\bOffice\s+SDK\b/gi, 'platform')
    .replace(/\bpass-through from intelligence\b/gi, 'assembled from research layers')
    .trim();
}

export function eventLabel(event) {
  const raw = String(event?.event_type || event?.summary || 'Update');
  const map = {
    annual_report: 'Annual Report',
    conference_call: 'Conference Call',
    capital_allocation: 'Capital Allocation',
    research_update: 'Research Update',
    execution_update: 'Execution Update',
    filing: 'Filing',
    earnings: 'Earnings',
  };
  const key = raw.toLowerCase().replace(/[^a-z0-9]+/g, '_');
  for (const [k, v] of Object.entries(map)) {
    if (key.includes(k)) return v;
  }
  return productizeText(raw.replace(/[._]/g, ' ')).replace(/\b\w/g, (c) => c.toUpperCase());
}

export function pickMarketStrip(intelligence) {
  const pulse = intelligence?.pulse || {};
  const indices = Array.isArray(intelligence?.indexSentiments) ? intelligence.indexSentiments : [];
  const byName = (re) => indices.find((i) => re.test(String(i?.name || i?.label || '')));

  const nifty = byName(/nifty/i) || null;
  const bank = byName(/bank/i) || null;

  const row = (label, source, fallbackValue = '—') => ({
    label,
    value: source?.value ?? source?.level ?? source?.price ?? fallbackValue,
    delta: source?.change ?? source?.changePct ?? source?.pct ?? source?.sentiment ?? '',
    direction: String(source?.direction || source?.bias || '').toLowerCase(),
  });

  return [
    row('NIFTY', nifty || pulse?.nifty, pulse?.nifty ?? '—'),
    row('Bank Nifty', bank || pulse?.bankNifty, pulse?.bankNifty ?? '—'),
    row('US Futures', pulse?.usFutures || pulse?.us, 'Watch'),
    row('Dollar', pulse?.dollar || pulse?.dxy, 'Watch'),
    row('Brent', pulse?.brent || pulse?.oil, 'Watch'),
    row('Gold', pulse?.gold, 'Watch'),
  ];
}
