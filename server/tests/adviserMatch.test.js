import test from 'node:test';
import assert from 'node:assert/strict';
import { matchAdviser, officeAddress, advDate } from '../services/adviserMatch.js';

const firm = (name, id, over = {}) => ({ firm_name: name, firm_source_id: id, ...over });

test('the manager matches its own registration', () => {
  const hits = [
    firm('OIA LTD', '136174'),
    firm('BRIDGEWATER ADVISORS INC.', '109826'),
    firm('BRIDGEWATER ASSOCIATES, LP', '105129'),
  ];
  const found = matchAdviser('Bridgewater Associates', hits);
  assert.equal(found.firm.firm_source_id, '105129');
  assert.equal(found.matchedBy, 'legal name');
});

test('the search index matches loosely and this does not', () => {
  // Asking the adviser search for "bridgewater" returns OIA LTD first, because
  // BRIDGEWATER appears in that firm's list of other names. The search narrows;
  // this decides.
  assert.equal(matchAdviser('Bridgewater Associates', [firm('OIA LTD', '136174', { firm_other_names: ['BRIDGEWATER'] })]), null);
});

test('a dotted form is the same firm', () => {
  // Most funds are constituted as an LP or LLC and file with the periods in.
  // Read as punctuation those become single letters that match nothing, which
  // is how the names least able to match were the ones most needed.
  assert.equal(matchAdviser('Coatue Management', [firm('COATUE MANAGEMENT, L.L.C.', '1')]).firm.firm_source_id, '1');
  assert.equal(matchAdviser('D1 Capital Partners', [firm('D1 CAPITAL PARTNERS L.P.', '2')]).firm.firm_source_id, '2');
  assert.equal(matchAdviser('Pershing Square Capital Management', [firm('PERSHING SQUARE CAPITAL MANAGEMENT, L.P.', '3')]).firm.firm_source_id, '3');
});

test('a longer name that contains the manager is a different firm', () => {
  // The danger of matching loosely rather than exactly. "Citadel" is inside
  // CITADEL ADVISORS, CITADEL SECURITIES and CITADEL ENTERPRISE - three
  // different registrations, one of which trades and one of which does not.
  const hits = [firm('CITADEL ADVISORS LLC', '148826'), firm('CITADEL SECURITIES LLC', '116797')];
  assert.equal(matchAdviser('Citadel', hits), null);
  assert.equal(matchAdviser('Citadel Advisors', hits).firm.firm_source_id, '148826');

  // With one candidate rather than two, nothing else can refuse it: a rule
  // that accepted a name merely containing the manager's would link Citadel to
  // Citadel Advisors here, and the ambiguity check would never see it.
  assert.equal(matchAdviser('Citadel', [firm('CITADEL ADVISORS LLC', '148826')]), null);
});

test('two firms answering to one name is a refusal', () => {
  // A wrong link does not fail loudly. It puts another firm's registration
  // date, address and disclosure flag on a manager's profile, where it reads
  // as fact.
  const hits = [firm('ACME CAPITAL LLC', '1'), firm('ACME CAPITAL, L.L.C.', '2')];
  assert.equal(matchAdviser('Acme Capital', hits), null);
});

test('one firm listed twice under one CRD is still one match', () => {
  const hits = [firm('ACME CAPITAL LLC', '1'), firm('ACME CAPITAL, L.L.C.', '1')];
  assert.equal(matchAdviser('Acme Capital', hits).firm.firm_source_id, '1');
});

test('a manager that is not a registered adviser matches nothing', () => {
  // The normal case, not an error. Berkshire Hathaway is an operating company
  // that files 13F, and a family office has been exempt from registering since
  // 2011.
  assert.equal(matchAdviser('Berkshire Hathaway', []), null);
  assert.equal(matchAdviser('Duquesne Family Office', [firm('DUQUESNE CAPITAL MANAGEMENT LLC', '9')]), null);
});

test('a name that is only corporate form matches nothing', () => {
  // Both sides reduce to nothing, and nothing must not equal nothing here:
  // that would link the first firm whose name is pure suffix to a manager
  // whose name is too.
  assert.equal(matchAdviser('Inc.', [firm('L.L.C.', '1')]), null);
  assert.equal(matchAdviser('   ', [firm('Corp', '2')]), null);
});

test('a firm with no CRD cannot be linked', () => {
  assert.equal(matchAdviser('Acme Capital', [firm('ACME CAPITAL', undefined)]), null);
});

test('nothing in yields nothing out, without throwing', () => {
  assert.equal(matchAdviser('', [firm('ACME', '1')]), null);
  assert.equal(matchAdviser('Acme', undefined), null);
  assert.equal(matchAdviser(undefined, []), null);
});

test('the office address is JSON inside a string', () => {
  const withAddress = firm('X', '1', { firm_ia_address_details: '{"officeAddress": {"city": "WESTPORT", "country": "United States"}}' });
  assert.deepEqual(officeAddress(withAddress), { city: 'WESTPORT', country: 'United States' });
});

test('an address that does not parse costs nothing', () => {
  // The field is a string of JSON and nothing guarantees it parses. An address
  // is the least of what the profile carries.
  for (const raw of ['not json', '', null, undefined, '{"broken":']) {
    assert.deepEqual(officeAddress(firm('X', '1', { firm_ia_address_details: raw })), { city: null, country: null });
  }
  assert.deepEqual(officeAddress(undefined), { city: null, country: null });
});

test('filed dates are US order and become ISO', () => {
  assert.equal(advDate('08/18/2026'), '2026-08-18');
  assert.equal(advDate('1/12/1990'), '1990-01-12');
});

test('a date that is not one is null, not today', () => {
  // A profile saying a firm registered today because its date would not parse
  // is worse than one that says nothing.
  // Including a date shaped right and meaning nothing: 18/08/2026 is a real
  // format somewhere, and month 18 is not a month.
  for (const bad of ['', null, undefined, '2026-08-18', 'August 18 2026', '18/08/2026', '18/08/2026 extra', 'x/y/z', '13/13/2026']) {
    assert.equal(advDate(bad), null, JSON.stringify(bad));
  }
});
