import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  calibrateDisplayedConfidence,
  dedupeAnswerText,
  normalizeProvenance,
  scenarioCopy,
} from '../../src/components/AskAgi/answerQuality.js';

describe('Ask AGI institutional answer quality', () => {
  it('removes repeated synthesis sentences', () => {
    assert.equal(
      dedupeAnswerText('Reliance has four engines. Reliance has four engines. Jio is growing.'),
      'Reliance has four engines. Jio is growing.',
    );
    assert.equal(
      dedupeAnswerText('Reliance combines O2C, Jio, Retail and New Energy. Reliance combines O2C, Jio, Retail and New Energy…'),
      'Reliance combines O2C, Jio, Retail and New Energy.',
    );
  });

  it('preserves dated source metadata and removes exact duplicates', () => {
    const rows = normalizeProvenance([
      { title: 'Annual report', source: 'RIL', url: '/ril.pdf', as_of: '2026-03-31', evidence_type: 'REPORTED' },
      { title: 'Annual report', source: 'RIL', url: '/ril.pdf', as_of: '2026-03-31', evidence_type: 'REPORTED' },
    ]);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].date, '2026-03-31');
    assert.equal(rows[0].evidenceType, 'REPORTED');
  });

  it('caps confidence when financials and valuation are unsupported', () => {
    assert.equal(calibrateDisplayedConfidence(88, {
      full_company_analysis: true,
      financials_supported: false,
      valuation_supported: false,
    }), 50);
  });

  it('uses market language for outlook scenarios', () => {
    const copy = scenarioCopy('sector');
    assert.equal(copy.title, 'Market Scenarios');
    assert.match(copy.positiveLead, /outlook/i);
  });
});
