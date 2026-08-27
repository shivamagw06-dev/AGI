/** Research desk taxonomy — homepage filters and CMS article classification. */

export const RESEARCH_DESK_ALL = 'all';

export const RESEARCH_DESKS = [
  {
    id: 'indian-market',
    label: 'Indian Market',
    section: 'Indian Market',
    hint: 'India desk',
  },
  {
    id: 'global-markets',
    label: 'Global Markets',
    section: 'Global Markets',
    hint: 'World markets',
  },
  {
    id: 'private-markets',
    label: 'Private Markets',
    section: 'Private Markets',
    hint: 'Deals & exits',
  },
  {
    id: 'hedge-funds',
    label: 'Hedge Funds',
    section: 'Hedge Funds',
    hint: 'Strategies',
  },
  {
    id: 'economics',
    label: 'Economics',
    section: 'Economics',
    hint: 'Macro & policy',
  },
];

/** Canonical section values shown in the article editor. */
export const RESEARCH_DESK_SECTIONS = RESEARCH_DESKS.map((d) => d.section);

/** Legacy article.section values mapped to a desk id for filtering. */
const LEGACY_SECTION_TO_DESK = {
  'Pre-Market Update': 'indian-market',
  'Morning Market Update': 'indian-market',
  "Today's Market Brief": 'indian-market',
  'Market Opening Outlook': 'indian-market',
  '12 PM Market Update': 'indian-market',
  'Market News': 'indian-market',
  'Research Reports': 'indian-market',
  'Stock Analysis': 'indian-market',
  'Company Updates': 'indian-market',
  IPOs: 'indian-market',
  'Market Close Update': 'indian-market',
  'Day Close Update': 'indian-market',
  'Market Close Summary': 'indian-market',
  Research: 'indian-market',
  'Opinions & Editorials': 'indian-market',
  Commodities: 'global-markets',
  Economy: 'economics',
  'Macro Intelligence': 'economics',
  'Private Equity': 'private-markets',
  'Deal Tracker': 'private-markets',
  "Editor's Desk": 'indian-market',
};

export function getDeskById(deskId) {
  if (!deskId || deskId === RESEARCH_DESK_ALL) return null;
  return RESEARCH_DESKS.find((d) => d.id === deskId) || null;
}

export function getDeskForSection(section) {
  const raw = String(section || '').trim();
  if (!raw) return null;

  const direct = RESEARCH_DESKS.find((d) => d.section === raw);
  if (direct) return direct;

  const legacyId = LEGACY_SECTION_TO_DESK[raw];
  return legacyId ? getDeskById(legacyId) : null;
}

/** All DB section strings that belong to a desk (canonical + legacy). */
export function getSectionsForDesk(deskId) {
  if (!deskId || deskId === RESEARCH_DESK_ALL) return null;

  const desk = getDeskById(deskId);
  if (!desk) return null;

  const sections = new Set([desk.section]);
  for (const [legacySection, mappedDeskId] of Object.entries(LEGACY_SECTION_TO_DESK)) {
    if (mappedDeskId === deskId) sections.add(legacySection);
  }
  return Array.from(sections);
}

export function articleMatchesDesk(article, deskId) {
  if (!deskId || deskId === RESEARCH_DESK_ALL) return true;
  const section = article?.section || article?.category;
  const desk = getDeskForSection(section);
  return desk?.id === deskId;
}
