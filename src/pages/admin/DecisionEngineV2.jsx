import { useCallback, useEffect, useState } from 'react';
import { Scale, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  analyseIdev2,
  getIdev2Dashboard,
  getIdev2FreezeReview,
  getIdev2Health,
  getIdev2Monitoring,
  getIdev2QualityGates,
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

export default function DecisionEngineV2() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [freeze, setFreeze] = useState(null);
  const [pack, setPack] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [ticker, setTicker] = useState('HDFCBANK');
  const [question, setQuestion] = useState(
    'What is the highest-quality institutional decision for HDFC Bank?'
  );
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g, f] = await Promise.all([
        getIdev2Health(),
        getIdev2Dashboard(),
        getIdev2QualityGates(),
        getIdev2FreezeReview(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
      setFreeze(f);
    } catch (err) {
      setError(err?.message || 'Failed to load IDE V2');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onAnalyse = async () => {
    setBusy('analyse');
    setError('');
    try {
      const out = await analyseIdev2({ ticker, question });
      setPack(out);
      const mon = await getIdev2Monitoring(ticker || 'HDFCBANK');
      setMonitoring(mon);
    } catch (err) {
      setError(err?.message || 'Analyse failed');
    } finally {
      setBusy('');
    }
  };

  const weights = pack?.weights?.weights || {};
  const conflicts = pack?.conflicts?.conflicts || [];
  const gate = pack?.recommendation_gate || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-700 font-semibold">
            Institutional Decision Engine V2 · FINAL architectural component · architecture frozen
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Scale className="h-6 w-6 text-slate-800" />
            What is the highest-quality institutional decision?
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Constitutional orchestrator across FIL→SSL, analysts, committee and portfolio office.
            Readiness statuses only — never forced Buy/Hold/Sell. No new top-level layers after this.
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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'ide-v2'} />
        <Stat
          label="Sample gate"
          value={pack?.recommendation_gate?.status ?? dashboard?.sample_gate ?? '—'}
          hint="policy readiness"
        />
        <Stat
          label="Confidence"
          value={pack?.confidence?.confidence ?? dashboard?.sample_confidence ?? '—'}
          hint="calibrated"
        />
        <Stat
          label="Freeze review"
          value={freeze?.passed ? 'Pass' : 'Review'}
          hint="AGIB v3 complete"
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint="audit · conflicts · no policy breach"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Decision pipeline</h2>
          <input
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <textarea
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm min-h-[88px]"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <Button variant="outline" onClick={onAnalyse} disabled={!!busy}>
            {busy === 'analyse' ? 'Orchestrating…' : 'POST /decision-engine-v2/analyse'}
          </Button>
          <p className="text-xs text-slate-400">
            {pack?.report?.cio_brief || dashboard?.sample_summary || 'Run analyse to build a constitutional package.'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Recommendation gate</h2>
          <p className="font-semibold text-slate-800">{gate.status || '—'}</p>
          <ul className="space-y-1 text-slate-600">
            {(gate.reasons || []).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
          <p className="text-xs text-slate-400">
            Forced trade: {String(gate.forced_buy_hold_sell ?? false)} · policy governed
          </p>
          <p className="text-xs text-slate-500 mt-2">
            Audit {pack?.audit?.audit_id || dashboard?.sample_audit_id || '—'}
          </p>
        </div>
      </div>

      {pack?.found ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Transparent weights</h2>
            <ul className="space-y-1 text-slate-600">
              {Object.entries(weights).map(([k, v]) => (
                <li key={k} className="flex justify-between border-b border-slate-100 py-1">
                  <span>{k}</span>
                  <span className="font-medium">{v}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Conflict matrix</h2>
            <ul className="space-y-2 text-slate-600">
              {conflicts.map((c, i) => (
                <li key={i}>
                  <span className="text-xs uppercase tracking-wide text-rose-700 mr-2">
                    {(c.type || '').replaceAll('_', ' ')}
                  </span>
                  {c.why}
                </li>
              ))}
              {!conflicts.length ? <li className="text-slate-400">No material conflicts disclosed.</li> : null}
            </ul>
            <p className="text-xs text-slate-500 mt-2">
              Uncertainty: {pack.uncertainty?.dominant} · coverage {pack.evidence_summary?.coverage}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Monitoring queue</h2>
            <ul className="space-y-1 text-slate-600">
              {(pack.monitoring?.watch_items || []).slice(0, 6).map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
            <p className="text-xs text-slate-400 mt-2">
              Review {pack.monitoring?.review_date} · history rows {monitoring?.count ?? 0}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Architecture freeze</h2>
            <p className="text-slate-600">
              {freeze?.post_freeze_rule ||
                'Future work improves evidence, coverage, reasoning, calibration — not architecture.'}
            </p>
            <ul className="text-xs text-slate-500 space-y-1 mt-2">
              {Object.entries(freeze?.checklist || {}).map(([k, ok]) => (
                <li key={k}>
                  {ok ? '✓' : '✗'} {k.replaceAll('_', ' ')}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Quality gates</h2>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              gates?.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
            }`}
          >
            {gates?.passed ? 'Pass' : 'Review'}
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(gates?.checks || {}).map(([key, ok]) => (
            <div
              key={key}
              className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
            >
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
