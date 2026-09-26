import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { investorSlug, investorPath, numberFromDisclosure, disclosureStatus, portfolioCsv } from './investorProfiles.js';

const root = new URL('../data/investorProfiles/', import.meta.url);
const directory = JSON.parse(fs.readFileSync(new URL('index.json', root), 'utf8'));
const profiles = directory.map(item => JSON.parse(fs.readFileSync(new URL(`holdings/${item.country.toLowerCase()}-${item.slug}.json`, root), 'utf8')));

test('all 134 India and US investors have distinct resolvable profile routes', () => {
  assert.equal(directory.length, 134);
  assert.equal(directory.filter(row => row.country === 'IN').length, 63);
  assert.equal(directory.filter(row => row.country === 'US').length, 71);
  assert.equal(new Set(directory.map(row => investorPath(row.country, row.name))).size, 134);
  for (const row of directory) assert.equal(row.slug, investorSlug(row.name));
  assert.notEqual(investorPath('IN', 'Mohnish Pabrai'), investorPath('US', 'Mohnish Pabrai'));
});

test('every snapshot preserves aligned reporting periods and explicit provenance', () => {
  for (const profile of profiles) {
    assert.ok(profile.sourceUrl?.startsWith('https://'), profile.name);
    assert.ok(profile.retrievedAt && profile.coverageLabel && profile.coverageNote, profile.name);
    for (const row of profile.rows) {
      assert.ok(row.stock && !row.stock.includes(''), profile.name);
      assert.equal(row.history.length, profile.periods.length, `${profile.name}: ${row.stock}`);
    }
    if (!profile.rows.length) assert.equal(profile.coverageLabel, 'Detailed source unavailable');
    if (profile.rows.length && (profile.sourceLimited || !profile.retrievalComplete)) assert.equal(profile.coverageLabel, 'Partial disclosed portfolio');
    if (profile.kind === 'sec13f') {
      assert.equal(profile.periods[0], 'Portfolio weight (%)');
      assert.ok(profile.managerName);
      assert.ok(profile.rows.every(row => row.security && row.cusip));
    }
  }
});

test('source units, missing disclosures and below-threshold positions are not conflated', () => {
  assert.equal(numberFromDisclosure('-'), null);
  assert.equal(numberFromDisclosure('0%'), 0);
  assert.equal(numberFromDisclosure('1,000'), 1000);
  assert.equal(disclosureStatus({ change: 'Below 1% first time' }), 'Below threshold');
  assert.equal(disclosureStatus({ change: 'New' }), 'New disclosure');
  assert.equal(disclosureStatus({ change: 'Add 8.73%' }), 'Increased');
  assert.equal(disclosureStatus({ change: 'Reduce 5.35%' }), 'Reduced');
  assert.equal(disclosureStatus({ change: null, quantity: null, history: ['2.4%'] }), 'Disclosed');
  assert.equal(disclosureStatus({ change: '-', quantity: '-', history: ['-','2.4%'] }), 'Historical / unavailable');
  const india = profiles.find(row => row.name === 'Radhakishan Damani');
  assert.ok(india.rows.find(row => row.stock === 'Sundaram Finance').history.includes('-'));
  assert.ok(india.rows.find(row => row.stock === 'Avenue Supermarts').value.endsWith(' Cr'));
  const berkshire = profiles.find(row => row.name === 'Warren Buffett');
  assert.equal(berkshire.managerName, 'Berkshire Hathaway');
  assert.equal(berkshire.reportPeriod, '2026-06-30');
});

test('CSV includes provenance and security class, escapes quotes and neutralizes formulas', () => {
  const csv = portfolioCsv({ periods: ['Portfolio weight (%)'], rows: [{stock:'=HYPERLINK("bad")', security:'COM · Put · SH', cusip:'123', quantity:'2', value:'3 M', change:'-2.5', history:['1%']}], sourceUrl:'https://example.com/filing', reportPeriod:'2026-06-30', retrievedAt:'2026-09-26' });
  assert.ok(csv.includes('"\'=HYPERLINK(""bad"")"'));
  assert.ok(csv.includes('"COM · Put · SH"'));
  assert.ok(csv.includes('"-2.5"'));
  assert.ok(csv.includes('"https://example.com/filing","2026-06-30","2026-09-26"'));
});
