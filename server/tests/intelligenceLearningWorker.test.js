import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { validateLearningPayload } from '../services/intelligenceLearningWorker.js';

const valid = {
  industries: ['telecom'], entities: [], facts: [], claims: [], kpis: [], relationships: [],
  causal_chains: [{ trigger: 'Tariff increase', nodes: ['Tariff', 'ARPU'], conditions: ['Churn controlled'], counter_effects: ['Churn rises'] }],
  financial_impacts: [{ statement_type: 'income_statement', metric_key: 'revenue', quantified_value: null }],
  theses: [], monitoring_indicators: [], evidence_quotes: ['Airtel increased prepaid tariffs.'],
};

describe('intelligenceLearningWorker validation', () => {
  it('accepts grounded, two-sided causal learning', () => {
    const result = validateLearningPayload(valid, 'Airtel increased prepaid tariffs. Churn remains a risk.');
    assert.equal(result.valid, true);
  });

  it('quarantines absent evidence and one-sided causality', () => {
    const result = validateLearningPayload({ ...valid, evidence_quotes: ['Not in source'], causal_chains: [{ trigger: 'Tariff', nodes: ['A', 'B'], conditions: [], counter_effects: [] }] }, 'Airtel increased prepaid tariffs.');
    assert.equal(result.valid, false);
    assert.ok(result.errors.includes('evidence_quote_not_in_source'));
    assert.ok(result.errors.includes('causal_counter_effect_required'));
  });

  it('rejects quantified impacts without a deterministic method', () => {
    const result = validateLearningPayload({ ...valid, financial_impacts: [{ statement_type: 'cash_flow', metric_key: 'fcf', quantified_value: 10 }] }, 'Airtel increased prepaid tariffs.');
    assert.equal(result.valid, false);
    assert.ok(result.errors.includes('quantified_impact_requires_method'));
  });
});
