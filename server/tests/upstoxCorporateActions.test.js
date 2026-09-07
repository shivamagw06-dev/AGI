import assert from 'assert';
import { describe, it, beforeEach, afterEach } from 'node:test';
import {
  getCorporateActions,
  isUpstoxConfigured,
  resolveUpstoxAccessToken,
} from '../providers/upstox.js';
import { getUpstoxHealth } from '../services/upstoxHealth.js';

describe('upstox corporate actions', () => {
  const saved = {};

  beforeEach(() => {
    for (const k of Object.keys(process.env)) {
      if (k.startsWith('UPSTOX_')) {
        saved[k] = process.env[k];
        delete process.env[k];
      }
    }
  });

  afterEach(() => {
    for (const k of Object.keys(process.env)) {
      if (k.startsWith('UPSTOX_')) delete process.env[k];
    }
    Object.assign(process.env, saved);
    for (const k of Object.keys(saved)) delete saved[k];
  });

  it('treats short UPSTOX_API as client_id, not bearer token', () => {
    process.env.UPSTOX_API = 'short-client-id';
    const resolved = resolveUpstoxAccessToken();
    assert.equal(resolved.token, '');
    assert.equal(resolved.likely_client_id, true);
    assert.equal(isUpstoxConfigured(), false);
  });

  it('accepts long UPSTOX_API as access token alias', () => {
    process.env.UPSTOX_API = 'x'.repeat(48);
    const resolved = resolveUpstoxAccessToken();
    assert.equal(resolved.token.length, 48);
    assert.equal(resolved.source, 'UPSTOX_API');
    assert.equal(isUpstoxConfigured(), true);
  });

  it('pulls corporate-actions with Bearer token (mocked)', async () => {
    process.env.UPSTOX_ACCESS_TOKEN = 'test-access-token-with-enough-length-abcdefgh';
    const sample = {
      status: 'success',
      data: [
        {
          name: 'Dividend',
          expiry_date: '14 Aug 2025',
          amount: 5.5,
          ratio: null,
          event_details: [
            { name: 'Announcement date', value: '25 Apr 2025' },
            { name: 'Ex dividend date', value: '14 Aug 2025' },
            { name: 'Amount', value: '5.5' },
            { name: 'Details', value: 'Rs.5.5000 per share(55%)Final Dividend' },
          ],
        },
      ],
    };

    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url, opts) => {
      assert.match(String(url), /\/fundamentals\/INE002A01018\/corporate-actions$/);
      assert.equal(opts.headers.Authorization, 'Bearer test-access-token-with-enough-length-abcdefgh');
      return {
        ok: true,
        status: 200,
        json: async () => sample,
      };
    };

    try {
      const raw = await getCorporateActions('INE002A01018');
      assert.equal(raw.status, 'success');
      assert.equal(raw.data.length, 1);

      const health = await getUpstoxHealth({ isin: 'INE002A01018' });
      assert.equal(health.ok, true);
      assert.equal(health.corporate_actions.count, 1);
      assert.equal(health.corporate_actions.sample[0].name, 'Dividend');
      assert.equal(health.corporate_actions.sample[0].amount, 5.5);
      assert.ok(!JSON.stringify(health).includes('test-access-token'));
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
