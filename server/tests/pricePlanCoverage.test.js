import test from 'node:test';
import assert from 'node:assert/strict';
import { planFetches } from '../services/pricePlan.js';

const asOf = '2026-09-10';
const daysBefore = (n) => new Date(Date.parse(asOf) - n * 86_400_000).toISOString().slice(0, 10);
const holding = (ticker, earliest) => ({ ticker, security_key: `K-${ticker}`, report_date: earliest });

const plan = (options) => planFetches(
  [holding('TSM', '2021-09-30')],
  { asOf, ...options },
);

test('a symbol whose history starts long after it was held is due again', () => {
  // The case that blocked twenty-two of fifty-one managers. TSM was fetched
  // recently, so the freshness log called it current, while its stored history
  // began 2022-12-01 against a first holding of 2021-09-30.
  const fresh = new Map([['TSM', daysBefore(1)]]);
  const coverage = new Map([['TSM', '2022-12-01']]);

  const withoutCoverage = plan({ freshness: fresh });
  assert.equal(withoutCoverage.plans.length, 0, 'freshness alone skips it, which is the bug');

  const withCoverage = plan({ freshness: fresh, coverage });
  assert.equal(withCoverage.plans.length, 1, 'knowing where the history starts makes it due');
  assert.equal(withCoverage.skipped.coverageGap, 1);
});

test('the refetch asks from the date it is held, not from where it left off', () => {
  // Asking from 2022-12-01 would return exactly what is already stored.
  const { plans } = plan({
    freshness: new Map([['TSM', daysBefore(1)]]),
    coverage: new Map([['TSM', '2022-12-01']]),
  });
  assert.ok(plans[0].from < '2021-09-30', `expected a start before the first holding, got ${plans[0].from}`);
  assert.equal(plans[0].earliestHeld, '2021-09-30');
});

test('a few days late is a holiday, not a gap', () => {
  // A security first held on a quarter end may simply not have traded that
  // day. Treating that as a gap would re-fetch most of the table every run.
  const { plans, skipped } = plan({
    freshness: new Map([['TSM', daysBefore(1)]]),
    coverage: new Map([['TSM', '2021-10-04']]),
  });
  assert.equal(plans.length, 0);
  assert.equal(skipped.coverageGap, 0);
  assert.equal(skipped.alreadyFresh, 1);
});

test('a gap is not throttled by when the symbol was last fetched', () => {
  // Every one of the twenty-nine stuck symbols had been fetched within days -
  // that is precisely why they were stuck. A throttle keyed on the fetch log
  // cannot tell a symbol never asked for with a wide enough window from one
  // asked and refused, and would have blocked the repair entirely.
  const coverage = new Map([['TSM', '2022-12-01']]);
  assert.equal(plan({ freshness: new Map([['TSM', daysBefore(0)]]), coverage }).plans.length, 1, 'fetched today');
  assert.equal(plan({ freshness: new Map([['TSM', daysBefore(3)]]), coverage }).plans.length, 1, 'fetched three days ago');
  assert.equal(plan({ freshness: new Map([['TSM', daysBefore(45)]]), coverage }).plans.length, 1, 'fetched last month');
});

test('a symbol never fetched is due whatever its coverage says', () => {
  const { plans } = plan({ freshness: new Map(), coverage: new Map([['TSM', '2022-12-01']]) });
  assert.equal(plans.length, 1);
});

test('a narrow refresh window is not judged on coverage', () => {
  // A daily refresh asks only for recent sessions by design, so its history
  // always starts after the holding. Reading that as a gap would turn every
  // refresh into a full backfill.
  const { plans, skipped } = plan({
    freshness: new Map([['TSM', daysBefore(1)]]),
    coverage: new Map([['TSM', '2022-12-01']]),
    windowDays: 10,
  });
  assert.equal(plans.length, 0);
  assert.equal(skipped.coverageGap, 0);
});

test('coverage the plan has never heard of changes nothing', () => {
  const { plans } = plan({ freshness: new Map([['TSM', daysBefore(1)]]), coverage: new Map([['NVDA', '2015-01-02']]) });
  assert.equal(plans.length, 0);
});

test('no coverage map at all behaves as before', () => {
  assert.equal(plan({ freshness: new Map([['TSM', daysBefore(1)]]) }).plans.length, 0);
  assert.equal(plan({ freshness: new Map() }).plans.length, 1);
});
