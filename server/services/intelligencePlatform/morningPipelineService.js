import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { entityStats, listEntities } from './entityStore.js';
import { relationshipStats } from './relationshipStore.js';
import { timelineStats } from './timelineService.js';
import { generateEntitySummary } from './aiSummaryService.js';
import { bootstrapIntelligencePlatform } from './bootstrap.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LOG_FILE = path.join(__dirname, '../../data/intelligence_platform/morning_pipeline.json');

function readLog() {
  try {
    return JSON.parse(fs.readFileSync(LOG_FILE, 'utf8'));
  } catch {
    return { runs: [], last_refresh: null };
  }
}

function writeLog(data) {
  const dir = path.dirname(LOG_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(LOG_FILE, JSON.stringify(data, null, 2));
}

export function getMorningPipelineStatus() {
  const log = readLog();
  return {
    last_refresh: log.last_refresh,
    last_run: log.runs[0] || null,
    total_runs: log.runs.length,
    next_scheduled: null,
    status: log.last_refresh ? 'ready' : 'pending',
  };
}

export async function runMorningPipeline({ actor = 'system' } = {}) {
  const started = new Date().toISOString();
  const steps = [];

  try {
    steps.push({ step: 'bootstrap_entities', status: 'running' });
    const boot = await bootstrapIntelligencePlatform({ force: false });
    steps[steps.length - 1] = { step: 'bootstrap_entities', status: 'done', detail: boot };

    steps.push({ step: 'refresh_summaries', status: 'running' });
    const { entities } = listEntities({ limit: 20, status: 'published' });
    const firms = entities.filter((e) => e.entity_type === 'pe_firm').slice(0, 5);
    const refreshed = [];
    for (const firm of firms) {
      await generateEntitySummary(firm.id, { force: true });
      refreshed.push(firm.slug);
    }
    steps[steps.length - 1] = { step: 'refresh_summaries', status: 'done', detail: { refreshed } };

    steps.push({ step: 'stats_snapshot', status: 'running' });
    const stats = {
      entities: entityStats(),
      relationships: relationshipStats(),
      timeline: timelineStats(),
    };
    steps[steps.length - 1] = { step: 'stats_snapshot', status: 'done', detail: stats };

    const finished = new Date().toISOString();
    const run = {
      id: `run-${Date.now()}`,
      actor,
      started_at: started,
      finished_at: finished,
      steps,
      success: true,
    };

    const log = readLog();
    log.runs.unshift(run);
    log.runs = log.runs.slice(0, 30);
    log.last_refresh = finished;
    writeLog(log);

    return { success: true, run, last_refresh: finished };
  } catch (error) {
    const finished = new Date().toISOString();
    steps.push({ step: 'error', status: 'failed', detail: error.message });
    const run = { id: `run-${Date.now()}`, actor, started_at: started, finished_at: finished, steps, success: false };
    const log = readLog();
    log.runs.unshift(run);
    writeLog(log);
    return { success: false, run, error: error.message };
  }
}

export function getPipelineLog({ limit = 10 } = {}) {
  const log = readLog();
  return { last_refresh: log.last_refresh, runs: log.runs.slice(0, limit) };
}
