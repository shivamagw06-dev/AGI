import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { CLOSE_MINUTE, OPEN_MINUTE, istParts, nseOpen } from './nseSession.js';

/**
 * IST is UTC+5:30 with no daylight saving, so each instant below is written
 * as the UTC time that corresponds to a known IST wall clock. Writing them in
 * UTC rather than with a +05:30 suffix is deliberate: it means the fixtures
 * cannot be read as "whatever the host thinks 09:15 is".
 *
 *   09:15 IST = 03:45Z     12:00 IST = 06:30Z     15:30 IST = 10:00Z
 *
 * 2026-09-17 is a Thursday and 2026-09-19 a Saturday; both are asserted
 * rather than assumed, so a wrong fixture fails loudly instead of quietly
 * testing the wrong day.
 */
const at = (iso) => new Date(iso);
const THURSDAY = '2026-09-17';
const SATURDAY = '2026-09-19';
const SUNDAY = '2026-09-20';

test('the fixture days are the weekdays the tests assume', () => {
  assert.equal(istParts(at(`${THURSDAY}T06:30:00Z`)).weekday, 'Thu');
  assert.equal(istParts(at(`${SATURDAY}T06:30:00Z`)).weekday, 'Sat');
  assert.equal(istParts(at(`${SUNDAY}T06:30:00Z`)).weekday, 'Sun');
});

test('before the open', () => {
  // 09:14 IST, one minute short.
  assert.equal(nseOpen(at(`${THURSDAY}T03:44:00Z`)), false);
});

test('exactly 09:15 IST is open', () => {
  const opening = at(`${THURSDAY}T03:45:00Z`);
  assert.deepEqual(
    { hour: istParts(opening).hour, minute: istParts(opening).minute },
    { hour: 9, minute: 15 },
  );
  assert.equal(istParts(opening).minuteOfDay, OPEN_MINUTE);
  assert.equal(nseOpen(opening), true);
});

test('during the session', () => {
  assert.equal(nseOpen(at(`${THURSDAY}T06:30:00Z`)), true);   // 12:00 IST
  assert.equal(nseOpen(at(`${THURSDAY}T05:00:00Z`)), true);   // 10:30 IST
  assert.equal(nseOpen(at(`${THURSDAY}T09:59:00Z`)), true);   // 15:29 IST
});

test('exactly 15:30 IST is still open', () => {
  const closing = at(`${THURSDAY}T10:00:00Z`);
  assert.deepEqual(
    { hour: istParts(closing).hour, minute: istParts(closing).minute },
    { hour: 15, minute: 30 },
  );
  assert.equal(istParts(closing).minuteOfDay, CLOSE_MINUTE);
  assert.equal(nseOpen(closing), true);
});

test('after the close', () => {
  assert.equal(nseOpen(at(`${THURSDAY}T10:01:00Z`)), false);  // 15:31 IST
  assert.equal(nseOpen(at(`${THURSDAY}T17:30:00Z`)), false);  // 23:00 IST
});

test('the weekend is closed even inside session hours', () => {
  // 12:00 IST on both weekend days: the clock says trading, the calendar does not.
  assert.equal(nseOpen(at(`${SATURDAY}T06:30:00Z`)), false);
  assert.equal(nseOpen(at(`${SUNDAY}T06:30:00Z`)), false);
});

test('an instant just before IST midnight does not roll into the next day', () => {
  // 23:59 IST Thursday = 18:29Z Thursday. A manual-offset version of this
  // function got the day wrong here.
  const late = at(`${THURSDAY}T18:29:00Z`);
  assert.equal(istParts(late).weekday, 'Thu');
  assert.equal(istParts(late).minuteOfDay, 23 * 60 + 59);
  assert.equal(nseOpen(late), false);
});

test('00:00 IST reads as minute zero, not minute 1440', () => {
  // Some ICU builds format midnight as "24". Left unnormalised, the session
  // check would compare 1440 against the close and answer wrongly.
  const midnight = at(`${THURSDAY}T18:30:00Z`);   // 00:00 IST Friday
  assert.equal(istParts(midnight).minuteOfDay, 0);
  assert.equal(nseOpen(midnight), false);
});

/**
 * The host's own timezone must not matter.
 *
 * This is the property the deleted offset arithmetic silently depended on, so
 * it is checked by actually running the module under different TZ values
 * rather than by reasoning that Intl handles it.
 */
const PROBE = `
import { nseOpen, istParts } from './src/lib/nseSession.js';
const at = (iso) => new Date(iso);
process.stdout.write(JSON.stringify({
  tz: process.env.TZ || null,
  hostOffsetMinutes: new Date('2026-09-17T06:30:00Z').getTimezoneOffset(),
  parts: istParts(at('2026-09-17T06:30:00Z')),
  beforeOpen: nseOpen(at('2026-09-17T03:44:00Z')),
  atOpen: nseOpen(at('2026-09-17T03:45:00Z')),
  during: nseOpen(at('2026-09-17T06:30:00Z')),
  atClose: nseOpen(at('2026-09-17T10:00:00Z')),
  afterClose: nseOpen(at('2026-09-17T10:01:00Z')),
  weekend: nseOpen(at('2026-09-19T06:30:00Z')),
}));
`;

const underTz = (tz) => JSON.parse(execFileSync(
  process.execPath, ['--input-type=module', '--eval', PROBE],
  { env: { ...process.env, TZ: tz }, encoding: 'utf8' },
));

test('a host running in UTC gets the same answers', () => {
  const utc = underTz('UTC');
  assert.equal(utc.hostOffsetMinutes, 0, 'the probe really did run in UTC');
  assert.deepEqual(utc.parts, { weekday: 'Thu', hour: 12, minute: 0, minuteOfDay: 720 });
  assert.deepEqual(
    [utc.beforeOpen, utc.atOpen, utc.during, utc.atClose, utc.afterClose, utc.weekend],
    [false, true, true, true, false, false],
  );
});

test('a host in another timezone gets the same answers', () => {
  // New York is behind UTC and observes DST; Kolkata itself is the adversarial
  // case where a leftover offset would cancel out and look correct.
  for (const tz of ['America/New_York', 'Pacific/Kiritimati', 'Asia/Kolkata']) {
    const run = underTz(tz);
    assert.deepEqual(run.parts, { weekday: 'Thu', hour: 12, minute: 0, minuteOfDay: 720 },
      `IST parts differed under TZ=${tz}`);
    assert.deepEqual(
      [run.beforeOpen, run.atOpen, run.during, run.atClose, run.afterClose, run.weekend],
      [false, true, true, true, false, false],
      `session answers differed under TZ=${tz}`);
  }
});

test('the hosts really did differ, or the test above proves nothing', () => {
  const offsets = ['UTC', 'America/New_York', 'Pacific/Kiritimati', 'Asia/Kolkata']
    .map((tz) => underTz(tz).hostOffsetMinutes);
  assert.equal(new Set(offsets).size, offsets.length,
    `expected four distinct host offsets, got ${JSON.stringify(offsets)}`);
});

/**
 * The host's own DST transition must not move IST.
 *
 * This is the case that separates an explicit `timeZone` from manual offset
 * arithmetic, and the earlier tests in this file do not reach it: for an
 * ordinary September instant the two approaches are arithmetically
 * equivalent, because the host offset cancels against formatting in the host
 * zone. They diverge only where the host offset itself changes.
 *
 * Measured, not assumed: across the US fallback on 1 November 2026 a manual
 * version reads IST a full hour early for six consecutive hours, because the
 * offset it looks up belongs to the shifted instant rather than the real one.
 *
 * IST has no daylight saving, so stepping UTC forward by an hour must always
 * step IST forward by exactly an hour - no repeated hour, no skipped one.
 */
const DST_PROBE = `
import { istParts } from './src/lib/nseSession.js';
const readings = [];
for (let h = 0; h < 48; h += 1) {
  const at = new Date(Date.UTC(2026, 10, 1, 0, 0, 0) + h * 3600e3);
  readings.push(istParts(at).minuteOfDay);
}
process.stdout.write(JSON.stringify({
  hostOffsetsSeen: [...new Set([0, 24].map((h) =>
    new Date(Date.UTC(2026, 10, 1, 0, 0, 0) + h * 3600e3).getTimezoneOffset()))],
  readings,
}));
`;

test('a host crossing its own DST boundary does not shift IST', () => {
  const run = JSON.parse(execFileSync(
    process.execPath, ['--input-type=module', '--eval', DST_PROBE],
    { env: { ...process.env, TZ: 'America/New_York' }, encoding: 'utf8' },
  ));

  // The probe is only meaningful if the host offset really did change.
  assert.equal(run.hostOffsetsSeen.length, 2,
    `expected the host offset to change across the boundary, saw ${JSON.stringify(run.hostOffsetsSeen)}`);

  for (let i = 1; i < run.readings.length; i += 1) {
    const step = (run.readings[i] - run.readings[i - 1] + 1440) % 1440;
    assert.equal(step, 60,
      `IST moved ${step} minutes for one UTC hour at index ${i} `
      + `(${run.readings[i - 1]} -> ${run.readings[i]}) — the host's DST leaked through`);
  }
});
