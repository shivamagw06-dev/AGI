import assert from 'node:assert/strict';
import test from 'node:test';
import { recentSessions, sessionState, sessionWindowsFilter } from './liveAlphaSession.js';

const ist = (value) => new Date(`${value}+05:30`);

test('the session is open 09:15 to 15:30 IST on a trading weekday', () => {
  assert.equal(sessionState(ist('2026-09-17T09:14:00')).reason, 'market_closed_before_open');
  assert.equal(sessionState(ist('2026-09-17T09:15:00')).open, true);
  assert.equal(sessionState(ist('2026-09-17T15:29:59')).open, true);
  assert.equal(sessionState(ist('2026-09-17T15:30:00')).reason, 'market_closed_after_close');
});

test('weekends and exchange holidays are closed all day', () => {
  // Live Alpha stored shortlists on all three before this gate existed.
  assert.equal(sessionState(ist('2026-09-19T11:00:00')).reason, 'market_closed_non_trading_day');
  assert.equal(sessionState(ist('2026-09-13T11:00:00')).reason, 'market_closed_non_trading_day');
  assert.equal(sessionState(ist('2026-09-14T11:00:00')).reason, 'market_closed_non_trading_day');
});

test('a margin widens the window for connecting and collecting', () => {
  const margin = { leadMs: 10 * 60_000, lagMs: 5 * 60_000 };
  assert.equal(sessionState(ist('2026-09-17T09:06:00'), margin).open, true);
  assert.equal(sessionState(ist('2026-09-17T15:34:00'), margin).open, true);
  assert.equal(sessionState(ist('2026-09-19T11:00:00'), margin).open, false);
});

test('recent sessions skip weekends and holidays, newest first', () => {
  const sessions = recentSessions(ist('2026-09-19T12:00:00'), 4);
  assert.deepEqual(sessions.map((row) => row.date), ['2026-09-18', '2026-09-17', '2026-09-16', '2026-09-15']);
  // A session that has not started yet is not recent.
  assert.equal(recentSessions(ist('2026-09-21T08:00:00'), 1)[0].date, '2026-09-18');
  const filter = sessionWindowsFilter('as_of', sessions.slice(0, 1));
  assert.equal(filter, '(and(as_of.gte.2026-09-18T03:45:00.000Z,as_of.lte.2026-09-18T10:00:00.000Z))');
});
