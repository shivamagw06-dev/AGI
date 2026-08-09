import { loadLiveAlphaUniverse } from './liveAlphaRuntime.js';
import { getLiveAlphaWorkspace } from './liveAlphaWorkspace.js';
import { buildConfluenceQueue } from './researchConfluence.js';
import { getResearchEvidence } from './researchEvidenceCollector.js';
import { completeDueConfluenceOutcomes, saveConfluenceEvents } from './confluenceValidationStore.js';

let timer = null;
let state = { enabled: false, status: 'disabled', last_run: null, last_capture: null, last_completion: null, last_error: null };

export async function runConfluenceValidationCycle() {
  if (state.status === 'running') return state;
  state = { ...state, status: 'running', last_error: null };
  try {
    const [workspace, universe] = await Promise.all([getLiveAlphaWorkspace(), loadLiveAlphaUniverse()]);
    const research = await getResearchEvidence({ workspace, limit: 25 });
    const queue = buildConfluenceQueue({ workspace, research: research.evidence, limit: 25 });
    const capture = await saveConfluenceEvents(queue, universe);
    const completion = await completeDueConfluenceOutcomes();
    state = { ...state, status: 'idle', last_run: new Date().toISOString(), last_capture: capture, last_completion: completion };
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
