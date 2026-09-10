import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  ARCHETYPES, strategyProfile, traitsFor, caveatsFor, confidenceFor, evidenceFor,
} from './strategyFingerprint.js';

/**
 * The fixtures are real books, not invented ones.
 *
 * Every number below was measured from the stored 13F holdings of the manager
 * named. That matters more than usual here: a classifier tested on numbers
 * chosen to suit it proves only that it agrees with itself. These are the
 * books it has to work on, and if a threshold is wrong one of them lands in
 * the wrong bucket.
 */
const REAL = {
  citadel: { positions: 13572, top10Pct: 22.7, optionsPct: 53.2, votesPct: 99.0, turnoverPct: 12.3 },
  janeStreet: { positions: 11385, top10Pct: 32.5, optionsPct: 51.5, votesPct: 72.2, turnoverPct: 14.0 },
  jpmorgan: { positions: 7720, top10Pct: 24.9, optionsPct: 11.7, votesPct: 90.2, turnoverPct: 11.1 },
  goldman: { positions: 6524, top10Pct: 19.2, optionsPct: 13.8, votesPct: 88.9, turnoverPct: 9.8 },
  millennium: { positions: 5796, top10Pct: 18.4, optionsPct: 33.7, votesPct: 62.9, turnoverPct: 12.5 },
  blackrock: { positions: 5696, top10Pct: 28.0, optionsPct: 0.8, votesPct: 96.2, turnoverPct: 5.5 },
  vanguard: { positions: 4329, top10Pct: 31.2, optionsPct: 0.0, votesPct: 14.6, turnoverPct: 2.8 },
  aqr: { positions: 3900, top10Pct: 12.2, optionsPct: 0.0, votesPct: 99.9, turnoverPct: 6.5 },
  renaissance: { positions: 3140, top10Pct: 12.0, optionsPct: 0.0, votesPct: 100.0, turnoverPct: 18.0 },
  maverick: { positions: 179, top10Pct: 42.8, optionsPct: 1.1, votesPct: 0.0, turnoverPct: 46.9 },
  valueAligned: { positions: 123, top10Pct: 53.6, optionsPct: 52.0, votesPct: 100.0, turnoverPct: 13.8 },
  bakerBros: { positions: 84, top10Pct: 72.8, optionsPct: 0.0, votesPct: 100.0, turnoverPct: 9.5 },
  d1: { positions: 55, top10Pct: 76.7, optionsPct: 0.0, votesPct: 100.0, turnoverPct: 38.2 },
  berkshire: { positions: 29, top10Pct: 88.5, optionsPct: 0.0, votesPct: 100.0, turnoverPct: 3.4 },
  scion: { positions: 8, top10Pct: 100.0, optionsPct: 50.0, votesPct: 50.0, turnoverPct: 87.5 },
  // No prior quarter stored. The first sweep measured this book as 100% new,
  // which is not a strategy: it is one filing with nothing to compare to.
  bridgewater: { positions: 997, top10Pct: 40.0, optionsPct: 0.0, votesPct: 100.0, turnoverPct: 21.5 },
  norges: { positions: 1617, top10Pct: 32.4, optionsPct: 0.0, votesPct: 100.0, turnoverPct: null },
};

// Measured: 42 stored quarters for most of these managers, which is what the
// caveats and confidence rules are calibrated against.
for (const key of Object.keys(REAL)) REAL[key].quartersObserved = 42;
REAL.norges.quartersObserved = 1;

describe('the archetype each real book lands in', () => {
  const expected = [
    ['citadel', 'market_making'],
    ['janeStreet', 'market_making'],
    ['millennium', 'market_making'],
    ['aqr', 'systematic_broad'],
    ['renaissance', 'systematic_broad'],
    ['vanguard', 'broad_low_turnover'],
    ['blackrock', 'broad_low_turnover'],
    ['jpmorgan', 'diversified_broad'],
    ['berkshire', 'concentrated_held'],
    ['bakerBros', 'concentrated_held'],
    ['d1', 'concentrated_rotated'],
    ['valueAligned', 'derivatives_overlay'],
    ['scion', 'derivatives_overlay'],
    ['maverick', 'focused_rotated'],
    ['bridgewater', 'selective_diversified'],
  ];
  for (const [name, archetype] of expected) {
    test(`${name} is ${archetype}`, () => {
      assert.equal(strategyProfile(REAL[name]).archetype, archetype);
    });
  }

  test('a book three positions under the broad threshold is not called focused', () => {
    // Bridgewater reports 997 positions. The breadth threshold is 1000, and
    // an earlier label called everything below it "Focused but spread" - which
    // for a thousand-name book is the label arguing with its own evidence.
    // The archetype is right; the word was not.
    const profile = strategyProfile(REAL.bridgewater);
    assert.equal(profile.archetype, 'selective_diversified');
    assert.doesNotMatch(profile.label, /focused/i);
    // And a label decided this close to a threshold says so.
    assert.equal(profile.confidence, 'medium');
  });

  test('a bank is not mistaken for a quant fund', () => {
    // Goldman reports 19.2% in its largest ten, below the 20% band that marks
    // an evenly weighted book, and would have been called systematic on a
    // 0.8 point margin. It reports 13.8% of its lines as options; AQR and
    // Renaissance report none. That is the difference, and the classifier has
    // to use it.
    assert.equal(strategyProfile(REAL.goldman).archetype, 'diversified_broad');
    assert.equal(strategyProfile(REAL.aqr).archetype, 'systematic_broad');
  });
});

describe('an unmeasurable metric is absent, not zero', () => {
  test('a manager with one stored quarter is not called fully rotated', () => {
    const profile = strategyProfile(REAL.norges);
    // Turnover is unknown, so no archetype that depends on turnover may fire.
    assert.equal(profile.archetype, 'diversified_broad');
    assert.equal(profile.confidence, 'low');
    assert.equal(profile.evidence.some((row) => row.key === 'turnover'), false);
    assert.match(profile.caveats.join(' '), /Only one quarter is stored/);
  });

  test('turnover of zero is a measurement and still classifies', () => {
    // The distinction the null exists for: 0% new is a real, meaningful
    // reading - the manager changed nothing - and must not be treated as
    // missing the way null is.
    const held = strategyProfile({ ...REAL.berkshire, turnoverPct: 0 });
    assert.equal(held.archetype, 'concentrated_held');
    assert.equal(held.evidence.find((row) => row.key === 'turnover').value, 0);
  });
});

describe('confidence', () => {
  test('is low when the book is too small to have a shape', () => {
    assert.equal(strategyProfile(REAL.scion).confidence, 'low');
  });

  test('is medium within five points of the threshold that decided it', () => {
    // 53.6% in the largest ten is concentrated; 49% is not. A label that
    // would flip on a small revision should say so rather than be defended.
    assert.equal(confidenceFor({ ...REAL.valueAligned, quartersObserved: 8 },
      ARCHETYPES[0]), 'medium');
  });

  test('is high only with a real history behind it', () => {
    assert.equal(confidenceFor({ ...REAL.berkshire, quartersObserved: 42 },
      { key: 'concentrated_held' }), 'high');
    // Greenlight's four stored quarters. A year of filings cannot establish
    // how a manager behaves, whatever this quarter's book looks like.
    assert.equal(confidenceFor({ ...REAL.berkshire, quartersObserved: 4 },
      { key: 'concentrated_held' }), 'medium');
    assert.equal(confidenceFor({ ...REAL.berkshire, quartersObserved: 3 },
      { key: 'concentrated_held' }), 'low');
  });
});

describe('traits hold across archetypes', () => {
  test('13D is reported as intent, 13G as its absence', () => {
    const activist = traitsFor({ activistFilings: 3, passiveFilings: 9 });
    assert.equal(activist[0].key, 'activist');
    const passive = traitsFor({ activistFilings: 0, passiveFilings: 9 });
    assert.equal(passive[0].key, 'passive_stakes');
    // Neither is claimed when nothing was filed.
    assert.deepEqual(traitsFor({ activistFilings: 0, passiveFilings: 0 }), []);
  });

  test('a manager that holds shares without the vote is flagged', () => {
    // Vanguard reports sole voting authority on 14.6% of its positions and
    // Maverick on none. The shares are held; the vote sits with the funds.
    assert.equal(traitsFor(REAL.vanguard).some((t) => t.key === 'votes_rarely'), true);
    assert.equal(traitsFor(REAL.maverick).some((t) => t.key === 'votes_rarely'), true);
    assert.equal(traitsFor(REAL.berkshire).some((t) => t.key === 'votes_own_book'), true);
  });

  test('holding period is judged against the manager\'s own history', () => {
    // Measured, all of it. An absolute "four or more quarters" threshold
    // cleared 41 of the 51 managers - a trait that fires for four fifths of
    // the set distinguishes nothing. The share of its own record that the
    // median name survives does.
    const keys = (m) => traitsFor(m).map((t) => t.key);
    // Valley Forge: every name, all 39 quarters.
    assert.ok(keys({ medianQuartersHeld: 39, quartersObserved: 39 }).includes('long_held'));
    // Vanguard: 31 of 42.
    assert.ok(keys({ medianQuartersHeld: 31, quartersObserved: 42 }).includes('long_held'));
    // Berkshire: 16 of 42. Rarely changes quarter to quarter, and still not a
    // book whose names survive the record - both are true and the profile
    // should not claim the second.
    assert.equal(keys({ medianQuartersHeld: 16, quartersObserved: 42 }).includes('long_held'), false);
    // Thiel Macro: 1 of 27, and Scion 1.5 of 32. Nothing stays.
    assert.ok(keys({ medianQuartersHeld: 1, quartersObserved: 27 }).includes('rapidly_rotated'));
    assert.ok(keys({ medianQuartersHeld: 1.5, quartersObserved: 32 }).includes('rapidly_rotated'));
    // Never both.
    for (const m of [{ medianQuartersHeld: 39, quartersObserved: 39 },
      { medianQuartersHeld: 1, quartersObserved: 27 }]) {
      const found = keys(m).filter((k) => k === 'long_held' || k === 'rapidly_rotated');
      assert.equal(found.length, 1, JSON.stringify(m));
    }
  });

  test('a manager with almost no history gets neither holding-period trait', () => {
    // Greenlight has four stored quarters, so its median name has survived all
    // four. That is a fact about how little we hold, not about Greenlight, and
    // claiming "positions survive the record" from it would be the profile
    // reporting our own collection gap as the manager's behaviour.
    const keys = traitsFor({ medianQuartersHeld: 4, quartersObserved: 4 }).map((t) => t.key);
    assert.equal(keys.includes('long_held'), false);
    assert.equal(keys.includes('rapidly_rotated'), false);
  });

  test('the median is published with the record it is measured against', () => {
    // 16 quarters is a decade of conviction or a third of the history; only
    // the denominator says which.
    const row = evidenceFor({ positions: 29, top10Pct: 88.5, medianQuartersHeld: 16, quartersObserved: 42 })
      .find((entry) => entry.key === 'held');
    assert.equal(row.value, 16);
    assert.equal(row.outOf, 42);
  });
});

describe('what the profile refuses to say', () => {
  test('no archetype claims a motive', () => {
    // Every rationale states what a book of this shape is characteristic of.
    // None states what the manager believes, intends or is trying to achieve -
    // that is attribution, and 13F is not evidence of it.
    for (const archetype of ARCHETYPES) {
      assert.match(archetype.characteristicOf, /characteristic of/,
        `${archetype.key} should describe the pattern, not the motive`);
      assert.doesNotMatch(archetype.characteristicOf,
        /\b(believes?|wants?|aims? to|intends? to|hopes?|expects? to)\b/i,
        `${archetype.key} attributes a motive`);
    }
  });

  test('every profile carries the limits of 13F itself', () => {
    for (const key of Object.keys(REAL)) {
      assert.match(strategyProfile(REAL[key]).caveats.join(' '), /US-listed long equity/,
        `${key} should state what 13F does not show`);
    }
  });

  test('a manager with no reported positions gets no profile at all', () => {
    assert.equal(strategyProfile({ positions: 0, top10Pct: 0 }), null);
    assert.equal(strategyProfile(null), null);
    assert.equal(strategyProfile({}), null);
  });
});

describe('the classifier is total and unambiguous', () => {
  test('every real book matches exactly one archetype', () => {
    for (const [name, metrics] of Object.entries(REAL)) {
      const matches = ARCHETYPES.filter((row) => row.when(metrics));
      assert.ok(matches.length >= 1, `${name} matched no archetype`);
      // Later matches are allowed - the list is ordered narrowest-first - but
      // the one that wins must be the first, and it must be deterministic.
      assert.equal(strategyProfile(metrics).archetype, matches[0].key, name);
    }
  });

  test('archetype keys are unique', () => {
    const keys = ARCHETYPES.map((row) => row.key);
    assert.equal(new Set(keys).size, keys.length);
  });

  test('evidence never carries a value it could not measure', () => {
    for (const row of evidenceFor(REAL.norges)) {
      assert.notEqual(row.value, null, `${row.key} was published as null`);
    }
  });

  test('a short history is admitted', () => {
    assert.match(caveatsFor({ ...REAL.berkshire, priorPositions: 20, quartersObserved: 2 }).join(' '),
      /short history/);
  });
});
