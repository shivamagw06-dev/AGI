/**
 * Soft pipeline foundation for CMS → Intelligence ingest.
 * Architecture v1.0.1 LOCKED — maps stages onto existing AGIB layers.
 * research_hub soft-wires RIH after KIP/KC so every article becomes an Intelligence Object.
 */

/** Ordered soft stages. Prerequisites are previous stages in this list. */
export const PIPELINE_STAGES = [
  'queued',
  'wake_engine',
  'kip_ingest', // existing IE /v1/kip/ingest/agi (extract/chunk/embed inside KIP)
  'knowledge_compound', // optional soft KC populate — never blocks terminal success
  'research_hub', // optional soft RIH Intelligence Hub build — never blocks terminal success
  'awaiting_approval', // optional human gate
  'completed',
];

export const PRIORITY = {
  MARKET_ALERT: 1,
  RESEARCH_UPDATE: 2,
  DEFAULT: 3,
  ARCHIVE: 4,
};

export function resolveIngestPriority(input = {}) {
  if (Number.isFinite(Number(input.priority))) {
    const p = Math.max(1, Math.min(4, Math.round(Number(input.priority))));
    return p;
  }
  const section = String(input.section || input.research_type || '').toLowerCase();
  const destination = String(input.destination || input.cms_status || '').toLowerCase();
  const tags = Array.isArray(input.themes)
    ? input.themes.join(' ').toLowerCase()
    : String(input.tags || '').toLowerCase();
  const blob = `${section} ${destination} ${tags}`;
  if (/market.?alert|breaking|urgent|flash/.test(blob)) return PRIORITY.MARKET_ALERT;
  if (/research|outlook|committee|ic |dossier|filing/.test(blob)) return PRIORITY.RESEARCH_UPDATE;
  if (/archive|legacy|historical/.test(blob)) return PRIORITY.ARCHIVE;
  return PRIORITY.DEFAULT;
}

export function stageIdempotencyKey({ jobId, stage, contentHash, embeddingVersion }) {
  return `${jobId}:${stage}:${contentHash || 'na'}:${embeddingVersion || 'default'}`;
}

export function appendStageTrace(trace = [], { stage, status, at = new Date().toISOString(), meta = {} }) {
  const next = Array.isArray(trace) ? [...trace] : [];
  next.push({ stage, status, at, ...meta });
  return next.slice(-40);
}

export function pipelineBlueprint() {
  return {
    architecture_status: 'v1.0.1 LOCKED',
    note: 'Stages soft-wire existing AGIB layers (KIP/KC/RIH). research_hub never blocks ingest success.',
    stages: PIPELINE_STAGES.map((stage, idx) => ({
      stage,
      order: idx,
      prerequisites: idx === 0 ? [] : [PIPELINE_STAGES[idx - 1]],
      maps_to:
        stage === 'kip_ingest'
          ? 'IE KIP /v1/kip/ingest/agi'
          : stage === 'knowledge_compound'
            ? 'IE KC /v1/kc/populate (soft, optional)'
            : stage === 'research_hub'
              ? 'IE RIH /v1/research/hub/build (soft, optional)'
            : stage === 'wake_engine'
              ? 'IE /v1/health'
              : 'Node CMS ingest worker',
    })),
    longer_term:
      'CMS articles become Research Intelligence Hubs; extraction→chunk→embed remain inside KIP/KC soft layers.',
  };
}
