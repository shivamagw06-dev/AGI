import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { sourceAuthority } from '../services/researchKnowledgeRegistry.js';

describe('researchKnowledgeRegistry', () => {
  it('gives official sources the highest authority tier', () => {
    assert.deepEqual(sourceAuthority('central_bank_report', 'RBI'), {
      tier: 1,
      reliability: 0.95,
    });
  });

  it('distinguishes house research from unverified user material', () => {
    const house = sourceAuthority('agi_research', 'Agarwal Global Investments');
    const unknown = sourceAuthority('other', 'uploaded material');
    assert.equal(house.tier, 5);
    assert.ok(house.reliability > unknown.reliability);
  });
});
