/** Universal entity types for the Intelligence Platform. */

export const ENTITY_TYPES = {
  pe_firm: { label: 'Firm', plural: 'Firms', searchGroup: 'Private Equity Firms' },
  general_partner: { label: 'General Partner', plural: 'General Partners', searchGroup: 'Private Equity Firms' },
  limited_partner: { label: 'Limited Partner', plural: 'Limited Partners', searchGroup: 'Investors' },
  investor: { label: 'Investor', plural: 'Investors', searchGroup: 'Investors' },
  company: { label: 'Company', plural: 'Companies', searchGroup: 'Companies' },
  portfolio_company: { label: 'Portfolio Company', plural: 'Portfolio Companies', searchGroup: 'Portfolio Companies' },
  fund: { label: 'Fund', plural: 'Funds', searchGroup: 'Funds' },
  transaction: { label: 'Transaction', plural: 'Transactions', searchGroup: 'Transactions' },
  industry: { label: 'Industry', plural: 'Industries', searchGroup: 'Industries' },
  person: { label: 'Person', plural: 'People', searchGroup: 'People' },
  article: { label: 'Article', plural: 'Articles', searchGroup: 'Articles' },
  news: { label: 'News', plural: 'News', searchGroup: 'News' },
  location: { label: 'Location', plural: 'Locations', searchGroup: 'Locations' },
};

/** Node colors for knowledge graph — institutional palette. */
export const NODE_COLORS = {
  pe_firm: '#0B3B60',
  general_partner: '#0B3B60',
  limited_partner: '#475569',
  investor: '#475569',
  company: '#1D6B4F',
  portfolio_company: '#1D6B4F',
  fund: '#B8860B',
  transaction: '#B91C1C',
  industry: '#C2410C',
  person: '#6D28D9',
  article: '#64748B',
  news: '#64748B',
  location: '#78716C',
};

export const RELATION_TYPES = {
  OWNS: 'Owns',
  MANAGES: 'Manages',
  INVESTED_IN: 'Invested in',
  MENTIONS: 'Mentions',
  WORKS_AT: 'Works at',
  OPERATES_IN: 'Operates in',
  SPONSORED_BY: 'Sponsored by',
  EXITED: 'Exited',
  ACQUIRED: 'Acquired',
  FOUNDED: 'Founded',
  BOARD_MEMBER: 'Board member',
  COMPETES_WITH: 'Competes with',
  PARTNERED_WITH: 'Partnered with',
  ADVISES: 'Advises',
  FINANCED: 'Financed',
  SOLD_TO: 'Sold to',
  RELATED_TO: 'Related to',
};

/** Search result group order for universal search UI. */
export const SEARCH_GROUP_ORDER = [
  'Private Equity Firms',
  'Funds',
  'Portfolio Companies',
  'Companies',
  'Transactions',
  'Articles',
  'Industries',
  'People',
  'News',
  'Investors',
  'Locations',
];

export function entityTypeLabel(type) {
  return ENTITY_TYPES[type]?.label || type;
}

export function searchGroupForType(type) {
  return ENTITY_TYPES[type]?.searchGroup || 'Other';
}

export function nodeColorForType(type) {
  return NODE_COLORS[type] || '#64748B';
}

export function slugify(name) {
  return String(name || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 120);
}

export function entityPublicPath(entity) {
  if (!entity) return '/private-markets';
  if (entity.entity_type === 'pe_firm' || entity.entity_type === 'general_partner') {
    return `/private-markets/firms/${entity.slug}`;
  }
  if (entity.entity_type === 'article' || entity.entity_type === 'news') {
    const articleId = entity.metadata?.article_id;
    if (articleId) return `/articles/${articleId}`;
    return `/research?q=${encodeURIComponent(entity.name)}`;
  }
  return `/private-markets/entities/${entity.slug}`;
}
