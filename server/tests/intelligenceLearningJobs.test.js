import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  LEARNING_PIPELINE_VERSION,
  LEARNING_STAGES,
  learningEnabled,
  learningModelRoles,
} from '../services/intelligenceLearningJobs.js';

describe('intelligenceLearningJobs', () => {
  it('defines a resumable ordered universal pipeline', () => {
    assert.equal(LEARNING_PIPELINE_VERSION, 'universal-learning-v4');
    assert.equal(LEARNING_STAGES[0], 'classification');
    assert.equal(LEARNING_STAGES.at(-1), 'validation');
    assert.ok(LEARNING_STAGES.includes('causal_intelligence'));
    assert.ok(LEARNING_STAGES.includes('financial_impact'));
  });

  it('keeps teacher roles configurable and learning disabled by default', () => {
    const roles = learningModelRoles({
      AGI_REASONING_PROVIDER: 'anthropic',
      AGI_LEARNING_EXTRACTION_MODEL: 'extractor',
      AGI_LEARNING_REASONING_MODEL: 'reasoner',
    });
    assert.deepEqual(roles, {
      provider: 'anthropic',
      extraction_model: 'extractor',
      reasoning_model: 'reasoner',
      critic_model: 'reasoner',
    });
    assert.equal(learningEnabled({}), false);
    assert.equal(learningEnabled({ NODE_ENV: 'production' }), true);
    assert.equal(learningEnabled({ NODE_ENV: 'production', AGI_INTELLIGENCE_LEARNING_ENABLED: 'false' }), false);
    assert.equal(learningEnabled({ AGI_INTELLIGENCE_LEARNING_ENABLED: 'true' }), true);
  });
});
