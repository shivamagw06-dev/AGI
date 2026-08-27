import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  articleMatchesDesk,
  getSectionsForDesk,
  RESEARCH_DESKS,
} from './deskSections.js';

describe('deskSections', () => {
  it('exposes five research desks', () => {
    assert.equal(RESEARCH_DESKS.length, 5);
    assert.deepEqual(
      RESEARCH_DESKS.map((d) => d.id).sort(),
      ['economics', 'global-markets', 'hedge-funds', 'indian-market', 'private-markets'].sort()
    );
  });

  it('matches canonical and legacy private markets sections', () => {
    assert.equal(articleMatchesDesk({ section: 'Private Markets' }, 'private-markets'), true);
    assert.equal(articleMatchesDesk({ section: 'Private Equity' }, 'private-markets'), true);
    assert.equal(articleMatchesDesk({ section: 'Deal Tracker' }, 'private-markets'), true);
    assert.equal(articleMatchesDesk({ section: 'Global Markets' }, 'private-markets'), false);
  });

  it('lists query sections for hedge funds and economics', () => {
    const hf = getSectionsForDesk('hedge-funds');
    assert.ok(hf.includes('Hedge Funds'));
    const econ = getSectionsForDesk('economics');
    assert.ok(econ.includes('Economics'));
    assert.ok(econ.includes('Macro Intelligence'));
  });
});
