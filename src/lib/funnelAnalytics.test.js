import { describe, expect, it, beforeEach } from 'vitest';
import {
  getFunnelSummary,
  markSignupIntent,
  consumeSignupIntent,
  trackFunnelEvent,
  trackFirstMeaningfulAction,
} from '@/lib/funnelAnalytics';

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
    expect(summary.counts.unlock_screen).toBe(1);
    expect(summary.counts.signup_started).toBe(1);
    expect(summary.counts.signup_completed).toBe(1);
    expect(summary.counts.first_meaningful_action).toBe(1);
    expect(summary.rates.signup_to_activation_pct).toBe(100);
  });

  it('consumes signup intent once', () => {
    markSignupIntent({ channel: 'google', next: '/ask' });
    expect(consumeSignupIntent()?.channel).toBe('google');
    expect(consumeSignupIntent()).toBeNull();
  });

  it('fires first meaningful action only once', () => {
    trackFirstMeaningfulAction('ask_agi_query');
    trackFirstMeaningfulAction('company_analysis_opened');
    expect(getFunnelSummary().counts.first_meaningful_action).toBe(1);
  });
});
