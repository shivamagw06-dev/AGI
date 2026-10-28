import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  classifyInstrument,
  instrumentUniverseSummary,
  pickIsinCompanies,
  statementRequests,
} from '../services/upstoxFundamentalsRefresh.js';

describe('Upstox annual statement backfill', () => {
  it('keeps stocks and excludes ETFs/funds from company financial requests', () => {
    const rows = [
      { symbol: 'TCS', isin: 'INE467B01029', company_name: 'Tata Consultancy Services Limited' },
      { symbol: 'NIFTYBEES', isin: 'INF204KB14I2', company_name: 'Nippon India ETF Nifty BeES' },
      { symbol: 'GOLDBEES', isin: 'INF204KB17I5', company_name: 'Nippon India ETF Gold BeES' },
    ];
    assert.equal(classifyInstrument(rows[0]).type, 'STOCK');
    assert.equal(classifyInstrument(rows[1]).type, 'FUND');
    assert.deepEqual(pickIsinCompanies(rows, { limit: 10 }).map((row) => row.symbol), ['TCS']);
    assert.deepEqual(instrumentUniverseSummary(rows), { STOCK: 1, ETF: 0, FUND: 2, UNKNOWN: 0 });
  });

  it('builds exactly three full annual statement calls for backfill', () => {
    const requests = statementRequests({ annualOnly: true });
    assert.equal(requests.length, 3);
    assert.deepEqual(requests.map(([endpoint]) => endpoint), ['income-statement', 'balance-sheet', 'cash-flow']);
    for (const [, params] of requests) {
      assert.equal(params.type, 'consolidated');
      assert.equal(params.time_period, 'yearly');
      assert.equal(params.fs, true);
    }
  });

  it('keeps the normal refresh capable of quarterly data', () => {
    const requests = statementRequests();
    assert.equal(requests.length, 4);
    assert.deepEqual(requests[3], [
      'income-statement',
      { type: 'consolidated', time_period: 'quarterly', fs: false },
    ]);
    assert.equal(requests.some(([endpoint, params]) =>
      endpoint !== 'income-statement' && params.time_period === 'quarterly'), false);
  });
});
