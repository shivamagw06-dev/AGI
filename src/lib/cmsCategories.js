export const DEFAULT_CATEGORIES = [
  // Primary research desks (homepage filters + article editor)
  { name: 'Indian Market', slug: 'indian-market', description: 'India equities, sectors, and company research', sort_order: 1 },
  { name: 'Global Markets', slug: 'global-markets', description: 'US, Europe, Asia and cross-border markets', sort_order: 2 },
  { name: 'Private Markets', slug: 'private-markets', description: 'Private equity, venture, and deal intelligence', sort_order: 3 },
  { name: 'Hedge Funds', slug: 'hedge-funds', description: 'Hedge fund strategies and manager research', sort_order: 4 },
  { name: 'Economics', slug: 'economics', description: 'Macro, policy, rates, inflation and geopolitics', sort_order: 5 },
  // Legacy / market-update categories
  { name: 'Morning Market Update', slug: 'morning-market-update', description: 'AGI Morning Brief — pre-market and opening bell', sort_order: 11 },
  { name: '12 PM Market Update', slug: '12-pm-market-update', description: 'AGI Markets midday snapshot and key moves', sort_order: 2 },
  { name: 'Day Close Update', slug: 'day-close-update', description: 'AGI Evening Brief — end-of-day wrap', sort_order: 3 },
  { name: 'Market News', slug: 'market-news', description: 'AGI Markets — breaking market news and headlines', sort_order: 4 },
  { name: 'Research Reports', slug: 'research-reports', description: 'In-depth institutional research reports', sort_order: 5 },
  { name: 'Stock Analysis', slug: 'stock-analysis', description: 'Company and equity analysis', sort_order: 6 },
  { name: 'Economy', slug: 'economy', description: 'Macroeconomic trends, GDP, inflation and policy', sort_order: 17 },
  { name: 'Commodities', slug: 'commodities', description: 'Oil, gold, metals and commodity markets', sort_order: 18 },
  { name: 'IPOs', slug: 'ipos', description: 'IPO pipeline, listings and new issues', sort_order: 10 },
  // Extended letter aliases (require migration 20260725190000)
  { name: 'Pre-Market Update', slug: 'pre-market-update', description: 'AGI Morning Brief alias', sort_order: 11 },
  { name: 'Market Close Update', slug: 'market-close-update', description: 'AGI Evening Brief alias', sort_order: 12 },
  { name: 'Macro Intelligence', slug: 'macro-intelligence', description: 'AGI Macro desk', sort_order: 13 },
  { name: 'Intelligence', slug: 'intelligence', description: 'Private AGI Intelligence notes (not public)', sort_order: 14 },
];

const STORAGE_KEY = 'agib:cms:categories';

export function getLocalCategories() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return DEFAULT_CATEGORIES.map((c, i) => ({ ...c, id: `local-${i}`, is_active: true }));
}

export function saveLocalCategories(categories) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(categories));
}
