import React from 'react';

/**
 * Light-theme pieces shared by every strategy on the strategy page. Colour
 * carries the same meanings as the monitor: blue disclosed, green strong,
 * amber AGI estimate, grey low confidence, red weak.
 */

export const FOCUS = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d9701f]';

const TAGS = {
  D: ['Disclosed', 'Stated by the company in its own filing, release, presentation or call.', 'text-[#1f5f9e] border-[#b9d3ee]'],
  I: ['AGI arithmetic', 'Calculated by AGI from disclosed figures. No assumption involved.', 'text-[#4b5563] border-[#d1d5db]'],
  A: ['AGI estimate', 'Depends on AGI assumptions (growth, margin, exit multiple).', 'text-[#9a520c] border-[#efc9a0]'],
};
export function Tag({ t }) {
  const [label, why, tone] = TAGS[t];
  return (
    <abbr title={`${label}: ${why}`} className={`ml-1.5 inline-block rounded border bg-white px-1 align-middle text-[10px] font-semibold leading-[15px] no-underline ${tone}`}>
      {t}
    </abbr>
  );
}

const TONE = {
  strong: 'bg-[#e3f4ea] text-[#17693a]',
  neutral: 'bg-[#eef1f5] text-[#34404f]',
  disclosed: 'bg-[#e8f1fb] text-[#1f5f9e]',
  caution: 'bg-[#fdf1e2] text-[#9a520c]',
  weak: 'bg-[#fdecec] text-[#b42318]',
  low: 'bg-[#f3f4f6] text-[#6b7480]',
  none: 'text-[#a0a8b3]',
};
const BAND_TONE = {
  default: { high: 'strong', strong: 'strong', medium: 'neutral', moderate: 'neutral', low: 'low', weak: 'weak', 'capital-hungry': 'caution', 'stated only': 'disclosed', 'not measurable': 'none' },
  expectation: { low: 'neutral', moderate: 'neutral', high: 'caution', 'very high': 'weak', 'not measurable': 'none' },
};
export function Band({ b, scale = 'default' }) {
  const tone = TONE[BAND_TONE[scale][b] || BAND_TONE.default[b] || 'neutral'];
  return <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-[12px] font-medium ${tone}`}>{b}</span>;
}

export const pct = (v, d = 0) => (Number.isFinite(v) ? `${v >= 0 ? '' : '−'}${Math.abs(v * 100).toFixed(d)}%` : '—');
export const signedPct = (v, d = 0) => (Number.isFinite(v) ? `${v >= 0 ? '+' : '−'}${Math.abs(v * 100).toFixed(d)}%` : '—');
export const dateLabel = (d) => {
  if (!d) return '';
  const t = new Date(`${d}T00:00:00Z`);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
};
