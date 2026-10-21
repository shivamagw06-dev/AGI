import test from 'node:test';
import assert from 'node:assert/strict';
import { inNseScreenerRefreshWindow } from './nseScreenerScheduler.js';

test('daily screener refresh waits until after market close in IST', () => {
  assert.equal(inNseScreenerRefreshWindow(new Date('2026-09-30T10:40:00Z'), () => true), false); // 16:10 IST
  assert.equal(inNseScreenerRefreshWindow(new Date('2026-09-30T10:45:00Z'), () => true), true);  // 16:15 IST
  assert.equal(inNseScreenerRefreshWindow(new Date('2026-09-30T10:45:00Z'), () => false), false); // holiday
});
