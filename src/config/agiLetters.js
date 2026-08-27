/**
 * AGI flagship letters / newsletters.
 * Keys are stored in subscribers.preferences JSON.
 */

export const AGI_LETTERS = [
  {
    key: 'agi_markets',
    name: 'AGI Markets',
    shortName: 'Markets',
    schedule: 'Flagship publication',
    tagline: 'Your market hub for equities, macro, commodities, FX and fixed income.',
    purpose: 'Flagship publication and market hub.',
    contents: [
      'Homepage brand and general market news',
      'Equity, macro, commodities, FX, fixed income',
      'Main newsletter for broad market coverage',
    ],
    defaultSelected: true,
    hubPath: '/market-intelligence',
  },
  {
    key: 'agi_morning_brief',
    name: 'AGI Morning Brief',
    shortName: 'Morning Brief',
    schedule: '7:00–8:00 AM IST',
    tagline: 'Everything you need before the opening bell.',
    purpose: 'Pre-open desk note.',
    contents: [
      'Overnight US & global markets',
      'Asia market setup',
      'SGX GIFT Nifty / futures',
      'Key macro events',
      'Earnings today',
      'Stocks to watch',
      'Institutional insights',
      'Economic calendar',
    ],
    defaultSelected: false,
    hubPath: '/pre-market',
  },
  {
    key: 'agi_evening_brief',
    name: 'AGI Evening Brief',
    shortName: 'Evening Brief',
    schedule: '4:30–6:00 PM IST',
    tagline: 'What moved markets today—and why.',
    purpose: 'End-of-day wrap.',
    contents: [
      'Market wrap',
      'Top gainers & losers',
      'Sector performance',
      'FII/DII flows',
      'Breaking developments',
      "Tomorrow's watchlist",
      'Closing commentary',
    ],
    defaultSelected: false,
    hubPath: '/updates/market-close',
  },
  {
    key: 'agi_macro',
    name: 'AGI Macro',
    shortName: 'Macro',
    schedule: 'Weekly or major events',
    tagline: 'Understanding the forces shaping global markets.',
    purpose: 'Long-form and event-driven macro.',
    contents: [
      'RBI and Fed policy',
      'Inflation and employment',
      'Bond markets',
      'Currency moves',
      'Geopolitics',
      'Fiscal policy',
      'Global trade',
      'Long-form macro analysis',
    ],
    defaultSelected: false,
    hubPath: '/macro-intelligence',
  },
];

export const AGI_LETTER_KEYS = AGI_LETTERS.map((l) => l.key);

export function defaultLetterPreferences(selectedKeys = null) {
  const selected = new Set(
    Array.isArray(selectedKeys) && selectedKeys.length
      ? selectedKeys
      : AGI_LETTERS.filter((l) => l.defaultSelected).map((l) => l.key)
  );
  if (!selected.size) selected.add('agi_markets');
  return Object.fromEntries(AGI_LETTER_KEYS.map((key) => [key, selected.has(key)]));
}

export function getLetter(key) {
  return AGI_LETTERS.find((l) => l.key === key) || AGI_LETTERS[0];
}

/** Map CMS article section names to a letter key. */
export function letterKeyFromSection(section = '') {
  const value = String(section || '').trim().toLowerCase();
  if (!value) return 'agi_markets';

  if (
    /pre-?market|morning market|morning brief|today'?s market brief|market opening|opening outlook/.test(
      value
    )
  ) {
    return 'agi_morning_brief';
  }

  if (/market close|day close|evening brief|closing|eod|end of day/.test(value)) {
    return 'agi_evening_brief';
  }

  if (/macro|economy|global markets|commodit|fiscal|monetary|inflation|rbi|fed|geopolit/.test(value)) {
    return 'agi_macro';
  }

  return 'agi_markets';
}

export function letterDisplayFrom(letterKey) {
  const letter = getLetter(letterKey);
  return `${letter.name} <updates@agarwalglobalinvestments.com>`;
}
