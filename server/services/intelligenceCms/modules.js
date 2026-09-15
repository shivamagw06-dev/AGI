/** Intelligence CMS — module registry. Valuation Monitor is the first dataset. */

export const RECORD_STATUSES = ['draft', 'review', 'published', 'archived'];

export const RELATION_TYPES = [
  'company',
  'industry',
  'pe_firm',
  'article',
  'transaction',
  'fund',
  'person',
  'comparable',
];

export const INTELLIGENCE_MODULES = {
  valuation_monitor: {
    id: 'valuation_monitor',
    label: 'Valuation Monitor',
    slug: 'valuation-monitor',
    description: 'Private market valuation multiples and AGI research ratings.',
    publicPath: '/private-markets#valuation-monitor',
    columns: [
      { key: 'company', label: 'Company', type: 'text', required: true, grid: true },
      { key: 'sector', label: 'Sector', type: 'text', grid: true },
      { key: 'ev_revenue', label: 'EV/Revenue', type: 'text', grid: true },
      { key: 'ev_ebitda', label: 'EV/EBITDA', type: 'text', grid: true },
      { key: 'pe_ratio', label: 'P/E', type: 'text', grid: true },
      { key: 'growth', label: 'Growth', type: 'text', grid: true },
      { key: 'margin', label: 'Margin', type: 'text', grid: true },
      { key: 'geography', label: 'Geography', type: 'text', grid: true },
      { key: 'comment', label: 'Comment', type: 'text', grid: true },
      { key: 'agi_rating', label: 'AGI Rating', type: 'text', grid: true },
      { key: 'analyst', label: 'Analyst', type: 'text', grid: true },
    ],
    detailFields: [
      { key: 'commentary', label: 'Investment commentary', type: 'textarea' },
      { key: 'risks', label: 'Risks', type: 'textarea' },
      { key: 'comparables', label: 'Comparable companies', type: 'textarea' },
      { key: 'historical_multiples', label: 'Historical multiples', type: 'textarea' },
      { key: 'chart_url', label: 'Chart URL', type: 'text' },
      { key: 'supporting_research', label: 'Supporting research', type: 'textarea' },
      { key: 'ai_draft', label: 'AI draft (optional)', type: 'textarea' },
    ],
    enabled: true,
  },
  transactions: {
    id: 'transactions',
    label: 'Recent Transactions',
    slug: 'transactions',
    description: 'M&A and private market transactions shown on the Private Markets page.',
    publicPath: '/private-markets#recent-transactions',
    columns: [
      { key: 'date', label: 'Date', type: 'text', grid: true },
      { key: 'target', label: 'Target', type: 'text', required: true, grid: true },
      { key: 'buyer', label: 'Buyer', type: 'text', grid: true },
      { key: 'seller', label: 'Seller', type: 'text', grid: true },
      { key: 'enterprise_value', label: 'Enterprise Value', type: 'text', grid: true },
      { key: 'deal_value', label: 'Deal Value', type: 'text', grid: true },
      { key: 'industry', label: 'Sector', type: 'text', grid: true },
      { key: 'country', label: 'Country', type: 'text', grid: true },
      { key: 'status', label: 'Status', type: 'text', grid: true },
    ],
    detailFields: [
      { key: 'summary', label: 'Deal summary', type: 'textarea' },
      { key: 'commentary', label: 'AGI commentary', type: 'textarea' },
    ],
    enabled: true,
  },
  pe_firms: {
    id: 'pe_firms',
    label: 'Private Equity Firms',
    slug: 'pe-firms',
    description: 'Global private equity firm registry.',
    columns: [
      { key: 'name', label: 'Firm', type: 'text', required: true, grid: true },
      { key: 'aum', label: 'AUM', type: 'text', grid: true },
      { key: 'hq', label: 'HQ', type: 'text', grid: true },
      { key: 'strategy', label: 'Strategy', type: 'text', grid: true },
    ],
    detailFields: [{ key: 'overview', label: 'Overview', type: 'textarea' }],
    enabled: false,
  },
  portfolio_companies: {
    id: 'portfolio_companies',
    label: 'Portfolio Companies',
    slug: 'portfolio-companies',
    description: 'PE-backed portfolio company registry.',
    columns: [
      { key: 'company', label: 'Company', type: 'text', required: true, grid: true },
      { key: 'pe_firm', label: 'PE Firm', type: 'text', grid: true },
      { key: 'sector', label: 'Sector', type: 'text', grid: true },
      { key: 'country', label: 'Country', type: 'text', grid: true },
    ],
    detailFields: [{ key: 'notes', label: 'Notes', type: 'textarea' }],
    enabled: false,
  },
  funds: {
    id: 'funds',
    label: 'Funds',
    slug: 'funds',
    description: 'Private market fund intelligence.',
    columns: [
      { key: 'name', label: 'Fund', type: 'text', required: true, grid: true },
      { key: 'gp', label: 'GP', type: 'text', grid: true },
      { key: 'vintage', label: 'Vintage', type: 'text', grid: true },
      { key: 'fund_size', label: 'Fund Size', type: 'text', grid: true },
    ],
    detailFields: [{ key: 'strategy', label: 'Strategy', type: 'textarea' }],
    enabled: false,
  },
  industries: {
    id: 'industries',
    label: 'Industries',
    slug: 'industries',
    description: 'Industry intelligence modules.',
    columns: [
      { key: 'name', label: 'Industry', type: 'text', required: true, grid: true },
      { key: 'market_size', label: 'Market Size', type: 'text', grid: true },
    ],
    detailFields: [{ key: 'overview', label: 'Overview', type: 'textarea' }],
    enabled: false,
  },
  people: {
    id: 'people',
    label: 'People',
    slug: 'people',
    description: 'Executives, partners, and deal professionals.',
    columns: [
      { key: 'name', label: 'Name', type: 'text', required: true, grid: true },
      { key: 'title', label: 'Title', type: 'text', grid: true },
      { key: 'firm', label: 'Firm', type: 'text', grid: true },
    ],
    detailFields: [{ key: 'bio', label: 'Biography', type: 'textarea' }],
    enabled: false,
  },
  editors_desk: {
    id: 'editors_desk',
    label: "Editor's Desk",
    slug: 'editors-desk',
    description: 'Daily institutional editor notes.',
    columns: [
      { key: 'title', label: 'Title', type: 'text', required: true, grid: true },
      { key: 'date', label: 'Date', type: 'text', grid: true },
    ],
    detailFields: [{ key: 'body', label: 'Editor note', type: 'textarea' }],
    enabled: false,
  },
};

export function getModule(moduleId) {
  return INTELLIGENCE_MODULES[moduleId] || null;
}

export function listModules({ enabledOnly = false } = {}) {
  return Object.values(INTELLIGENCE_MODULES).filter((m) => !enabledOnly || m.enabled);
}

export function gridColumns(moduleId) {
  const mod = getModule(moduleId);
  if (!mod) return [];
  return (mod.columns || []).filter((c) => c.grid !== false);
}
