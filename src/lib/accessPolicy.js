/**
 * Progressive registration wall — free browse for acquisition content,
 * free signup required for proprietary intelligence features.
 *
 * Articles, home, and market overview stay open. Ask AGI, desks, company
 * research, valuation, signals, and saved research require an account.
 */

export const UNLOCK_BENEFITS = [
  'Company & sector intelligence',
  'Institutional-style valuation analysis',
  'Ask AGI research',
  'Quantitative signals (Live Alpha & Hedge Fund)',
  'Research desks and forecasts',
  'Saved companies and watchlists',
];

const FEATURE_COPY = {
  ask_agi: {
    eyebrow: 'Ask AGI',
    title: 'Unlock Ask AGI research',
    blurb: 'Run real research questions against AGI intelligence — not demo prompts.',
  },
  agi_workspace: {
    eyebrow: 'AGI Workspace',
    title: 'Unlock the AGI research workspace',
    blurb: 'Company dossiers, portfolios, watchlists and institutional workflows.',
  },
  valuation: {
    eyebrow: 'Valuation Intelligence',
    title: 'Unlock valuation intelligence',
    blurb: 'Consensus multiples, historical percentiles, peer positioning and terminal analytics.',
  },
  hedge_fund: {
    eyebrow: 'Hedge Fund',
    title: 'Unlock Hedge Fund intelligence',
    blurb: 'Strategy context, opportunity scans and alpha research desks.',
  },
  live_alpha: {
    eyebrow: 'Live Alpha',
    title: 'Unlock Live Alpha signals',
    blurb: 'Quantitative signal teasers become full live opportunity views after signup.',
  },
  market_intelligence: {
    eyebrow: 'Market Intelligence',
    title: 'Unlock market intelligence',
    blurb: 'Full desk coverage beyond the public market snapshot.',
  },
  economics: {
    eyebrow: 'Economics',
    title: 'Unlock Economic Intelligence',
    blurb: 'G20 macro network, country pulse and governed macro evidence.',
  },
  global_markets: {
    eyebrow: 'Global Markets',
    title: 'Unlock global markets intelligence',
    blurb: 'Cross-market regimes, transmission and research desks.',
  },
  private_markets: {
    eyebrow: 'Private Markets',
    title: 'Unlock private markets intelligence',
    blurb: 'Firm dossiers, deal context and private-market research objects.',
  },
  company_research: {
    eyebrow: 'Company Research',
    title: 'Unlock company intelligence',
    blurb: 'Full stock research, fundamentals and AGI company views.',
  },
  sector_theme: {
    eyebrow: 'Sector & Theme',
    title: 'Unlock sector and theme intelligence',
    blurb: 'Deep sector desks, theme maps and workflow research.',
  },
  forecasts: {
    eyebrow: 'Forecasts',
    title: 'Unlock forecasts and predictions',
    blurb: 'Forward-looking research surfaces beyond public teasers.',
  },
  workspace: {
    eyebrow: 'Personal Workspace',
    title: 'Unlock saved research',
    blurb: 'Watchlists, saved companies and your research history.',
  },
  insider: {
    eyebrow: 'Insider Activity',
    title: 'Unlock insider activity intelligence',
    blurb: 'Full insider and filing intelligence beyond the teaser.',
  },
  ipo: {
    eyebrow: 'IPO Intelligence',
    title: 'Unlock IPO intelligence',
    blurb: 'Issue analysis and IPO research desks.',
  },
  intelligence: {
    eyebrow: 'AGI Intelligence',
    title: 'Unlock AGI Intelligence',
    blurb: 'Create a free account to continue into proprietary research features.',
  },
};

/** Longest prefix wins. Free paths are omitted (return null). */
const GATED_PREFIXES = [
  ['/ask', 'ask_agi'],
  ['/agi', 'agi_workspace'],
  ['/valuation-intelligence', 'valuation'],
  ['/valuation-terminal', 'valuation'],
  ['/hedge-fund', 'hedge_fund'],
  ['/live-alpha', 'live_alpha'],
  ['/market-intelligence', 'market_intelligence'],
  ['/market-sector-intelligence', 'market_intelligence'],
  ['/pre-market', 'market_intelligence'],
  ['/market-data', 'market_intelligence'],
  ['/data-health', 'market_intelligence'],
  ['/economics', 'economics'],
  ['/global-markets', 'global_markets'],
  ['/private-markets', 'private_markets'],
  ['/private-equity', 'private_markets'],
  ['/research/stocks', 'company_research'],
  ['/portfolio', 'sector_theme'],
  ['/themes', 'sector_theme'],
  ['/sectors', 'sector_theme'],
  ['/research/workflow', 'sector_theme'],
  ['/predictions', 'forecasts'],
  ['/workspace', 'workspace'],
  ['/insider-activity', 'insider'],
  ['/ipo-intelligence', 'ipo'],
  ['/ipos', 'ipo'],
];

export function getFeatureForPath(pathname = '') {
  const path = String(pathname || '').split('?')[0] || '/';
  if (path === '/' || path === '') return null;

  // Explicit free acquisition surfaces
  const freeExact = new Set([
    '/markets',
    '/research',
    '/about',
    '/contact',
    '/login',
    '/verify-email',
    '/forgot-password',
    '/reset-password',
    '/unlock-pin',
    '/privacy',
    '/terms',
    '/disclaimer',
    '/sebi-disclosure',
    '/business',
    '/events',
    '/market-updates',
    '/company-updates',
  ]);
  if (freeExact.has(path)) return null;
  if (path.startsWith('/article/')) return null;
  if (path.startsWith('/category/')) return null;
  if (path.startsWith('/updates/')) return null;
  if (path.startsWith('/sections/')) return null;
  if (path.startsWith('/admin')) return null; // RequireAdmin handles CMS
  if (path.startsWith('/u/')) return null;
  if (path === '/profile/edit') return null;

  let match = null;
  let bestLen = -1;
  for (const [prefix, feature] of GATED_PREFIXES) {
    if (path === prefix || path.startsWith(`${prefix}/`)) {
      if (prefix.length > bestLen) {
        bestLen = prefix.length;
        match = feature;
      }
    }
  }
  return match;
}

export function isPathGated(pathname) {
  return Boolean(getFeatureForPath(pathname));
}

export function getFeatureCopy(featureKey) {
  return FEATURE_COPY[featureKey] || FEATURE_COPY.intelligence;
}

export function buildLoginUrl({ returnTo = '/', mode = 'signup' } = {}) {
  const next = String(returnTo || '/').startsWith('/') ? returnTo : '/';
  const params = new URLSearchParams();
  params.set('mode', mode === 'signin' ? 'signin' : 'signup');
  params.set('next', next);
  return `/login?${params.toString()}`;
}

export function resolveAccess({ user, pathname }) {
  const feature = getFeatureForPath(pathname);
  if (!feature) {
    return { allowed: true, feature: null, reason: 'public' };
  }
  if (user) {
    return { allowed: true, feature, reason: 'authenticated' };
  }
  return {
    allowed: false,
    feature,
    reason: 'registration_required',
    loginPath: buildLoginUrl({ returnTo: pathname, mode: 'signup' }),
  };
}
