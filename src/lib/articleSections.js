import { RESEARCH_DESK_SECTIONS } from '@/lib/deskSections';

/** Canonical article.section values accepted by DB constraint articles_section_allowed. */

export const ALLOWED_ARTICLE_SECTIONS = [
  ...RESEARCH_DESK_SECTIONS,
  'Pre-Market Update',
  'Morning Market Update',
  "Today's Market Brief",
  'Market Opening Outlook',
  '12 PM Market Update',
  'Market News',
  'Research Reports',
  'Stock Analysis',
  'Company Updates',
  'IPOs',
  'Market Close Update',
  'Day Close Update',
  'Market Close Summary',
  'Macro Intelligence',
  'Economy',
  'Global Markets',
  'Commodities',
  'Intelligence',
  'AGI Intelligence',
  'Research',
  'Opinions & Editorials',
  'Deal Tracker',
  "Editor's Desk",
  'Private Equity',
];

const SECTION_ALIASES = {
  'pre market update': 'Pre-Market Update',
  'pre-market update': 'Pre-Market Update',
  'morning brief': 'Morning Market Update',
  'agi morning brief': 'Morning Market Update',
  'evening brief': 'Day Close Update',
  'agi evening brief': 'Day Close Update',
  'market close': 'Market Close Update',
  'day close': 'Day Close Update',
  macro: 'Macro Intelligence',
  'agi macro': 'Macro Intelligence',
  'macro intelligence': 'Macro Intelligence',
  intelligence: 'Intelligence',
  'agi intelligence': 'Intelligence',
  research: 'Research Reports',
  'research report': 'Research Reports',
  'stock research': 'Stock Analysis',
  'indian market': 'Indian Market',
  ipo: 'IPOs',
  ipos: 'IPOs',
  'ipo research': 'IPOs',
  'private markets': 'Private Markets',
  'hedge funds': 'Hedge Funds',
  'hedge fund': 'Hedge Funds',
  economics: 'Economics',
  'private equity': 'Private Markets',
};

export function normalizeArticleSection(section, { forIntelligence = false } = {}) {
  const raw = String(section || '').trim();
  if (forIntelligence) {
    // Private intelligence notes use a dedicated non-public section.
    if (!raw || !ALLOWED_ARTICLE_SECTIONS.includes(raw)) return 'Intelligence';
    return raw;
  }
  if (!raw) return 'Indian Market';
  if (ALLOWED_ARTICLE_SECTIONS.includes(raw)) return raw;

  const alias = SECTION_ALIASES[raw.toLowerCase()];
  if (alias) return alias;

  // Fuzzy contains match against allowed list.
  const lower = raw.toLowerCase();
  const fuzzy = ALLOWED_ARTICLE_SECTIONS.find((name) => lower.includes(name.toLowerCase()));
  return fuzzy || 'Indian Market';
}
