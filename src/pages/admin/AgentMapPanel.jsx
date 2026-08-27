import { useCallback, useEffect, useMemo, useState } from 'react';
import { Bot, RefreshCw, X } from 'lucide-react';
import { getMissionControlAgentMap } from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

const STATUS_STYLES = {
  working: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  soft: 'bg-amber-500/15 text-amber-200 border-amber-500/40',
  off: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  orphan: 'bg-slate-500/20 text-slate-300 border-slate-500/40',
  degraded: 'bg-orange-500/15 text-orange-200 border-orange-500/40',
  unknown: 'bg-white/5 text-[var(--io-muted)] border-[var(--io-border)]',
};

function StatusPill({ status }) {
  const s = String(status || 'unknown').toLowerCase();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${STATUS_STYLES[s] || STATUS_STYLES.unknown}`}
    >
      {s}
    </span>
  );
}

export default function AgentMapPanel({ open, onClose }) {
  const [map, setMap] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(null);

  const load = useCallback(async ({ quiet } = {}) => {
    if (!quiet) setLoading(true);
    setError('');
    try {
      // Snapshot reader only — never triggers module probe fan-out.
      const body = await getMissionControlAgentMap();
      setMap(body);
      setSelected((prev) => prev || body?.agents?.[0] || null);
    } catch (err) {
      setError(err?.message || 'Failed to load Agent Map');
    } finally {
      if (!quiet) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    load();
    // Poll cached snapshot only while the panel is open.
    const t = window.setInterval(() => load({ quiet: true }), 90_000);
    return () => window.clearInterval(t);
  }, [open, load]);

  const warming = Boolean(map?._warming || map?.status === 'warming');
  const lastUpdated =
    map?.snapshot_meta?.persisted_at || map?.snapshot?.persisted_at || map?.generated_at || null;

  const agents = useMemo(() => {
    const list = map?.agents || [];
    const q = query.trim().toLowerCase();
    return list.filter((a) => {
      if (filter !== 'all' && a.status !== filter) return false;
      if (!q) return true;
      const blob = `${a.name} ${a.id} ${a.responsibility} ${(a.sources || []).join(' ')} ${a.group_label}`.toLowerCase();
      return blob.includes(q);
    });
  }, [map, filter, query]);

  const groups = useMemo(() => {
    const order = [];
    const buckets = new Map();
    for (const a of agents) {
      if (!buckets.has(a.group)) {
        buckets.set(a.group, { id: a.group, label: a.group_label, agents: [] });
        order.push(a.group);
      }
      buckets.get(a.group).agents.push(a);
    }
    return order.map((id) => buckets.get(id));
  }, [agents]);

  if (!open) return null;

  const summary = map?.summary || {};

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-black/55 backdrop-blur-sm">
      <div className="flex h-full w-full max-w-5xl flex-col border-l border-[var(--io-border)] bg-[#0b1220] shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-[var(--io-border)] px-5 py-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--io-gold)]">
              Mission Control · Agent Map
            </p>
            <h2 className="mt-1 flex items-center gap-2 text-xl font-semibold text-[var(--io-ink)]">
              <Bot className="h-5 w-5 text-[var(--io-gold)]" />
              All AGIB Agents
            </h2>
            <p className="mt-1 text-xs text-[var(--io-muted)]">
              {warming
                ? map?.message || 'Agent Map is initializing.'
                : summary.headline || 'Working / soft-wire / off status for every agent'}{' '}
              · {map?.version || 'agent-map'}
              {lastUpdated ? ` · snapshot ${lastUpdated}` : ''}
              {' · poll 90s while open'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => load()}
              disabled={loading}
              className="border-[var(--io-border)] text-[var(--io-ink)]"
            >
              <RefreshCw className={`mr-2 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Check snapshot
            </Button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-[var(--io-border)] p-2 text-[var(--io-muted)] hover:text-[var(--io-ink)]"
              aria-label="Close Agent Map"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {warming ? (
          <div className="border-b border-[var(--io-border)] px-5 py-4 text-sm text-[var(--io-muted)]">
            <p className="font-semibold text-[var(--io-ink)]">Agent Map is warming up.</p>
            <p className="mt-1">
              {map?.message || 'The first agent inventory snapshot is being generated by the worker.'}
            </p>
            <p className="mt-2 text-[11px] text-[var(--io-caption)]">
              Last updated: Unknown · Polling every 90s while open · Never rebuilds on refresh.
            </p>
          </div>
        ) : null}

        <div className="grid gap-2 border-b border-[var(--io-border)] px-5 py-3 sm:grid-cols-5">
          {[
            ['all', 'All', summary.total],
            ['working', 'Working', summary.working],
            ['soft', 'Soft', summary.soft],
            ['off', 'Off', summary.off],
            ['orphan', 'Orphan', summary.orphan],
          ].map(([key, label, count]) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              className={`rounded-xl border px-3 py-2 text-left text-xs ${
                filter === key
                  ? 'border-[var(--io-gold)] bg-[rgba(212,175,55,0.08)]'
                  : 'border-[var(--io-border)] bg-white/[0.02]'
              }`}
            >
              <span className="block text-[10px] uppercase tracking-wider text-[var(--io-caption)]">{label}</span>
              <span className="mt-0.5 block text-lg font-semibold tabular-nums text-[var(--io-ink)]">
                {count ?? '—'}
              </span>
            </button>
          ))}
        </div>

        <div className="border-b border-[var(--io-border)] px-5 py-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search agents, sources, responsibilities…"
            className="w-full rounded-xl border border-[var(--io-border)] bg-white/[0.03] px-3 py-2 text-sm text-[var(--io-ink)] outline-none focus:border-[var(--io-gold)]"
          />
          {error ? <p className="mt-2 text-xs text-amber-200">{error}</p> : null}
          {map?.production_flags ? (
            <p className="mt-2 text-[11px] text-[var(--io-caption)]">
              Flags · ASK_SLIM={String(map.production_flags.ASK_SLIM)} · FAA_BG=
              {String(map.production_flags.FAA_BACKGROUND_COLLECTOR)} · OfficesInAsk=
              {String(map.production_flags.AGI_V4_OFFICES_IN_ASK)} · FAA_LIVE=
              {String(map.production_flags.FAA_LIVE_FETCH)}
            </p>
          ) : null}
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[1.1fr_0.9fr]">
          <div className="min-h-0 overflow-y-auto border-r border-[var(--io-border)] px-4 py-4">
            {loading && !map ? (
              <p className="text-sm text-[var(--io-muted)]">Loading agent inventory…</p>
            ) : null}
            {groups.map((g) => (
              <div key={g.id} className="mb-5">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--io-gold)]">
                  {g.label}
                </p>
                <div className="flex flex-wrap gap-2">
                  {g.agents.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => setSelected(a)}
                      className={`rounded-xl border px-3 py-2 text-left transition ${
                        selected?.id === a.id
                          ? 'border-[var(--io-gold)] bg-[rgba(212,175,55,0.1)]'
                          : 'border-[var(--io-border)] bg-white/[0.02] hover:border-[var(--io-gold)]/50'
                      }`}
                    >
                      <span className="block text-sm font-medium text-[var(--io-ink)]">{a.name}</span>
                      <span className="mt-1 block">
                        <StatusPill status={a.status} />
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {!loading && !groups.length ? (
              <p className="text-sm text-[var(--io-muted)]">No agents match this filter.</p>
            ) : null}
          </div>

          <div className="min-h-0 overflow-y-auto px-5 py-5">
            {selected ? (
              <div className="space-y-4">
                <div>
                  <StatusPill status={selected.status} />
                  <h3 className="mt-2 text-2xl font-semibold text-[var(--io-ink)]">{selected.name}</h3>
                  <p className="mt-1 text-xs text-[var(--io-caption)]">{selected.id}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--io-gold)]">
                    Responsibility
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-[var(--io-ink)]">{selected.responsibility}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--io-gold)]">
                    Data sources
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {(selected.sources || []).map((s) => (
                      <span
                        key={s}
                        className="rounded-full border border-[var(--io-border)] bg-white/[0.03] px-2.5 py-1 text-[11px] text-[var(--io-muted)]"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--io-gold)]">
                    Status detail
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-[var(--io-muted)]">
                    {selected.detail || map?.status_legend?.[selected.status] || '—'}
                  </p>
                </div>
                {selected.probe && Object.keys(selected.probe).length ? (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--io-gold)]">
                      Probe
                    </p>
                    <pre className="mt-2 overflow-x-auto rounded-xl border border-[var(--io-border)] bg-black/30 p-3 text-[11px] text-[var(--io-caption)]">
                      {JSON.stringify(selected.probe, null, 2)}
                    </pre>
                  </div>
                ) : null}
                <div className="rounded-xl border border-[var(--io-border)] bg-white/[0.02] p-3 text-[11px] text-[var(--io-caption)]">
                  <p className="font-semibold text-[var(--io-muted)]">Legend</p>
                  <ul className="mt-2 space-y-1">
                    {Object.entries(map?.status_legend || {}).map(([k, v]) => (
                      <li key={k}>
                        <StatusPill status={k} /> <span className="ml-1">{v}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <p className="text-sm text-[var(--io-muted)]">Select an agent button to inspect status.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
