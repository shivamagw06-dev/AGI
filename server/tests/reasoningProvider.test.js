import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { reasoningProviderStatus } from '../services/reasoningProvider.js';

describe('reasoningProvider', () => {
  it('selects OpenAI without exposing credentials', () => {
    assert.deepEqual(reasoningProviderStatus({ AGI_REASONING_PROVIDER: 'openai', OPENAI_API_KEY: 'secret' }), {
      provider: 'openai', configured: true,
    });
  });

  it('normalizes Gemini to the Google adapter', () => {
    assert.deepEqual(reasoningProviderStatus({ MODEL_PROVIDER: 'gemini', GEMINI_API_KEY: 'secret' }), {
      provider: 'google', configured: true,
    });
  });

  it('supports a credential-free local endpoint', () => {
    assert.deepEqual(reasoningProviderStatus({ AGI_REASONING_PROVIDER: 'local', LOCAL_MODEL_BASE_URL: 'http://model:8000/' }), {
      provider: 'local', configured: true,
    });
  });
});
