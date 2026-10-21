import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { ADVISER_ABSENCE, ABSENCE_KINDS, adviserAbsence, unmatchedAbsenceSlugs } from '../services/adviserAbsence.js';
import { attachProfiles } from '../services/institutionalResearchLayerService.js';

/**
 * Seventeen managers matched no adviser registration and the page said the
 * same thing about all of them. Nine of those absences are permanent facts
 * about the manager; the rest are facts about our matching. The risk in fixing
 * that is stating the first about a manager that is really the second.
 */
describe('why a manager has no Form ADV', () => {
  test('an absence that will never be filled is explained', () => {
    const berkshire = adviserAbsence('berkshire-hathaway');
    assert.equal(berkshire.kind, 'operating_company');
    assert.match(berkshire.explanation, /files 13F on its own corporate holdings/);
    assert.match(berkshire.basis, /no firm under this name/);
  });

  test('a manager we merely failed to match gets no explanation', () => {
    // Baker Bros registers as BAKER BROTHERS INVESTMENTS, Himalaya as
    // HIMALAYA CAPITAL, Dalal Street as one of two Pabrai entities. All of
    // them have a registration; claiming a reason they have none would state
    // the opposite of the truth.
    for (const slug of ['baker-bros-advisors', 'himalaya-capital',
      'jane-street', 'baillie-gifford', 'dalal-street', 'blackrock']) {
      assert.equal(adviserAbsence(slug), null, slug);
    }
    assert.equal(adviserAbsence(''), null);
    assert.equal(adviserAbsence(undefined), null);
  });

  test('the evidence is carried, not just the conclusion', () => {
    // Twenty-one firms answered to "BlackRock" and one to "Alphabet". Zero
    // results supports "there is nothing to find"; near misses support the
    // category but not as firmly, and the card says which it had.
    assert.match(adviserAbsence('alphabet').basis, /other firms under this name/);
    assert.match(adviserAbsence('nvidia').basis, /no firm under this name/);
  });

  test('every listed manager has a category that exists', () => {
    // A typo in a kind would silently drop the explanation and return the
    // manager to the generic blank this file exists to remove.
    for (const [slug, entry] of Object.entries(ADVISER_ABSENCE)) {
      assert.ok(ABSENCE_KINDS[entry.kind], `${slug} has unknown kind ${entry.kind}`);
      assert.ok(['no_results', 'near_misses'].includes(entry.basis), `${slug} basis`);
      assert.ok(adviserAbsence(slug), slug);
    }
  });

  test('a key that matches no manager is reported, not swallowed', () => {
    // The failure this file cannot see from the inside. "NVIDIA Corp" is the
    // slug `nvidia`, not `nvidia-corp`; keyed on the latter the card would have
    // shown the generic blank and nothing would have said why.
    const tracked = Object.keys(ADVISER_ABSENCE).map((slug) => ({ slug }));
    assert.deepEqual(unmatchedAbsenceSlugs(tracked), []);
    assert.deepEqual(unmatchedAbsenceSlugs([{ slug: 'berkshire-hathaway' }]).includes('nvidia'), true);
    assert.deepEqual(unmatchedAbsenceSlugs([]).length, Object.keys(ADVISER_ABSENCE).length);
  });

  test('no explanation attaches to a manager that has a registration', () => {
    // Both fields populated would let the card say a firm is registered and
    // say why it cannot be, on the same row.
    const rows = attachProfiles(
      [{ id: 'm1', slug: 'berkshire-hathaway', display_name: 'Berkshire Hathaway' },
        { id: 'm2', slug: 'citadel-advisors', display_name: 'Citadel Advisors' }],
      [],
      [{ manager_id: 'm2', legal_name: 'CITADEL ADVISORS LLC', crd: '148826' }],
    );
    const [berkshire, citadel] = rows;
    assert.equal(berkshire.adviser, null);
    assert.equal(berkshire.adviser_absence.kind, 'operating_company');
    assert.equal(citadel.adviser.crd, '148826');
    assert.equal(citadel.adviser_absence, null);
  });
});
