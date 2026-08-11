import { loadLiveAlphaUniverse } from './liveAlphaRuntime.js';
import { getLiveAlphaWorkspace } from './liveAlphaWorkspace.js';
import { buildConfluenceQueue } from './researchConfluence.js';
import { getResearchEvidence } from './researchEvidenceCollector.js';
import { completeDueConfluenceOutcomes, saveConfluenceEvents, saveEvidenceConvictionRanking } from './confluenceValidationStore.js';
import { syncResearchMemory } from './researchMemoryStore.js';
import { settleDueForecasts, syncProbabilisticForecasts } from './probabilisticForecastStore.js';
import { syncForecastCrossSections } from './forecastV2Store.js';
import { scopeQueueToLiveUniverse } from './confluenceCandidateScope.js';
import { buildEvidenceConfirmedConvictionRanking } from './evidenceConfirmedConviction.js';

let timer = null;
let state = { enabled: false, status: 'disabled', last_run: null, last_capture: null, last_completion: null, last_error: null };

export async function runConfluenceValidationCycle() {
  if (state.status === 'running') return state;
  state = { ...state, status: 'running', last_error: null };
  try {
    const [workspace, universe] = await Promise.all([getLiveAlphaWorkspace(), loadLiveAlphaUniverse()]);
    const research = await getResearchEvidence({ workspace, limit: 25 });
    const queue = scopeQueueToLiveUniverse(
      buildConfluenceQueue({ workspace, research: research.evidence, limit: 200 }),
      universe,
    );
    const conviction = buildEvidenceConfirmedConvictionRanking(queue, { limit: 200 });
    // A newly deployed app may briefly run before its database migration is
    // applied. Keep validation, memory and forecast maintenance alive while
    // surfacing the conviction persistence error in scheduler health.
    const convictionSave = await saveEvidenceConvictionRanking(conviction).catch((error) => ({
      status: error.status === 404 ? 'database_setup_required' : 'degraded',
      error: error.message,
      rankings: 0,
    }));
    const capture = await saveConfluenceEvents(queue, universe);
    const completion = await completeDueConfluenceOutcomes();
    const memory = await syncResearchMemory();
    const forecasts = await syncProbabilisticForecasts();
    const forecastOutcomes = await settleDueForecasts();
    const crossSections = await syncForecastCrossSections();
    state = { ...state, status: 'idle', last_run: new Date().toISOString(), last_conviction: convictionSave, last_capture: capture, last_completion: completion, last_memory_sync: memory, last_forecast_sync: forecasts, last_forecast_completion: forecastOutcomes, last_cross_section_sync: crossSections };
  } catch (error) {
    state = { ...state, status: error.status === 404 ? 'database_setup_required' : 'degraded', last_run: new Date().toISOString(), last_error: error.message };
  }
  return state;
}

export function startConfluenceValidationScheduler() {
  const enabled = String(process.env.CONFLUENCE_VALIDATION_ENABLED ?? process.env.LIVE_ALPHA_SHADOW_ENABLED ?? '').toLowerCase() === 'true';
  if (!enabled || timer) { state.enabled = enabled; return state; }
  state = { ...state, enabled: true, status: 'idle' };
  const tick = () => runConfluenceValidationCycle().catch((error) => { state = { ...state, status: 'degraded', last_error: error.message }; });
  timer = setInterval(tick, 5 * 60_000); timer.unref?.(); tick();
  return state;
}

export function getConfluenceValidationStatus() { return { ...state, research_only: true, execution_enabled: false }; }
