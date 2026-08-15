import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

export const LEARNING_PIPELINE_VERSION = 'universal-learning-v1';
export const LEARNING_STAGES = Object.freeze([
  'classification',
  'facts_claims',
  'industry_economics',
  'relationships',
  'causal_intelligence',
  'financial_impact',
  'thesis_intelligence',
  'temporal_conflicts',
  'validation',
]);

export function learningModelRoles(env = process.env) {
  return {
    provider: String(env.AGI_REASONING_PROVIDER || 'openai').trim(),
    extraction_model: String(env.AGI_LEARNING_EXTRACTION_MODEL || 'gpt-5.6-luna').trim(),
    reasoning_model: String(env.AGI_LEARNING_REASONING_MODEL || 'gpt-5.6-terra').trim(),
    critic_model: String(env.AGI_LEARNING_CRITIC_MODEL || env.AGI_LEARNING_REASONING_MODEL || 'gpt-5.6-terra').trim(),
  };
}

export function learningEnabled(env = process.env) {
  return /^(1|true|yes|on)$/i.test(String(env.AGI_INTELLIGENCE_LEARNING_ENABLED || 'false'));
}

export async function enqueueIntelligenceLearning(documentId, { priority = 5 } = {}) {
  if (!documentId) return { ok: false, skipped: true, reason: 'document_id_required' };
  const admin = createSupabaseAdmin();
  if (!admin) return { ok: false, skipped: true, reason: 'supabase_admin_unavailable' };
  const row = {
    document_id: documentId,
    pipeline_version: LEARNING_PIPELINE_VERSION,
    priority: Math.max(1, Math.min(9, Number(priority) || 5)),
    model_roles: learningModelRoles(),
    updated_at: new Date().toISOString(),
  };
  const { data, error } = await admin
    .from('intelligence_learning_jobs')
    .upsert(row, { onConflict: 'document_id,pipeline_version', ignoreDuplicates: true })
    .select('id,status,current_stage')
    .maybeSingle();
  if (error) {
    const migrationMissing = /intelligence_learning_jobs|schema cache|does not exist/i.test(error.message || '');
    return { ok: false, skipped: migrationMissing, reason: migrationMissing ? 'migration_required' : 'enqueue_failed', error: error.message };
  }
  return { ok: true, job: data, enabled: learningEnabled(), model_roles: row.model_roles };
}
