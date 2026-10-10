import test from 'node:test';
import assert from 'node:assert/strict';
import { summariseInsiderFilings, insiderHeadline, transactionsOf } from '../services/insiderSummary.js';

const filing = (parsed, filed_at = '2026-09-01') => ({
  accession_number: `a${Math.random()}`, filed_at, source_url: 'x', parsed_data: parsed,
});
const owner = [{ name: 'Jane Doe', officer_title: 'CFO', roles: ['officer'] }];

test('a vesting event is not reported as insider selling', () => {
  // The failure this exists to prevent. Shares withheld to pay tax on a grant
  // is a payroll event; totalling it as a sale produces alarming activity out
  // of a vesting calendar.
  const rows = [filing({
    owners: owner, planned: false,
    transactions: [
      { code: 'A', discretionary: false, direction: 'acquire', shares: 5000, value_usd: null },
      { code: 'F', discretionary: false, direction: 'dispose', shares: 2100, value_usd: 105000 },
    ],
  })];
  const s = summariseInsiderFilings(rows, { asOf: '2026-09-08' });
  assert.equal(s.sell_value, 0);
  assert.equal(s.sell_count, 0);
  assert.equal(s.routine_count, 2);
  assert.match(insiderHeadline(s), /all grants, option exercises or tax withholding/);
});

test('a discretionary purchase is counted and named', () => {
  const rows = [filing({
    owners: owner, planned: false,
    transactions: [{ code: 'P', discretionary: true, direction: 'acquire', shares: 1000, value_usd: 250000 }],
  })];
  const s = summariseInsiderFilings(rows, { asOf: '2026-09-08' });
  assert.equal(s.buy_count, 1);
  assert.equal(s.buy_value, 250000);
  assert.match(insiderHeadline(s), /1 discretionary purchase/);
});

test('a pre-arranged sale is counted but flagged', () => {
  // A sale under a plan adopted months earlier is a real transaction and not
  // a view on the price today. Hiding it would understate activity; showing
  // it unmarked would overstate what it means.
  const rows = [filing({
    owners: owner, planned: true,
    transactions: [{ code: 'S', discretionary: true, direction: 'dispose', shares: 1439, value_usd: 456177 }],
  })];
  const s = summariseInsiderFilings(rows, { asOf: '2026-09-08' });
  assert.equal(s.sell_count, 1);
  assert.equal(s.planned_count, 1);
  assert.match(insiderHeadline(s), /under a pre-arranged plan/);
});

test('a filing that could not be read is unknown activity, not none', () => {
  // Folding an unparsed filing into the totals reports an absence nobody
  // observed.
  const rows = [filing({ primary_document: 'form4.xml', parse_status: 'unread' })];
  const s = summariseInsiderFilings(rows, { asOf: '2026-09-08' });
  assert.equal(s.unread, 1);
  assert.equal(s.events.length, 0);
  assert.match(insiderHeadline(s), /could not be read/);
  assert.equal(transactionsOf(rows[0]), null);
});

test('silence is reported as silence', () => {
  const s = summariseInsiderFilings([], { asOf: '2026-09-08' });
  assert.match(insiderHeadline(s), /No insider filings/);
});

test('filings outside the window are excluded', () => {
  const rows = [
    filing({ owners: owner, transactions: [{ code: 'P', discretionary: true, direction: 'acquire', shares: 1, value_usd: 10 }] }, '2026-09-01'),
    filing({ owners: owner, transactions: [{ code: 'P', discretionary: true, direction: 'acquire', shares: 1, value_usd: 99 }] }, '2024-01-01'),
  ];
  const s = summariseInsiderFilings(rows, { asOf: '2026-09-08', sinceDays: 180 });
  assert.equal(s.buy_count, 1);
  assert.equal(s.buy_value, 10);
});

test('events are ordered newest transaction first', () => {
  const rows = [filing({
    owners: owner,
    transactions: [
      { code: 'P', discretionary: true, direction: 'acquire', transaction_date: '2026-07-01', shares: 1, value_usd: 1 },
      { code: 'P', discretionary: true, direction: 'acquire', transaction_date: '2026-08-15', shares: 1, value_usd: 1 },
    ],
  })];
  const s = summariseInsiderFilings(rows, { asOf: '2026-09-08' });
  assert.deepEqual(s.events.map((e) => e.transaction_date), ['2026-08-15', '2026-07-01']);
});

test('distinct insiders are counted, not filings', () => {
  // Three filings from one officer is one person acting, not three.
  const rows = [1, 2, 3].map(() => filing({
    owners: owner,
    transactions: [{ code: 'P', discretionary: true, direction: 'acquire', shares: 1, value_usd: 1 }],
  }));
  assert.equal(summariseInsiderFilings(rows, { asOf: '2026-09-08' }).distinct_insiders, 1);
});
