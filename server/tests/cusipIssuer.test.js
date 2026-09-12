import test from 'node:test';
import assert from 'node:assert/strict';
import { issuerPrefix, checkDigitValid, sectorByIssuer, sectorFromIssuer } from '../services/cusipIssuer.js';

test('the check digit separates real CUSIPs from filers\' option identifiers', () => {
  // Verified against the real holdings. The invalid ones are what filers
  // synthesise for options by replacing the issue digits, and they are most of
  // the tickerless value in the book.
  assert.equal(checkDigitValid('037833100'), true, 'AAPL common');
  assert.equal(checkDigitValid('037833950'), false, 'an option on AAPL');
  assert.equal(checkDigitValid('67066G104'), true, 'NVDA common');
  assert.equal(checkDigitValid('67066G904'), false, 'an option on NVDA');
  assert.equal(checkDigitValid('594918104'), true, 'MSFT common');
  assert.equal(checkDigitValid('594918904'), false, 'an option on MSFT');
  // Real securities whose filers simply gave no ticker.
  assert.equal(checkDigitValid('02079K602'), true, 'an Alphabet issue');
  assert.equal(checkDigitValid('958102AT2'), true, 'a Western Digital bond');
  assert.equal(checkDigitValid('670703107'), true, 'Nuvalent');
});

test('an option and its underlying share an issuer', () => {
  // The whole basis of the inference.
  assert.equal(issuerPrefix('037833100'), issuerPrefix('037833950'));
  assert.equal(issuerPrefix('67066G104'), issuerPrefix('67066G904'));
  assert.equal(issuerPrefix('46090E103'), issuerPrefix('46090E953'));
});

test('share classes of one company share an issuer too', () => {
  // GOOGL and GOOG, and they belong in the same sector.
  assert.equal(issuerPrefix('02079K305'), '02079K');
  assert.equal(issuerPrefix('02079K107'), '02079K');
});

test('a prefix is read only from something nine characters long', () => {
  // Truncating anything else to six would collide with a real issuer, which
  // is the one mistake this must not make.
  assert.equal(issuerPrefix('037833'), null);
  assert.equal(issuerPrefix('0378331000'), null);
  assert.equal(issuerPrefix(''), null);
  assert.equal(issuerPrefix(null), null);
  assert.equal(issuerPrefix(undefined), null);
  assert.equal(issuerPrefix('037833 10'), null);
  assert.equal(issuerPrefix('03783!100'), null);
});

test('a foreign CINS reads the same way', () => {
  // Gates Industrial and Janus Henderson both arrive with a leading letter.
  assert.equal(issuerPrefix('G39108108'), 'G39108');
  assert.equal(issuerPrefix('G4474Y214'), 'G4474Y');
});

test('an issuer whose securities agree lends its sector to the rest', () => {
  const byIssuer = sectorByIssuer([
    { cusip: '037833100', sector: 'Information Technology' },
    { cusip: '67066G104', sector: 'Information Technology' },
  ]);
  assert.equal(sectorFromIssuer('037833950', byIssuer), 'Information Technology');
  assert.equal(sectorFromIssuer('67066G904', byIssuer), 'Information Technology');
});

test('an issuer whose securities disagree lends nothing', () => {
  // Two sectors under one issuer means the assumption behind this whole idea
  // does not hold there, and a guess would be an invention.
  const byIssuer = sectorByIssuer([
    { cusip: '12345A100', sector: 'Financials' },
    { cusip: '12345A200', sector: 'Real Estate' },
  ]);
  assert.equal(byIssuer.has('12345A'), false);
  assert.equal(sectorFromIssuer('12345A950', byIssuer), null);
});

test('Unclassified is not evidence', () => {
  // An issuer known only through unclassified rows stays unknown, rather than
  // becoming Unclassified by a second route and looking resolved.
  const byIssuer = sectorByIssuer([
    { cusip: '12345A100', sector: 'Unclassified' },
    { cusip: '12345A200', sector: '' },
    { cusip: '12345A300', sector: null },
  ]);
  assert.equal(byIssuer.size, 0);
  assert.equal(sectorFromIssuer('12345A950', byIssuer), null);
});

test('Unclassified does not break an issuer that otherwise agrees', () => {
  // Ignored rather than counted as a second opinion: an issuer with one real
  // sector and one unclassified issue is not in disagreement with itself.
  const byIssuer = sectorByIssuer([
    { cusip: '037833100', sector: 'Information Technology' },
    { cusip: '037833200', sector: 'Unclassified' },
  ]);
  assert.equal(sectorFromIssuer('037833950', byIssuer), 'Information Technology');
});

test('an iShares prefix resolves although it covers many different funds', () => {
  // 464287 is the iShares Trust. It issues dozens of ETFs and this cannot say
  // which - but every one of them is a fund, which is the question being
  // asked.
  const byIssuer = sectorByIssuer([
    { cusip: '464287200', sector: 'Funds & ETFs' },
    { cusip: '464287655', sector: 'Funds & ETFs' },
    { cusip: '464287432', sector: 'Funds & ETFs' },
  ]);
  assert.equal(sectorFromIssuer('464287955', byIssuer), 'Funds & ETFs');
});

test('security_key stands in where cusip is absent', () => {
  const byIssuer = sectorByIssuer([{ security_key: '037833100', sector: 'Information Technology' }]);
  assert.equal(sectorFromIssuer('037833950', byIssuer), 'Information Technology');
});

test('nothing in yields nothing out, without throwing', () => {
  assert.equal(sectorByIssuer().size, 0);
  assert.equal(sectorByIssuer([]).size, 0);
  assert.equal(sectorFromIssuer('037833950', undefined), null);
  assert.equal(sectorFromIssuer(null, new Map()), null);
  assert.equal(checkDigitValid(null), false);
  assert.equal(checkDigitValid('!!!!!!!!!'), false);
});
