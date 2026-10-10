import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Map as MapIcon,
  RefreshCw,
  Shield,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import {
  ANALYST_ROLES,
  DATA_SOURCES,
  LAYERS,
  PIPELINE_PATH,
  ZONES,
  findLayer,
  layersByZone,
} from '@/lib/intelligenceMapCatalog';
import { getIntelligenceMapSnapshot } from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';
import '@/office/theme.css';
import './IntelligenceMap.css';

function classifyProbe(probe) {
  if (!probe) return { status: 'waiting', label: 'Waiting' };
  if (probe.ok) return { status: 'active', label: 'Active' };
  const code = Number(probe.status || 0);
  if (code === 503 || code === 404 || code === 502) {
    return { status: 'unreachable', label: code ? `${code} Route` : 'Unreachable' };
  }
  if (code >= 400 || probe.error) return { status: 'error', label: 'Error' };
  return { status: 'idle', label: 'Idle' };
}

function toneForAccent(accent) {
  if (accent === 'gold') return 'gold';
  if (accent === 'purple') return 'purple';
  if (accent === 'red') return 'red';
  if (accent === 'green') return 'green';
  return 'blue';
}

function StatCard({ label, value, hint, tone }) {
  const color =
    tone === 'green'
      ? 'text-emerald-400'
      : tone === 'amber'
        ? 'text-amber-300'
        : tone === 'red'
          ? 'text-rose-400'
          : tone === 'blue'
            ? 'text-sky-300'
            : 'text-white';
  return (
    <div className="imap-stat">
      <p className="text-[11px] uppercase tracking-wide text-[var(--imap-muted)]">{label}</p>
      <p className={`mt-1.5 text-2xl font-semibold tabular-nums ${color}`}>{value}</p>
      {hint ? <p className="mt-1 text-[11px] text-[var(--imap-muted)]">{hint}</p> : null}
    </div>
  );
}

function LayerCard({ layer, runtime, selected, onSelect, onHover }) {
  const status = runtime?.status || 'waiting';
  const label = runtime?.label || 'Waiting';
  return (
    <button
      type="button"
      className="imap-layer w-full text-left"
      data-status={status}
      data-accent={layer.accent}
      onClick={() => onSelect(layer.id)}
      onMouseEnter={() => onHover(layer.id)}
      onMouseLeave={() => onHover(null)}
      aria-pressed={selected}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[10px] font-bold tracking-[0.14em] uppercase text-[var(--imap-muted)]">
            {layer.code}
          </p>
          <p className="mt-0.5 text-sm font-semibold text-white leading-tight">{layer.name}</p>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
            status === 'active'
              ? 'bg-emerald-500/15 text-emerald-300'
              : status === 'running'
                ? 'bg-sky-500/15 text-sky-300'
                : status === 'unreachable' || status === 'error'
                  ? 'bg-rose-500/15 text-rose-300'
                  : status === 'waiting'
                    ? 'bg-amber-500/15 text-amber-200'
                    : 'bg-white/5 text-[var(--imap-muted)]'
          }`}
        >
          {status === 'running' ? <span className="imap-spinner" /> : null}
          {label}
        </span>
      </div>
      <p className="mt-1.5 text-[11px] leading-snug text-[var(--imap-muted)]">{layer.purpose}</p>
      <div className="mt-2 grid grid-cols-3 gap-1.5 text-[10px] text-[var(--imap-muted)]">
        <div>
          <p className="uppercase tracking-wide opacity-70">Latency</p>
          <p className="tabular-nums text-white/90">
            {runtime?.latency_ms != null ? `${runtime.latency_ms} ms` : '—'}
          </p>
        </div>
        <div>
          <p className="uppercase tracking-wide opacity-70">Health</p>
          <p className="tabular-nums text-white/90">
            {status === 'active' ? '100%' : status === 'unreachable' ? '0%' : '—'}
          </p>
        </div>
        <div>
          <p className="uppercase tracking-wide opacity-70">Ver</p>
          <p className="tabular-nums text-white/90">{layer.version}</p>
        </div>
      </div>
      {runtime?.error ? (
        <p className="mt-2 text-[10px] leading-snug text-rose-300/90 line-clamp-2">{runtime.error}</p>
      ) : null}
    </button>
  );
}

function FlowConnector({ tone = 'green', speed = 'normal' }) {
  return (
    <div className="imap-connector" aria-hidden>
      <div className="imap-connector-line" data-tone={tone} data-speed={speed} />
    </div>
  );
}

export default function IntelligenceMap() {
  const [probes, setProbes] = useState({});
  const [desk, setDesk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [hoverId, setHoverId] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [question, setQuestion] = useState('Should I invest in HDFC Bank?');
  const [pathMode, setPathMode] = useState(false);
  const [pathStep, setPathStep] = useState(-1);
  const [activity, setActivity] = useState([]);
  const stageRef = useRef(null);

  const pushActivity = useCallback((message) => {
    setActivity((prev) =>
      [{ id: `${Date.now()}-${Math.random()}`, at: new Date().toISOString(), message }, ...prev].slice(
        0,
        40
      )
    );
  }, []);

  const load = useCallback(async ({ quiet } = {}) => {
    setError('');
    if (!quiet) pushActivity('Loading Intelligence Map snapshot…');
    try {
      // Snapshot reader only — no live catalog probe fan-out.
      const snap = await getIntelligenceMapSnapshot();
      const next = snap?.probes && typeof snap.probes === 'object' ? snap.probes : {};
      setProbes(next);
      setDesk(snap?.mission_control_summary || null);
      setUpdatedAt(
        snap?.snapshot_meta?.persisted_at || snap?.generated_at
          ? new Date(snap?.snapshot_meta?.persisted_at || snap?.generated_at)
          : new Date()
      );
      setLoading(false);

      if (snap?._warming || snap?.status === 'warming') {
        pushActivity(snap?.message || 'Intelligence Map is warming up — worker building first snapshot.');
        return;
      }

      const values = Object.values(next);
      const activeN = values.filter((p) => p?.ok).length;
      const badN = values.length - activeN;
      pushActivity(
        `Snapshot loaded · ${snap?.summary?.headline || `${activeN} active · ${badN} partial/unreachable`}`
      );
    } catch (err) {
      setError(err?.message || 'Failed to load Intelligence Map snapshot');
      setLoading(false);
    }
  }, [pushActivity]);

  useEffect(() => {
    load();
    // Poll cached snapshot only while the page is mounted (was 30s live fan-out).
    const t = window.setInterval(() => load({ quiet: true }), 90_000);
    return () => window.clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (!pathMode) {
      setPathStep(-1);
      return undefined;
    }
    setPathStep(0);
    pushActivity(`Live path started · ${question}`);
    const timer = window.setInterval(() => {
      setPathStep((s) => {
        const next = s + 1;
        if (next >= PIPELINE_PATH.length) {
          window.clearInterval(timer);
          pushActivity('Ask AGI answer published');
          return PIPELINE_PATH.length;
        }
        const layer = findLayer(PIPELINE_PATH[next]);
        pushActivity(`Executing ${layer?.code || PIPELINE_PATH[next]}`);
        return next;
      });
    }, 900);
    return () => window.clearInterval(timer);
  }, [pathMode, question, pushActivity]);

  const runtimeById = useMemo(() => {
    const map = {};
    for (const layer of LAYERS) {
      if (layer.id === 'AskAGI') {
        map[layer.id] = { status: 'active', label: 'Surface', latency_ms: null, error: null, probe: null };
        continue;
      }
      const probe = probes[layer.id];
      const classified = classifyProbe(probe);
      let status = classified.status;
      let label = classified.label;

      if (pathMode) {
        const idx = PIPELINE_PATH.indexOf(layer.id);
        if (idx >= 0) {
          if (pathStep > idx) {
            status = 'active';
            label = 'Complete';
          } else if (pathStep === idx) {
            status = 'running';
            label = 'Running';
          } else {
            status = 'waiting';
            label = 'Queued';
          }
        }
      }

      map[layer.id] = {
        status,
        label:
          status === 'unreachable'
            ? probe?.status
              ? `${probe.status} Unreachable`
              : 'Unreachable'
            : label,
        latency_ms: probe?.latency_ms ?? null,
        error: probe?.error || null,
        probe,
      };
    }
    return map;
  }, [probes, pathMode, pathStep]);

  const stats = useMemo(() => {
    const core = LAYERS.filter((l) => l.zone !== 'validation' && l.id !== 'AskAGI');
    const total = core.length + layersByZone('validation').length;
    let active = 0;
    let waiting = 0;
    let errors = 0;
    let unreachable = 0;
    for (const layer of LAYERS) {
      const s = runtimeById[layer.id]?.status;
      if (s === 'active' || s === 'running') active += 1;
      else if (s === 'waiting' || s === 'idle') waiting += 1;
      else if (s === 'error') errors += 1;
      else if (s === 'unreachable') unreachable += 1;
    }
    const critical = LAYERS.filter((l) => l.critical);
    const criticalOk = critical.filter((l) => {
      const s = runtimeById[l.id]?.status;
      return s === 'active' || s === 'running';
    }).length;
    const e2e = critical.length ? Math.round((criticalOk / critical.length) * 100) : 0;
    return {
      total,
      active,
      waiting,
      errors,
      unreachable,
      e2e,
      criticalHealthy: criticalOk === critical.length,
    };
  }, [runtimeById]);

  const selected = selectedId ? findLayer(selectedId) : null;
  const selectedRuntime = selectedId ? runtimeById[selectedId] : null;
  const hover = hoverId ? findLayer(hoverId) : null;

  const events = desk?.live_event_stream || [];
  const avgLatency = useMemo(() => {
    const vals = Object.values(probes)
      .map((p) => p?.latency_ms)
      .filter((n) => typeof n === 'number');
    if (!vals.length) return null;
    return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
  }, [probes]);

  const overallHealth = stats.e2e;

  return (
    <div className="agi-imap p-4 md:p-6">
      <div className="mx-auto max-w-[1680px] space-y-4">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--imap-gold)]">
                AGIB v3
              </p>
              <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-rose-200">
                Admin Only
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-wider text-[var(--imap-muted)]">
                Snapshot Topology
              </span>
            </div>
            <h1 className="mt-2 flex items-center gap-2 text-2xl md:text-3xl font-semibold tracking-tight">
              <MapIcon className="h-7 w-7 text-sky-300" />
              Institutional Intelligence Map
            </h1>
            <p className="mt-1 text-sm text-[var(--imap-muted)]">
              Brain map of the frozen AGIB pipeline — worker snapshot, polled every 90s. No live probe
              fan-out on open.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 min-w-[280px] text-sm">
            <div className="imap-stat py-2">
              <p className="text-[10px] uppercase text-[var(--imap-muted)]">Environment</p>
              <p className="font-medium text-emerald-300">Production</p>
            </div>
            <div className="imap-stat py-2">
              <p className="text-[10px] uppercase text-[var(--imap-muted)]">Architecture</p>
              <p className="font-medium text-amber-200">Frozen</p>
            </div>
            <div className="imap-stat py-2">
              <p className="text-[10px] uppercase text-[var(--imap-muted)]">Version</p>
              <p className="font-medium">v3.0</p>
            </div>
            <div className="imap-stat py-2">
              <p className="text-[10px] uppercase text-[var(--imap-muted)]">Last Update</p>
              <p className="font-medium tabular-nums">
                {updatedAt ? updatedAt.toLocaleTimeString() : '—'}
              </p>
            </div>
            <div className="imap-stat py-2">
              <p className="text-[10px] uppercase text-[var(--imap-muted)]">Overall Health</p>
              <p className="font-semibold text-emerald-300 tabular-nums">{overallHealth}%</p>
            </div>
            <div className="imap-stat py-2">
              <p className="text-[10px] uppercase text-[var(--imap-muted)]">Avg Latency</p>
              <p className="font-medium tabular-nums">{avgLatency != null ? `${avgLatency} ms` : '—'}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="border-white/15 bg-white/5 text-white hover:bg-white/10"
            onClick={() => load()}
            disabled={loading}
          >
            <RefreshCw className={`mr-2 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Check snapshot
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="border-white/15 bg-white/5 text-white hover:bg-white/10"
            onClick={() => setZoom((z) => Math.min(1.4, Number((z + 0.1).toFixed(2))))}
          >
            <ZoomIn className="mr-2 h-3.5 w-3.5" />
            Zoom
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="border-white/15 bg-white/5 text-white hover:bg-white/10"
            onClick={() => setZoom((z) => Math.max(0.7, Number((z - 0.1).toFixed(2))))}
          >
            <ZoomOut className="mr-2 h-3.5 w-3.5" />
            Out
          </Button>
          <div className="flex flex-1 min-w-[240px] items-center gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-white/30"
              placeholder="Current question"
            />
            <Button
              type="button"
              size="sm"
              className="bg-sky-600 hover:bg-sky-500 text-white"
              onClick={() => setPathMode((v) => !v)}
            >
              {pathMode ? 'Stop Path' : 'Run Path'}
            </Button>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/25 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {stats.errors === 0 && stats.unreachable > 0
              ? 'Core operational · validation routes partial'
              : stats.errors === 0
                ? 'All critical systems operational'
                : 'Attention required'}
          </div>
        </div>

        {error ? (
          <div className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100 flex gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            {error}
          </div>
        ) : null}

        {/* Top stats */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <StatCard label="Total Layers" value={stats.total} hint="Core + supporting + validation" />
          <StatCard label="Running / Active" value={stats.active} hint="Reachable health" tone="green" />
          <StatCard label="Waiting" value={stats.waiting} hint="Idle or queued" tone="amber" />
          <StatCard label="Errors" value={stats.errors} hint="Hard failures" tone={stats.errors ? 'red' : 'green'} />
          <StatCard
            label="Critical Path"
            value={stats.criticalHealthy ? 'Healthy' : 'Degraded'}
            hint="Frozen pipeline"
            tone={stats.criticalHealthy ? 'green' : 'amber'}
          />
          <StatCard label="End-to-End" value={`${stats.e2e}%`} hint="Critical layer coverage" tone="blue" />
        </div>

        {/* Data sources strip */}
        <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-3">
          <div className="flex items-center justify-between gap-3 mb-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-sky-300">
              Data Sources
            </p>
            <div className="imap-flow-rail flex-1 mx-4" data-tone="blue" data-speed="slow" />
            <p className="text-[11px] text-[var(--imap-muted)]">Feeds → Evidence</p>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {DATA_SOURCES.map((s) => (
              <span key={s.id} className="imap-source-chip">
                {s.name}
              </span>
            ))}
          </div>
        </div>

        <div className="grid xl:grid-cols-[1fr_280px] gap-4">
          {/* Main flow map */}
          <div className="imap-map-stage" ref={stageRef}>
            <div className="imap-map-canvas" style={{ transform: `scale(${zoom})` }}>
              <div className="flex items-stretch gap-2">
                {ZONES.map((zone, zoneIdx) => (
                  <div key={zone.id} className="contents">
                    <section className="imap-zone flex-1" data-accent={zone.accent}>
                      <div className="mb-3">
                        <p
                          className={`text-[10px] font-bold uppercase tracking-[0.16em] ${
                            zone.accent === 'gold'
                              ? 'text-amber-300'
                              : zone.accent === 'green'
                                ? 'text-emerald-300'
                                : zone.accent === 'purple'
                                  ? 'text-violet-300'
                                  : 'text-sky-300'
                          }`}
                        >
                          {zone.title}
                        </p>
                        <p className="text-[11px] text-[var(--imap-muted)]">{zone.subtitle}</p>
                        <div
                          className="imap-flow-rail mt-2"
                          data-tone={toneForAccent(zone.accent)}
                          data-speed={pathMode ? 'fast' : 'normal'}
                        />
                      </div>
                      <div className="space-y-2">
                        {layersByZone(zone.id).map((layer) => (
                          <LayerCard
                            key={layer.id}
                            layer={layer}
                            runtime={runtimeById[layer.id]}
                            selected={selectedId === layer.id}
                            onSelect={setSelectedId}
                            onHover={setHoverId}
                          />
                        ))}
                        {zone.id === 'reasoning' ? (
                          <div className="rounded-xl border border-amber-400/20 bg-amber-500/5 p-2.5">
                            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-amber-200/90 mb-2">
                              Analyst Desks
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {ANALYST_ROLES.map((role) => (
                                <span
                                  key={role}
                                  className="rounded-md border border-amber-400/20 bg-black/20 px-2 py-1 text-[10px] text-amber-50/90"
                                >
                                  {role}
                                </span>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    </section>
                    {zoneIdx < ZONES.length - 1 ? (
                      <FlowConnector
                        tone={
                          zoneIdx === 0
                            ? 'blue'
                            : zoneIdx === 1
                              ? 'green'
                              : zoneIdx === 2
                                ? 'gold'
                                : 'purple'
                        }
                        speed={pathMode ? 'fast' : 'normal'}
                      />
                    ) : null}
                  </div>
                ))}
              </div>

              {/* Validation */}
              <div className="imap-validation mt-4">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-rose-300">
                      Quality & Regression
                    </p>
                    <p className="text-[11px] text-[var(--imap-muted)]">
                      Always visible — never remove when routes are unavailable
                    </p>
                  </div>
                  <div className="imap-flow-rail w-40" data-tone="red" data-speed="slow" />
                </div>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-2">
                  {layersByZone('validation').map((layer) => (
                    <LayerCard
                      key={layer.id}
                      layer={layer}
                      runtime={runtimeById[layer.id]}
                      selected={selectedId === layer.id}
                      onSelect={setSelectedId}
                      onHover={setHoverId}
                    />
                  ))}
                </div>
              </div>

              {/* End-to-end path strip */}
              <div className="mt-4 rounded-xl border border-white/8 bg-black/20 p-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--imap-muted)] mb-2">
                  End-to-End Path · {PIPELINE_PATH.length} hops
                </p>
                <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                  {PIPELINE_PATH.map((id, i) => {
                    const layer = findLayer(id);
                    const rt = runtimeById[id];
                    const done = pathMode ? pathStep > i : rt?.status === 'active';
                    const current = pathMode && pathStep === i;
                    return (
                      <span key={id} className="inline-flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => setSelectedId(id)}
                          className={`rounded-md border px-2 py-1 font-medium ${
                            current
                              ? 'border-sky-400/50 bg-sky-500/20 text-sky-100'
                              : done
                                ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100'
                                : 'border-white/10 bg-white/5 text-white/60'
                          }`}
                        >
                          {layer?.code || id}
                        </button>
                        {i < PIPELINE_PATH.length - 1 ? (
                          <span className="text-white/25">→</span>
                        ) : null}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="imap-minimap" aria-hidden>
              <div className="imap-minimap-zones">
                {ZONES.map((z) => (
                  <div
                    key={z.id}
                    style={{
                      background:
                        z.accent === 'gold'
                          ? 'rgba(212,175,55,0.35)'
                          : z.accent === 'green'
                            ? 'rgba(52,211,153,0.3)'
                            : z.accent === 'purple'
                              ? 'rgba(167,139,250,0.3)'
                              : 'rgba(79,140,255,0.3)',
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Right activity */}
          <aside className="space-y-3">
            <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-3">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-emerald-300" />
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-emerald-300">
                  Live Activity
                </p>
              </div>
              <div className="imap-activity">
                {activity.length ? (
                  activity.map((item) => (
                    <div key={item.id} className="imap-activity-item">
                      <p className="text-[10px] text-[var(--imap-muted)] tabular-nums">
                        {new Date(item.at).toLocaleTimeString()}
                      </p>
                      <p className="text-xs text-white/90">{item.message}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-[var(--imap-muted)]">Waiting for topology events…</p>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--imap-muted)] mb-2">
                Hover Preview
              </p>
              {hover ? (
                <div className="space-y-1.5 text-xs">
                  <p className="font-semibold text-white">
                    {hover.code} · {hover.name}
                  </p>
                  <p className="text-[var(--imap-muted)]">{hover.purpose}</p>
                  <p>
                    <span className="text-[var(--imap-muted)]">In:</span> {hover.inputs.join(', ')}
                  </p>
                  <p>
                    <span className="text-[var(--imap-muted)]">Out:</span> {hover.outputs.join(', ')}
                  </p>
                  <p>
                    <span className="text-[var(--imap-muted)]">Next:</span>{' '}
                    {hover.downstream.join(' → ') || '—'}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-[var(--imap-muted)]">Hover any layer for inputs/outputs.</p>
              )}
            </div>

            <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--imap-muted)] mb-2">
                Mission Events
              </p>
              <div className="space-y-2 max-h-48 overflow-auto">
                {(events.length ? events : []).slice(0, 8).map((ev, idx) => (
                  <div key={ev.id || idx} className="text-xs border-l border-white/15 pl-2">
                    <p className="text-white/90">{ev.message || ev.event || ev.title || 'Event'}</p>
                    <p className="text-[10px] text-[var(--imap-muted)]">
                      {ev.at || ev.timestamp || ev.time || ''}
                    </p>
                  </div>
                ))}
                {!events.length ? (
                  <p className="text-xs text-[var(--imap-muted)]">No recent mission-control events.</p>
                ) : null}
              </div>
            </div>
          </aside>
        </div>

        {/* Bottom health panel */}
        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
          <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--imap-muted)]">
              Pipeline Health
            </p>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-[var(--imap-muted)] text-xs">End-to-End</p>
                <p className="text-xl font-semibold text-emerald-300">{stats.e2e}%</p>
              </div>
              <div>
                <p className="text-[var(--imap-muted)] text-xs">Avg Runtime</p>
                <p className="text-xl font-semibold tabular-nums">
                  {avgLatency != null ? `${(avgLatency / 1000).toFixed(2)} s` : '—'}
                </p>
              </div>
              <div>
                <p className="text-[var(--imap-muted)] text-xs">Partial Routes</p>
                <p className="text-xl font-semibold text-amber-200">{stats.unreachable}</p>
              </div>
              <div>
                <p className="text-[var(--imap-muted)] text-xs">Final Confidence</p>
                <p className="text-xl font-semibold">{Math.max(70, stats.e2e - 4)}%</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--imap-muted)]">
              Data Freshness (Top)
            </p>
            <div className="mt-3 space-y-2">
              {['FIL', 'FDI', 'CIG', 'IKG', 'IDE_V2', 'IIS'].map((id) => {
                const rt = runtimeById[id];
                return (
                  <div key={id} className="flex items-center justify-between text-xs">
                    <span className="text-white/85">{findLayer(id)?.code || id}</span>
                    <span
                      className={
                        rt?.status === 'active' ? 'text-emerald-300' : 'text-amber-200'
                      }
                    >
                      {rt?.latency_ms != null ? `${rt.latency_ms} ms · ${rt.label}` : rt?.label || '—'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--imap-muted)]">
              Quick Actions
            </p>
            <div className="mt-3 grid gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="justify-start border-white/15 bg-white/5 text-white hover:bg-white/10"
                onClick={() => load()}
              >
                <Shield className="mr-2 h-3.5 w-3.5" />
                Reload Snapshot
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="justify-start border-white/15 bg-white/5 text-white hover:bg-white/10"
                onClick={() => setPathMode(true)}
              >
                <CircleDashed className="mr-2 h-3.5 w-3.5" />
                Test Layer Connectivity Path
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="justify-start border-white/15 bg-white/5 text-white hover:bg-white/10"
                onClick={() => window.open('/admin/mission-control', '_self')}
              >
                <Activity className="mr-2 h-3.5 w-3.5" />
                Open Mission Control
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--imap-muted)]">
              Graph Summary
            </p>
            <div className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--imap-muted)]">Evidence objects</span>
                <span className="tabular-nums">{desk?.knowledge_growth?.evidence_objects ?? '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--imap-muted)]">KG nodes</span>
                <span className="tabular-nums">{desk?.knowledge_growth?.nodes ?? '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--imap-muted)]">KG edges</span>
                <span className="tabular-nums">{desk?.knowledge_growth?.edges ?? '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--imap-muted)]">Memory objects</span>
                <span className="tabular-nums">{desk?.knowledge_growth?.memory_objects ?? '—'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Diagnostics drawer */}
      {selected ? (
        <div className="imap-drawer" onClick={() => setSelectedId(null)} role="presentation">
          <div
            className="imap-drawer-panel"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label={`${selected.code} institutional diagnostics`}
          >
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--imap-gold)]">
                  Institutional Diagnostics
                </p>
                <h2 className="text-xl font-semibold mt-1">
                  {selected.code} · {selected.name}
                </h2>
                <p className="text-sm text-[var(--imap-muted)] mt-1">{selected.purpose}</p>
              </div>
              <button
                type="button"
                className="rounded-lg border border-white/10 p-2 text-white/70 hover:bg-white/5"
                onClick={() => setSelectedId(null)}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-4">
              <div className="imap-stat">
                <p className="text-[10px] uppercase text-[var(--imap-muted)]">Status</p>
                <p className="font-medium">{selectedRuntime?.label || '—'}</p>
              </div>
              <div className="imap-stat">
                <p className="text-[10px] uppercase text-[var(--imap-muted)]">Latency</p>
                <p className="font-medium tabular-nums">
                  {selectedRuntime?.latency_ms != null ? `${selectedRuntime.latency_ms} ms` : '—'}
                </p>
              </div>
              <div className="imap-stat">
                <p className="text-[10px] uppercase text-[var(--imap-muted)]">Route</p>
                <p className="font-medium text-xs break-all">{selected.route || 'n/a'}</p>
              </div>
              <div className="imap-stat">
                <p className="text-[10px] uppercase text-[var(--imap-muted)]">Version</p>
                <p className="font-medium">{selected.version}</p>
              </div>
            </div>

            <div className="space-y-3 text-sm">
              <section>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--imap-muted)]">
                  Inputs
                </p>
                <ul className="mt-1 list-disc pl-4 text-white/85">
                  {selected.inputs.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </section>
              <section>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--imap-muted)]">
                  Outputs
                </p>
                <ul className="mt-1 list-disc pl-4 text-white/85">
                  {selected.outputs.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </section>
              <section>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--imap-muted)]">
                  Upstream
                </p>
                <p className="mt-1 text-white/85">{selected.upstream.join(' · ') || '—'}</p>
              </section>
              <section>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--imap-muted)]">
                  Downstream
                </p>
                <p className="mt-1 text-white/85">{selected.downstream.join(' · ') || '—'}</p>
              </section>
              {selectedRuntime?.error ? (
                <section className="rounded-xl border border-rose-400/30 bg-rose-500/10 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-rose-200">
                    Last Failure
                  </p>
                  <p className="mt-1 text-rose-100">{selectedRuntime.error}</p>
                </section>
              ) : null}
              <section>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--imap-muted)] mb-1">
                  Latest Probe JSON
                </p>
                <pre className="rounded-xl border border-white/10 bg-black/40 p-3 text-[11px] overflow-auto max-h-64 text-emerald-100/90">
                  {JSON.stringify(selectedRuntime?.probe || { note: 'No probe for this surface' }, null, 2)}
                </pre>
              </section>
              {selected.docs ? (
                <Button
                  type="button"
                  size="sm"
                  className="bg-sky-600 hover:bg-sky-500"
                  onClick={() => window.open(selected.docs, '_self')}
                >
                  Open linked admin surface
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
