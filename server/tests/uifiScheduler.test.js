import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { rotationOffset } from '../services/uifiScheduler.js';

describe('UIFI rotating schedules', () => {
  it('advances weekly batches instead of repeatedly refreshing offset zero', () => {
    const first = rotationOffset(new Date('2026-08-02T02:30:00Z'), 80, 7);
    const second = rotationOffset(new Date('2026-08-09T02:30:00Z'), 80, 7);
    assert.equal(second - first, 80);
  });

  it('advances daily corporate-action batches', () => {
    const first = rotationOffset(new Date('2026-08-10T13:20:00Z'), 100, 1);
    const second = rotationOffset(new Date('2026-08-11T13:20:00Z'), 100, 1);
    assert.equal(second - first, 100);
  });
});
