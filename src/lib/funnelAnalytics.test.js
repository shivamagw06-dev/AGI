import assert from 'node:assert/strict';
import { beforeEach, describe, it } from 'node:test';
import {
  getFunnelSummary,
  markSignupIntent,
  consumeSignupIntent,
  trackFunnelEvent,
  trackFirstMeaningfulAction,
} from './funnelAnalytics.js';

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }

  clear() {
    this.values.clear();
  }

  getItem(key) {
    return this.values.has(key) ? this.values.get(key) : null;
  }

  removeItem(key) {
    this.values.delete(key);
  }

  setItem(key, value) {
    this.values.set(key, String(value));
  }
}

globalThis.localStorage = new MemoryStorage();
globalThis.sessionStorage = new MemoryStorage();
globalThis.window = { dataLayer: [] };

describe('funnelAnalytics', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('records unlock → signup → activation stages', () => {
    trackFunnelEvent('unlock_screen', { feature: 'ask_agi' });
    markSignupIntent({ feature: 'ask_agi', channel: 'email' });
    trackFunnelEvent('signup_completed', { channel: 'email' });
    trackFirstMeaningfulAction('ask_agi_query', { question: 'What is Nifty doing?' });

    const summary = getFunnelSummary();
    assert.equal(summary.counts.unlock_screen, 1);
    assert.equal(summary.counts.signup_started, 1);
    assert.equal(summary.counts.signup_completed, 1);
    assert.equal(summary.counts.first_meaningful_action, 1);
    assert.equal(summary.rates.signup_to_activation_pct, 100);
  });

  it('consumes signup intent once', () => {
    markSignupIntent({ channel: 'google', next: '/ask' });
    assert.equal(consumeSignupIntent()?.channel, 'google');
    assert.equal(consumeSignupIntent(), null);
  });

  it('fires first meaningful action only once', () => {
    trackFirstMeaningfulAction('ask_agi_query');
    trackFirstMeaningfulAction('company_analysis_opened');
    assert.equal(getFunnelSummary().counts.first_meaningful_action, 1);
  });
});
