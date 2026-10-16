import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Network,
  RefreshCw,
  Search,
  Zap,
} from 'lucide-react';
import {
  consultMee,
  createMeeEvent,
  getMeeDashboard,
  getMeeHealth,
  getMeeImpact,
  getMeeSimilar,
  runMeeCycle,
  searchMee,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function pct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return n > 1 ? `${Math.round(n)}%` : `${Math.round(n * 100)}%`;
}

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

const MODULES = [
  'Live Event Feed',
  'Event Registry',
  'Company Timelines',
  'Sector Timelines',
  'Theme Timelines',
  'Impact Explorer',
  'Propagation Monitor',
  'Event Relationships',
  'Severity Dashboard',
  'Historical Event Search',
  'Duplicate Detection',
  'Event Health',
  'Processing Queue',
];

export default function Events() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [query, setQuery] = useState('INFY buyback');
  const [consult, setConsult] = useState(null);
  const [hits, setHits] = useState([]);
  const [impact, setImpact] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [module, setModule] = useState(MODULES[0]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d] = await Promise.all([getMeeHealth(), getMeeDashboard()]);
      setHealth(h);
      setDashboard(d);
    } catch (err) {
      setError(err?.message || 'Failed to load Events console');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCycle = async () => {
    setBusy('cycle');
    setError('');
    try {
      await runMeeCycle(30);
      await load();
    } catch (err) {
      setError(err?.message || 'Detection cycle failed');
    } finally {
      setBusy('');
    }
  };

  const onSearch = async (e) => {
    e?.preventDefault?.();
    setBusy('search');
    setError('');
    try {
      const [s, c] = await Promise.all([
        searchMee(query.trim() || 'INFY'),
        consultMee(query.trim() || 'INFY'),
      ]);
      setHits(s?.hits || []);
      setConsult(c);
      const first = c?.recent_events?.[0] || s?.hits?.[0];
      const eid = first?.event_id || first?.id;
      if (eid) {
        const [imp, sim] = await Promise.all([
          getMeeImpact(eid).catch(() => null),
          getMeeSimilar(eid).catch(() => ({ similar: [] })),
        ]);
        setImpact(imp);
        setSimilar(sim?.similar || []);
      }
    } catch (err) {
      setError(err?.message || 'Search failed');
    } finally {
      setBusy('');
    }
  };

  const onSeed = async () => {
    setBusy('seed');
    try {
      await createMeeEvent({
        event_type: 'repo rate cut',
        title: 'RBI repo rate cut — sample event',
        summary: 'Central bank cut the repo rate; impact propagates through banking and housing.',
        sector_ids: ['banking'],
        confidence: 0.85,
        evidence_ids: ['ev_admin_seed'],
        evidence_links: [{ evidence_id: 'ev_admin_seed', claim_text: 'Repo rate cut', confidence: 0.85 }],
        origin: 'user',
        verify: true,
      });
      await load();
    } catch (err) {
      setError(err?.message || 'Seed failed');
    } finally {
      setBusy('');
    }
  };

  const metrics = dashboard?.metrics || health?.metrics || {};
  const feed = dashboard?.live_feed || [];
  const severity = dashboard?.severity_dashboard || {};
  const queue = dashboard?.queue || [];
  const duplicates = dashboard?.duplicates || [];
  const propagations = dashboard?.propagations || [];
  const eventHealth = dashboard?.event_health || health?.event_health || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-500 font-semibold">MEE v1.0</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Market Events</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Canonical event backbone after FLE — detect, classify, verify, version, propagate and preserve every meaningful market change.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={onSeed} disabled={busy === 'seed'}>
            Seed sample
          </Button>
          <Button onClick={onCycle} disabled={busy === 'cycle'}>
            <Zap className="w-4 h-4 mr-2" />
            Run cycle
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm flex gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Events detected" value={metrics.events_detected ?? eventHealth.events_total ?? '—'} />
        <Stat label="Verified" value={metrics.events_verified ?? eventHealth.verified ?? '—'} />
        <Stat label="Queue depth" value={metrics.queue_depth ?? queue.length ?? '—'} />
        <Stat
          label="Duplicate rate"
          value={pct(metrics.duplicate_rate)}
          hint={`Timeline ${metrics.timeline_entries ?? 0} · Relationships ${metrics.relationships ?? 0}`}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {MODULES.map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setModule(m)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              module === m
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Search className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-900">Historical Event Search</h2>
            </div>
            <form className="flex gap-2" onSubmit={onSearch}>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Company, sector, policy, commodity…"
              />
              <Button type="submit" disabled={busy === 'search'}>
                Search
              </Button>
            </form>
            {consult ? (
              <div className="mt-4 space-y-2 text-sm">
                <p className="text-slate-700">
                  Policy: <span className="font-medium">{consult.answer_policy}</span>
                </p>
                <p className="text-xs text-slate-500">
                  Recent {(consult.recent_events || []).length} · Affected companies{' '}
                  {(consult.affected_companies || []).join(', ') || '—'}
                </p>
                <ul className="space-y-2">
                  {(consult.recent_events || []).slice(0, 6).map((ev) => (
                    <li key={ev.event_id} className="border-b border-slate-100 pb-2">
                      <p className="font-medium text-slate-800">
                        {ev.event_type} · {ev.title}
                      </p>
                      <p className="text-xs text-slate-500">
                        {ev.severity} · {ev.status} · conf {pct(ev.confidence)}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-slate-500 mt-4">Search or run a detection cycle to populate events.</p>
            )}
            {hits.length ? (
              <div className="mt-4">
                <p className="text-xs uppercase text-slate-400 mb-2">Hits</p>
                <ul className="space-y-1 text-sm">
                  {hits.slice(0, 8).map((h) => (
                    <li key={h.id} className="text-slate-700">
                      {h.label} · {h.severity}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          {(module === 'Live Event Feed' || module === 'Event Registry') && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Live Event Feed</h2>
              <ul className="space-y-2 text-sm">
                {feed.slice(0, 12).map((ev) => (
                  <li key={ev.event_id} className="border-b border-slate-100 pb-2">
                    <p className="font-medium text-slate-800">
                      {ev.event_type} · {ev.title}
                    </p>
                    <p className="text-xs text-slate-500">
                      {ev.category} · {ev.severity} · {ev.status} · sources {ev.source_count}
                    </p>
                  </li>
                ))}
                {!feed.length ? <li className="text-slate-500">No events yet.</li> : null}
              </ul>
            </section>
          )}

          {(module === 'Impact Explorer' || module === 'Severity Dashboard') && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Network className="w-4 h-4" />
                {module}
              </h2>
              {module === 'Severity Dashboard' ? (
                <div className="grid grid-cols-5 gap-2 text-center text-sm">
                  {Object.entries(severity).map(([k, v]) => (
                    <div key={k} className="rounded-lg bg-slate-50 p-3">
                      <p className="text-xs text-slate-400">{k}</p>
                      <p className="text-xl font-semibold text-slate-900">{v}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm space-y-2">
                  {impact ? (
                    <>
                      <p className="text-slate-700">
                        Chain: {(impact.chain || []).join(' → ') || '—'}
                      </p>
                      <p className="text-xs text-slate-500">
                        Direct {(impact.direct || []).length} · 2nd {(impact.second_order || []).length} · 3rd{' '}
                        {(impact.third_order || []).length}
                      </p>
                      <ul className="space-y-1">
                        {(impact.first_order || []).slice(0, 8).map((n, i) => (
                          <li key={`${n.entity_id}-${i}`} className="text-slate-600">
                            L{n.order} {n.entity_type}:{n.entity_id} — {n.description}
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <p className="text-slate-500">Search an event to load its impact graph.</p>
                  )}
                  {similar.length ? (
                    <div className="mt-3">
                      <p className="text-xs uppercase text-slate-400 mb-1">Similar events</p>
                      <ul className="space-y-1">
                        {similar.slice(0, 5).map((s) => (
                          <li key={s.event_id} className="text-slate-600">
                            {s.event_type} · {s.title} · score {s.score}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              )}
            </section>
          )}
        </div>

        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Event Health / Queue</h2>
            <div className="text-sm space-y-1 text-slate-700">
              <p>Total: {eventHealth.events_total ?? '—'}</p>
              <p>Verified: {eventHealth.verified ?? '—'}</p>
              <p>Pending: {eventHealth.pending ?? '—'}</p>
              <p>Duplicates: {eventHealth.duplicates ?? duplicates.length}</p>
              <p>Avg confidence: {pct(eventHealth.avg_confidence)}</p>
            </div>
            <p className="text-xs uppercase text-slate-400 mt-4 mb-2">Queue</p>
            <ul className="text-xs text-slate-600 space-y-1 max-h-32 overflow-auto">
              {queue.slice(0, 10).map((id) => (
                <li key={id}>{id}</li>
              ))}
              {!queue.length ? <li>Empty</li> : null}
            </ul>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Propagation Monitor</h2>
            <ul className="space-y-2 text-sm max-h-64 overflow-auto">
              {propagations.slice(0, 10).map((p) => (
                <li key={p.propagation_id} className="border-b border-slate-100 pb-2">
                  <p className="font-medium text-slate-800">{p.status}</p>
                  <p className="text-xs text-slate-500">
                    {(p.targets || []).join(', ')} · {p.idempotency_key}
                  </p>
                </li>
              ))}
              {!propagations.length ? <li className="text-slate-500">No propagations yet.</li> : null}
            </ul>
            <p className="text-[11px] text-slate-400 mt-3">
              Health: {health?.status || '—'} · {health?.position || ''}
            </p>
          </section>

          {module === 'Duplicate Detection' && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Duplicates</h2>
              <ul className="text-sm space-y-2">
                {duplicates.slice(0, 8).map((d) => (
                  <li key={d.event_id} className="text-slate-600">
                    {d.title} → {d.duplicate_of}
                  </li>
                ))}
                {!duplicates.length ? <li className="text-slate-500">None detected.</li> : null}
              </ul>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
