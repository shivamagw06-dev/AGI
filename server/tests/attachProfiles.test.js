import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { attachProfiles } from '../services/institutionalResearchLayerService.js';

/**
 * The page renders whatever this returns, so the two ways it can quietly go
 * wrong both have to fail here instead.
 *
 * A profile attached to the wrong manager is worse than a missing one: the
 * reader has no way to tell, and the page states Berkshire's book shape under
 * Citadel's name. And `strategy` is an overloaded field - institutional_managers
 * has carried a hand-written strategy label since seed time, asserted rather
 * than measured, on ten of the fifty managers. If that leaked through, the
 * page would show an unverified claim in the place built for a measured one.
 */
const MANAGERS = [
  { id: 'm-berkshire', slug: 'berkshire-hathaway', display_name: 'Berkshire Hathaway', strategy: 'Concentrated quality and value', cik: '0001067983', quality_weight: 1.2 },
  { id: 'm-citadel', slug: 'citadel-advisors', display_name: 'Citadel Advisors', strategy: null },
  { id: 'm-thiel', slug: 'thiel-macro', display_name: 'Thiel Macro', strategy: null },
];
const STRATEGIES = [
  { manager_id: 'm-citadel', archetype: 'market_making', label: 'Multi-strategy / market making', confidence: 'high' },
  { manager_id: 'm-berkshire', archetype: 'concentrated_held', label: 'Concentrated and held', confidence: 'high' },
];
const ADVISERS = [
  { manager_id: 'm-citadel', legal_name: 'CITADEL ADVISORS LLC', crd: '148826' },
];

describe('the manager list the page renders', () => {
  test('each profile lands on the manager it was measured from', () => {
    const rows = attachProfiles(MANAGERS, STRATEGIES, ADVISERS);
    const byName = Object.fromEntries(rows.map((row) => [row.display_name, row]));
    // The strategy rows are deliberately in a different order from the
    // managers: anything that pairs them positionally passes an equal-length
    // test and fails this one.
    assert.equal(byName['Berkshire Hathaway'].strategy.archetype, 'concentrated_held');
    assert.equal(byName['Citadel Advisors'].strategy.archetype, 'market_making');
    assert.equal(byName['Citadel Advisors'].adviser.crd, '148826');
  });

  test('the measured profile occupies the field, not the asserted label', () => {
    // institutional_managers.strategy on Berkshire reads "Concentrated quality
    // and value", hand-typed at seed time. The page must not receive it under
    // the name it uses for the measured profile.
    const [berkshire] = attachProfiles([MANAGERS[0]], STRATEGIES, ADVISERS);
    assert.equal(typeof berkshire.strategy, 'object');
    assert.equal(berkshire.strategy.label, 'Concentrated and held');
  });

  test('a manager without a profile is kept, not dropped', () => {
    // Berkshire has no adviser registration because it is an operating company
    // that files 13F, and Thiel Macro has neither profile. Both are ordinary.
    const rows = attachProfiles(MANAGERS, STRATEGIES, ADVISERS);
    assert.equal(rows.length, 3);
    assert.equal(rows.find((row) => row.slug === 'berkshire-hathaway').adviser, null);
    const thiel = rows.find((row) => row.slug === 'thiel-macro');
    assert.equal(thiel.strategy, null);
    assert.equal(thiel.adviser, null);
  });

  test('nothing beyond identity and the two profiles reaches the page', () => {
    // cik and quality_weight are internal. A select('*') feeding this straight
    // through is how internal columns end up on a public surface.
    const [berkshire] = attachProfiles([MANAGERS[0]], STRATEGIES, ADVISERS);
    assert.deepEqual(Object.keys(berkshire).sort(),
      ['adviser', 'adviser_absence', 'campaigns', 'campaigns_heading',
        'display_name', 'id', 'said', 'slug', 'strategy']);
  });

  test('missing tables make an unenriched list, not an exception', () => {
    const rows = attachProfiles(MANAGERS, null, undefined);
    assert.equal(rows.length, 3);
    assert.equal(rows[0].strategy, null);
    assert.deepEqual(attachProfiles(), []);
  });
});

describe('board campaigns on the manager row', () => {
  const PROXY = [
    { manager_id: 'm-pershing', subject_cik: '0000008670', subject_name: 'AUTOMATIC DATA PROCESSING INC', form_type: 'DFAN14A', filed_at: '2017-11-06', source_url: 'https://sec.gov/adp-last/' },
    { manager_id: 'm-pershing', subject_cik: '0000008670', subject_name: 'AUTOMATIC DATA PROCESSING INC', form_type: 'PRRN14A', filed_at: '2017-08-04', source_url: 'https://sec.gov/adp-first/' },
    { manager_id: 'm-pershing', subject_cik: '0000850693', subject_name: 'ALLERGAN INC', form_type: 'DFAN14A', filed_at: '2014-11-14', source_url: 'https://sec.gov/agn/' },
  ];
  const MANAGERS = [
    { id: 'm-pershing', slug: 'pershing-square', display_name: 'Pershing Square' },
    { id: 'm-vanguard', slug: 'vanguard', display_name: 'The Vanguard Group' },
  ];

  test('campaigns land on the manager that ran them, hardest first', () => {
    const [pershing] = attachProfiles(MANAGERS, [], [], PROXY);
    assert.equal(pershing.campaigns.length, 2);
    assert.equal(pershing.campaigns[0].subject_name, 'AUTOMATIC DATA PROCESSING INC');
    assert.equal(pershing.campaigns[0].filings, 2);
    assert.equal(pershing.campaigns[0].first_filed, '2017-08-04');
    assert.equal(pershing.campaigns[0].last_filed, '2017-11-06');
  });

  test('the heading names what the manager actually did', () => {
    // Pershing Square ran contested fights; a sovereign fund filing one
    // exempt solicitation per company did not.
    const [pershing] = attachProfiles(MANAGERS, [], [], PROXY);
    assert.equal(pershing.campaigns_heading, 'Board campaigns');
    const proposals = attachProfiles(
      [{ id: 'm-norges', slug: 'norges-bank', display_name: 'Norges Bank' }], [], [],
      [{ manager_id: 'm-norges', subject_cik: '1', subject_name: 'WELLS FARGO & CO/MN', form_type: 'PX14A6G', filed_at: '2012-04-02' }],
    );
    assert.equal(proposals[0].campaigns_heading, 'Shareholder proposals');
  });

  test('a manager that has never fought a board gets an empty list', () => {
    // Six of the fifty have campaigns at all. An empty array renders as
    // nothing; a null would have the page testing for it in two ways.
    const vanguard = attachProfiles(MANAGERS, [], [], PROXY)[1];
    assert.deepEqual(vanguard.campaigns, []);
  });

  test('no proxy table is an unenriched list, not an exception', () => {
    for (const absent of [undefined, null, []]) {
      const rows = attachProfiles(MANAGERS, [], [], absent);
      assert.equal(rows.length, 2);
      assert.deepEqual(rows[0].campaigns, []);
    }
  });
});
