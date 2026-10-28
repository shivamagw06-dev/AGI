export const SCREENER_CATEGORIES = ['Value', 'Growth', 'Quality', 'Momentum', 'Shareholding', 'Technicals', 'Moving averages', 'Candlesticks', 'Dividends', 'Analyst estimates', 'Risk flags', 'Multi-factor', 'Other'];
export const LEGACY_SCREENERS = [
  { slug: 'low-pe', display_name: 'Low P/E', category: 'Value', description: 'Positive P/E below the 3, 5 and 10-year averages.', table: 'manual_low_pe_screener_snapshots', path: '/agi/screeners/low-pe', adminPath: '/admin/low-pe-screener' },
  { slug: 'promoter-holdings', display_name: 'Promoter holdings rising', category: 'Shareholding', description: 'Published promoter shareholding changes, with reporting dates.', table: 'manual_promoter_screener_snapshots', path: '/agi/screeners/promoter-holdings', adminPath: '/admin/promoter-screener' },
  { slug: 'piotroski', display_name: 'High Piotroski Score', category: 'Quality', description: 'Financial-strength candidates in the published score table.', table: 'manual_piotroski_screener_snapshots', path: '/agi/screeners/piotroski', adminPath: '/admin/piotroski-screener' },
  { slug: 'cash-flow', display_name: 'Consistent Free Cash Flow', category: 'Quality', description: 'Published companies with a positive cash-flow track record.', table: 'manual_cash_flow_screener_snapshots', path: '/agi/screeners/cash-flow', adminPath: '/admin/cash-flow-screener' },
  { slug: 'momentum', display_name: 'Momentum Stocks', category: 'Momentum', description: 'Published momentum, volume and relative-performance readings.', table: 'manual_momentum_screener_snapshots', path: '/agi/screeners/momentum', adminPath: '/admin/momentum-screener' },
];
export function screenerPath(screen) { return screen.kind === 'legacy' ? screen.path : `/agi/screeners/library/${screen.slug}`; }
export function screenerSlug(name) { return String(name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80); }
export const STARTER_SCREENERS = [
  ['agi-momentum-candidates', 'AGI Momentum candidates', 'Momentum', 'Price and earnings-momentum candidate tables.'],
  ['agi-value-candidates', 'AGI Value candidates', 'Value', 'Valuation and earnings-yield candidate tables.'],
  ['agi-growth-candidates', 'AGI Growth candidates', 'Growth', 'Revenue and earnings-growth candidate tables.'],
  ['agi-quality-candidates', 'AGI Quality candidates', 'Quality', 'Profitability, balance-sheet and earnings-quality candidates.'],
  ['agi-all-weather-candidates', 'AGI All-Weather candidates', 'Multi-factor', 'Combined factor candidates; final ranks and weights need separate review.'],
  ['golden-cross', 'Golden cross', 'Moving averages', 'Tables of bullish moving-average conditions.'],
  ['death-cross', 'Death cross', 'Moving averages', 'Tables of bearish moving-average conditions.'],
  ['volume-breakouts', 'Volume breakouts', 'Technicals', 'Price and traded-volume breakout candidates.'],
  ['relative-strength', 'Relative strength', 'Momentum', 'Stock performance compared with an index, sector or industry.'],
  ['fii-holding-increases', 'FII holding increases', 'Shareholding', 'Foreign-institution shareholding changes, using the reported quarter.'],
  ['dii-holding-increases', 'DII holding increases', 'Shareholding', 'Domestic-institution shareholding changes, using the reported quarter.'],
  ['candlestick-patterns', 'Candlestick patterns', 'Candlesticks', 'Dated pattern tables with their observation timeframe.'],
  ['dividend-quality', 'Dividend quality', 'Dividends', 'Dividend and cash-flow candidate tables.'],
  ['earnings-growth', 'Earnings growth', 'Growth', 'Quarterly or annual earnings-growth candidates.'],
  ['financial-red-flags', 'Financial red flags', 'Risk flags', 'Financial risk indicators for further research.'],
  ['analyst-estimate-candidates', 'Analyst estimate candidates', 'Analyst estimates', 'Imported consensus or forecast tables with a dated source.'],
].map(([slug, display_name, category, description]) => ({ slug, display_name, category, description, rule_notes: 'Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.' }));
