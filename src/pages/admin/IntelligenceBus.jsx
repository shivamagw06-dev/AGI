import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Bus,
  GitBranch,
  RefreshCw,
  Radio,
} from 'lucide-react';
import {
  getIbDashboard,
  getIbDeadLetter,
  getIbHealth,
  getIbMetrics,
  getIbSchema,
  getIbTraces,
  publishIbEvent,
  replayIbEvents,
  runIbDemoChain,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

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
  'Live Event Stream',
  'Publishers',
  'Subscribers',
  'Routing',
  'Replay',
  'Dead Letter Queue',
  'Schema Registry',
  'Delivery Metrics',
  'Latency',
  'Retries',
  'Correlation Explorer',
  'Execution Timeline',
  'Cache Invalidations',
  'Consumer Health',
];

export default function IntelligenceBus() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [schemas, setSchemas] = useState([]);
  const [dlq, setDlq] = useState([]);
  const [trace, setTrace] = useState(null);
  const [demo, setDemo] = useState(null);
  const [module, setModule] = useState(MODULES[0]);
  const [eventType, setEventType] = useState('CompanyUpdated');
  const [symbol, setSymbol] = useState('INFY');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, m, s, dead] = await Promise.all([
        getIbHealth(),
        getIbDashboard(),
        getIbMetrics(),
        getIbSchema(),
        getIbDeadLetter(20),
      ]);
      setHealth(h);
      setDashboard(d);
      setMetrics(m?.metrics || d?.metrics || {});
      setSchemas(s?.schemas || []);
      setDlq(dead?.dead_letters || []);
    } catch (err) {
      setError(err?.message || 'Failed to load Intelligence Bus console');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onPublish = async (e) => {
    e?.preventDefault?.();
    setBusy('publish');
    setError('');
    try {
      await publishIbEvent({
        event_type: eventType,
        producer: 'admin',
        aggregate_type: 'company',
        aggregate_id: symbol.trim().toUpperCase() || 'INFY',
        payload: {
          company_symbol: symbol.trim().toUpperCase() || 'INFY',
          scopes: ['cae', 'company'],
          evidence_id: `ev_${(symbol || 'infy').toLowerCase()}`,
          event_title: `${symbol} admin publish`,
          url: `https://example.com/${(symbol || 'infy').toLowerCase()}`,
        },
        priority: 'high',
      });
      await load();
    } catch (err) {
      setError(err?.message || 'Publish failed');
    } finally {
      setBusy('');
    }
  };

  const onDemo = async () => {
    setBusy('demo');
    setError('');
    try {
      const result = await runIbDemoChain(symbol.trim().toUpperCase() || 'INFY');
      setDemo(result);
      if (result?.correlation_id) {
        const t = await getIbTraces({ correlation_id: result.correlation_id });
        setTrace(t);
      }
      await load();
    } catch (err) {
      setError(err?.message || 'Demo chain failed');
    } finally {
      setBusy('');
    }
  };

  const onReplay = async () => {
    setBusy('replay');
    setError('');
    try {
      await replayIbEvents({
        company_symbol: symbol.trim().toUpperCase() || 'INFY',
        limit: 20,
      });
      await load();
    } catch (err) {
      setError(err?.message || 'Replay failed');
    } finally {
      setBusy('');
    }
  };

  const m = metrics || dashboard?.metrics || health?.metrics || {};
  const live = dashboard?.live_events || [];
  const subs = dashboard?.subscriptions || [];
  const invalidations = dashboard?.cache_invalidations || [];
  const chain = trace?.chain || demo?.trace?.chain || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-500 font-semibold">IB v1.0</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Intelligence Bus</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Event-driven orchestration backbone — publish, route, deliver, replay, and invalidate caches without coupling engines.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={onDemo} disabled={busy === 'demo'}>
            <GitBranch className="w-4 h-4 mr-2" />
            Demo chain
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
        <Stat label="Published" value={m.published ?? '—'} />
        <Stat label="Delivered" value={m.delivered ?? '—'} hint={`Retries ${m.retries ?? 0}`} />
        <Stat label="Dead letters" value={m.dead_lettered ?? '—'} hint={`Failed ${m.failed ?? 0}`} />
        <Stat
          label="Publish latency"
          value={`${m.avg_publish_latency_ms ?? '—'} ms`}
          hint={`Cache invalidations ${m.cache_invalidations ?? 0}`}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {MODULES.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setModule(name)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              module === name
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Radio className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-900">Publish / Replay</h2>
            </div>
            <form className="flex flex-wrap gap-2" onSubmit={onPublish}>
              <input
                value={eventType}
                onChange={(e) => setEventType(e.target.value)}
                className="flex-1 min-w-[180px] rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Event type"
              />
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-28 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Symbol"
              />
              <Button type="submit" disabled={busy === 'publish'}>
                <Bus className="w-4 h-4 mr-2" />
                Publish
              </Button>
              <Button type="button" variant="outline" onClick={onReplay} disabled={busy === 'replay'}>
                Replay
              </Button>
            </form>
            <p className="text-xs text-slate-500 mt-3">Active module: {module}</p>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Live Event Stream</h2>
            <div className="space-y-2 max-h-80 overflow-auto">
              {live.length === 0 ? (
                <p className="text-sm text-slate-500">No events yet — publish or run the demo chain.</p>
              ) : (
                live.map((evt) => (
                  <div key={evt.event_id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                    <div className="flex flex-wrap justify-between gap-2">
                      <span className="font-medium text-slate-900">{evt.event_type}</span>
                      <span className="text-xs text-slate-500">{evt.producer}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {evt.aggregate_id} · {evt.status} · {evt.correlation_id}
                    </p>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Correlation / Timeline</h2>
            {chain.length === 0 ? (
              <p className="text-sm text-slate-500">Run demo chain to visualise an execution path.</p>
            ) : (
              <ol className="space-y-2">
                {chain.map((node, idx) => (
                  <li key={node.event_id} className="rounded-lg border border-slate-100 px-3 py-2 text-sm">
                    <span className="text-xs text-slate-400 mr-2">{idx + 1}.</span>
                    <span className="font-medium">{node.event_type}</span>
                    <span className="text-slate-500"> ← {node.producer}</span>
                    <p className="text-xs text-slate-400 mt-1">
                      subscribers: {(node.subscribers || []).join(', ') || '—'}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>

        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Subscribers</h2>
            <div className="space-y-2 text-sm">
              {subs.map((s) => (
                <div key={s.subscription_id} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="font-medium">{s.subscriber}</p>
                  <p className="text-xs text-slate-500">
                    {(s.event_types || []).slice(0, 3).join(', ') || (s.categories || []).join(', ') || 'all'}
                    {(s.event_types || []).length > 3 ? '…' : ''}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Cache Invalidations</h2>
            <div className="space-y-2 text-sm max-h-48 overflow-auto">
              {invalidations.length === 0 ? (
                <p className="text-slate-500">None yet</p>
              ) : (
                invalidations.map((row, i) => (
                  <div key={`${row.event_id}-${i}`} className="rounded-lg bg-slate-50 px-3 py-2">
                    <p className="font-medium">{row.event_type}</p>
                    <p className="text-xs text-slate-500">{(row.scopes || []).join(', ')}</p>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Dead Letter Queue</h2>
            <div className="space-y-2 text-sm max-h-40 overflow-auto">
              {dlq.length === 0 ? (
                <p className="text-slate-500">Empty</p>
              ) : (
                dlq.map((d) => (
                  <div key={d.dlq_id} className="rounded-lg bg-red-50 px-3 py-2 text-red-800">
                    <p className="font-medium">{d.subscriber}</p>
                    <p className="text-xs">{d.error}</p>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Schema Registry</h2>
            <p className="text-sm text-slate-600">{schemas.length} schemas</p>
            <p className="text-xs text-slate-500 mt-1">
              Status: {health?.status || '—'} · {health?.architecture_status || ''}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
