import {
  Sunrise,
  Clock,
  Sunset,
  FileText,
  Building2,
  BarChart3,
} from 'lucide-react';

/** Homepage category cards — each maps to a content section in CMS */
export const HOME_CATEGORIES = [
  {
    id: 'pre-market',
    title: 'Pre-Market Update',
    description:
      'Everything to know before markets open — global markets, SGX Gift Nifty, commodities, news, and key events.',
    icon: Sunrise,
    path: '/updates/pre-market',
    section: 'Pre-Market Update',
  },
  {
    id: 'midday',
    title: '12 PM Market Update',
    description:
      'Mid-day market movement, sector performance, institutional activity, and important developments.',
    icon: Clock,
    path: '/updates/midday',
    section: '12 PM Market Update',
  },
  {
    id: 'market-close',
    title: 'Market Close Update',
    description:
      'End-of-day summary, winners, losers, FII/DII activity, and tomorrow\'s outlook.',
    icon: Sunset,
    path: '/updates/market-close',
    section: 'Market Close Update',
  },
  {
    id: 'research-notes',
    title: 'Research Notes',
    description:
      'Deep-dive reports, valuation analysis, sector research, and investment ideas.',
    icon: FileText,
    path: '/sections/research-notes',
    section: 'Research Notes',
  },
  {
    id: 'company-updates',
    title: 'Company Updates',
    description:
      'Quarterly results, earnings summaries, management commentary, corporate actions, and announcements.',
    icon: Building2,
    path: '/company-updates',
    section: 'Company Updates',
  },
  {
    id: 'market-overview',
    title: 'Market Overview',
    description:
      'Live indices, commodities, currencies, global markets, and economic indicators.',
    icon: BarChart3,
    path: '/markets/stocks',
    section: null,
  },
];

export const MARKET_UPDATE_CATEGORIES = HOME_CATEGORIES.filter((c) =>
  ['pre-market', 'midday', 'market-close'].includes(c.id)
);

export function getCategoryByPath(path) {
  return HOME_CATEGORIES.find((c) => c.path === path);
}

export function getCategoryById(id) {
  return HOME_CATEGORIES.find((c) => c.id === id);
}
