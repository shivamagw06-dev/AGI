/**
 * Degraded Knowledge Operations Center payload when the intelligence engine
 * is unreachable. Lets the admin UI open instead of spinning until timeout.
 */

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

export function buildKocDegradedHealth(detail = 'Intelligence engine unavailable') {
  return {
    ok: false,
    degraded: true,
    enabled: true,
    workstream_id: 'KOC-01',
    product: 'Knowledge Operations Center',
    platform: 'AGI V1.2',
    version: 'koc-01-v1.2.0-degraded',
    admin_only: true,
    error: detail,
    hint: 'agib-intelligence-engine is not responding. Redeploy or check Render logs; Retry after the engine is healthy.',
    generated_at: nowIso(),
  };
}

export function buildKocDegradedOverview({
  scope = 'TOP20',
  detail = 'Intelligence engine unavailable',
} = {}) {
  const health = buildKocDegradedHealth(detail);
  return {
    ...health,
    ok: true,
    endpoint: 'overview',
    scope: String(scope || 'TOP20').toUpperCase(),
    mission: 'Monitor, Validate, Learn and Improve Institutional Knowledge',
    system_health: {
      ok: false,
      degraded: true,
      bar: {
        cgl: { status: 'Down' },
        kil: { status: 'Down' },
        icf: { status: 'Down' },
        scheduler: { status: 'Unknown' },
        collector_health_pct: null,
        knowledge_latency_minutes: null,
        repair_queue: null,
        auto_repair: 'Paused',
        koc: { status: 'Degraded' },
      },
      detail,
    },
    kpis: {
      companies_covered: null,
      companies_scoped: null,
      institutional_coverage_complete: null,
      claim_safe: null,
      research_ready: null,
      knowledge_ready: null,
      knowledge_confidence: null,
      evidence_objects: null,
      documents_collected_today: null,
      documents_processed_today: null,
      claims_extracted_today: null,
      knowledge_snapshots: null,
      company_memory_updates: null,
      knowledge_graph_updates: null,
      research_refreshes: null,
      research_invalidations: null,
      collector_success_pct: null,
      cgl_status: 'Down',
      kil_status: 'Down',
      icf_status: 'Down',
      koc_status: 'Degraded',
      scheduler_status: 'Unknown',
      repair_queue: null,
    },
    missing_inbox: {
      title: 'Missing Knowledge Inbox',
      workflow: 'Engine offline — inbox unavailable',
      count: 0,
      by_priority: { Critical: 0, High: 0, Medium: 0, Low: 0 },
      items: [],
    },
    gap_ai: { ok: false, items: [], degraded: true },
    ingestion_timeline: [],
    daily_summary: {},
    coverage_table: [],
    knowledge_queue: { stages: {}, boards: [], items: [] },
    queue_stages: [],
    collector_health: [],
    coverage_heatmap: {},
    knowledge_versions: [],
    upload_pipeline: [],
    actions: [],
    degraded: true,
    engine_error: detail,
  };
}

export function buildKocDegradedAudit({ limit = 25, detail = 'Intelligence engine unavailable' } = {}) {
  return {
    ok: false,
    degraded: true,
    limit,
    events: [],
    error: detail,
    generated_at: nowIso(),
  };
}
