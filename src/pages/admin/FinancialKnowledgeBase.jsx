import { useCallback, useEffect, useState } from 'react';
import { BookOpen, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getFkbDashboard,
  getFkbGlossary,
  getFkbHealth,
  getFkbMetrics,
  getFkbRatios,
  getFkbRelationships,
  getFkbThresholds,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value ?? '—'}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

export default function FinancialKnowledgeBase() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [ratios, setRatios] = useState(null);
  const [relationships, setRelationships] = useState(null);
  const [thresholds, setThresholds] = useState(null);
  const [glossary, setGlossary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, m, r, rel, t, g] = await Promise.all([
        getFkbHealth(),
        getFkbDashboard(),
        getFkbMetrics(),
        getFkbRatios(),
        getFkbRelationships(),
        getFkbThresholds(),
        getFkbGlossary(),
      ]);
      setHealth(h);
      setDashboard(d);
      setMetrics(m);
      setRatios(r);
      setRelationships(rel);
      setThresholds(t);
      setGlossary(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Financial Knowledge Base');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-600 font-semibold">
            FKB-01 · Institutional Financial Knowledge Base
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-slate-700" />
            Canonical financial concepts
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Single source of truth for metrics, ratios, relationships, thresholds and glossary.
            Definitions only — no analysis, no BUY/SELL.
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version} />
        <Stat label="Metrics" value={dashboard?.metrics_loaded ?? metrics?.n ?? '—'} />
        <Stat label="Ratios" value={dashboard?.ratios_loaded ?? ratios?.n ?? '—'} />
        <Stat label="Relationships" value={dashboard?.relationships_loaded ?? relationships?.n ?? '—'} />
        <Stat label="Thresholds" value={dashboard?.thresholds_loaded ?? thresholds?.n ?? '—'} />
        <Stat
          label="Validation"
          value={dashboard?.validation_status ?? '—'}
          hint={`Glossary ${dashboard?.glossary_loaded ?? glossary?.n ?? '—'}`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 text-sm space-y-2 max-h-80 overflow-auto">
          <h2 className="font-semibold text-slate-900">Sample metrics</h2>
          {(metrics?.metrics || []).slice(0, 12).map((m) => (
            <div key={m.id} className="flex justify-between border-b border-slate-50 py-1">
              <span>{m.display_name}</span>
              <span className="text-slate-400 text-xs">{m.category}</span>
            </div>
          ))}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 text-sm space-y-2 max-h-80 overflow-auto">
          <h2 className="font-semibold text-slate-900">Sample relationships</h2>
          {(relationships?.relationships || []).slice(0, 12).map((r) => (
            <div key={r.id} className="border-b border-slate-50 py-1">
              <div className="flex justify-between">
                <span className="font-medium">{r.id}</span>
                <span className="text-xs text-slate-400">{r.severity}</span>
              </div>
              <p className="text-xs text-slate-500">{r.narrative_template}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
