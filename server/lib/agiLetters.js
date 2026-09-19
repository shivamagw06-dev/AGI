/** Server copy of AGI letter brand map (keep in sync with src/config/agiLetters.js). */

export const AGI_LETTERS = [
  {
    key: 'agi_markets',
    name: 'AGI Markets',
    schedule: 'Flagship publication',
    tagline: 'Your market hub for equities, macro, commodities, FX and fixed income.',
  },
  {
    key: 'agi_morning_brief',
    name: 'AGI Morning Brief',
    schedule: '7:00–8:00 AM IST',
    tagline: 'Everything you need before the opening bell.',
  },
  {
    key: 'agi_evening_brief',
    name: 'AGI Evening Brief',
    schedule: '4:30–6:00 PM IST',
    tagline: 'What moved markets today—and why.',
  },
  {
    key: 'agi_macro',
    name: 'AGI Macro',
    schedule: 'Weekly or major events',
    tagline: 'Understanding the forces shaping global markets.',
  },
];

export const AGI_LETTER_KEYS = AGI_LETTERS.map((l) => l.key);

export function getLetter(key) {
  return AGI_LETTERS.find((l) => l.key === key) || AGI_LETTERS[0];
}

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

/** Legacy rows without preferences receive all letters. */
export function normalizePreferences(prefs) {
  if (!prefs || typeof prefs !== 'object') {
    return Object.fromEntries(AGI_LETTER_KEYS.map((key) => [key, true]));
  }
  const next = Object.fromEntries(
    AGI_LETTER_KEYS.map((key) => [key, Boolean(prefs[key])])
  );
  if (!AGI_LETTER_KEYS.some((key) => next[key])) next.agi_markets = true;
  return next;
}

export function selectedLetterNames(prefs) {
  const normalized = normalizePreferences(prefs);
  return AGI_LETTERS.filter((l) => normalized[l.key]).map((l) => l.name);
}
