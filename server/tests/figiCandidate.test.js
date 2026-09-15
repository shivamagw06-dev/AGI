import test from 'node:test';
import assert from 'node:assert/strict';
import { preferredFigiCandidate, noCandidateReason } from '../services/figiCandidate.js';

// Shaped like a real OpenFIGI answer for a US company that also trades in
// Europe. The foreign lines are what used to win when no US line was present.
const honeywell = {
  data: [
    { ticker: 'HONGBP', exchCode: 'LN', marketSector: 'Equity', securityType2: 'Common Stock', compositeFIGI: 'BBG000X1' },
    { ticker: 'HON', exchCode: 'US', marketSector: 'Equity', securityType2: 'Common Stock', compositeFIGI: 'BBG000H5' },
    { ticker: 'HON1', exchCode: 'GR', marketSector: 'Equity', securityType2: 'Common Stock' },
  ],
};

test('the US line wins when there is one', () => {
  assert.equal(preferredFigiCandidate(honeywell).ticker, 'HON');
});

test('no US line means no ticker, not a foreign one', () => {
  // This is the whole fix. HONGBP, LRCXEUR and 8QR entered the holdings
  // because the score merely preferred a US listing and fell through to
  // whatever venue ranked next. A security reportable on Form 13F trades on
  // a US exchange, so a foreign symbol is never the right answer for it.
  const foreignOnly = { data: honeywell.data.filter((r) => r.exchCode !== 'US') };
  assert.equal(preferredFigiCandidate(foreignOnly), null);
});

test('a wrong ticker is worse than none, so nothing is guessed', () => {
  // A single plausible-looking foreign line is the tempting case: it is the
  // only answer available, and taking it splits the issuer's ownership across
  // two tickers in the screener while pricing neither correctly.
  const only = { data: [{ ticker: '8QR', exchCode: 'GR', marketSector: 'Equity', securityType2: 'Common Stock' }] };
  assert.equal(preferredFigiCandidate(only), null);
});

test('among US lines, an ordinary share beats an unusual instrument', () => {
  const result = {
    data: [
      { ticker: 'XYZW', exchCode: 'US', marketSector: 'Equity', securityType2: 'Warrant' },
      { ticker: 'XYZ', exchCode: 'US', marketSector: 'Equity', securityType2: 'Common Stock' },
    ],
  };
  assert.equal(preferredFigiCandidate(result).ticker, 'XYZ');
});

test('among equal US lines, the composite names the security', () => {
  const result = {
    data: [
      { ticker: 'ABC', exchCode: 'US', marketSector: 'Equity', securityType2: 'Common Stock' },
      { ticker: 'ABC', exchCode: 'US', marketSector: 'Equity', securityType2: 'Common Stock', compositeFIGI: 'BBG1' },
    ],
  };
  assert.equal(preferredFigiCandidate(result).compositeFIGI, 'BBG1');
});

test('a non-equity line is not a ticker for an equity holding', () => {
  const result = { data: [{ ticker: 'HON', exchCode: 'US', marketSector: 'Corp', securityType2: 'Note' }] };
  assert.equal(preferredFigiCandidate(result), null);
});

test('an empty or malformed answer yields nothing rather than throwing', () => {
  assert.equal(preferredFigiCandidate(null), null);
  assert.equal(preferredFigiCandidate({}), null);
  assert.equal(preferredFigiCandidate({ data: [] }), null);
});

test('the reason distinguishes unknown from listed-elsewhere', () => {
  // These need different work: one wants the SEC ticker file, the other wants
  // a look at whether the identifier itself is right.
  assert.match(noCandidateReason({ data: [] }), /no OpenFIGI listing/);
  const foreignOnly = { data: honeywell.data.filter((r) => r.exchCode !== 'US') };
  assert.match(noCandidateReason(foreignOnly), /listed only outside the US \(LN, GR\)/);
  assert.match(noCandidateReason({ data: [{ marketSector: 'Corp' }] }), /not as equity/);
});
