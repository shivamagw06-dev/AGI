import { resolveMarketSession, sessionById, SESSIONS } from './marketSession.js';

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

assert(SESSIONS.length === 5, 'expected 5 sessions');
assert(sessionById('pre').label === 'Pre Market', 'pre label');
assert(sessionById('global').topics.includes('US Futures'), 'global topics');

// Fixed IST-oriented checks via UTC dates that map into known IST windows.
// 03:30 UTC = 09:00 IST
assert(resolveMarketSession(new Date('2026-07-29T03:30:00.000Z')) === 'morning', '09:00 IST morning');
// 07:00 UTC = 12:30 IST
assert(resolveMarketSession(new Date('2026-07-29T07:00:00.000Z')) === 'afternoon', '12:30 IST afternoon');
// 10:30 UTC = 16:00 IST
assert(resolveMarketSession(new Date('2026-07-29T10:30:00.000Z')) === 'post', '16:00 IST post');
// 13:00 UTC = 18:30 IST
assert(resolveMarketSession(new Date('2026-07-29T13:00:00.000Z')) === 'global', '18:30 IST global');
// 02:00 UTC = 07:30 IST
assert(resolveMarketSession(new Date('2026-07-29T02:00:00.000Z')) === 'pre', '07:30 IST pre');

console.log('marketSession.test.js OK');
