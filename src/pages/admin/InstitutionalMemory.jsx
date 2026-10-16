import { useCallback, useEffect, useState } from 'react';
import { BookMarked, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getIlmCompany,
  getIlmDashboard,
  getIlmHealth,
  getIlmPortfolio,
  getIlmQualityGates,
  updateIlmLearning,
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

export default function InstitutionalMemory() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [pack, setPack] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [ticker, setTicker] = useState('HDFCBANK');
  const [portfolioId, setPortfolioId] = useState('agib_core_india');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [lessonNote, setLessonNote] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getIlmHealth(),
        getIlmDashboard(),
        getIlmQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Institutional Memory');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCompany = async () => {
    setBusy('company');
    setError('');
    try {
      const out = await getIlmCompany(ticker || 'HDFCBANK');
      setPack(out);
    } catch (err) {
      setError(err?.message || 'Company learning pack failed');
    } finally {
      setBusy('');
    }
  };

  const onPortfolio = async () => {
    setBusy('portfolio');
    setError('');
    try {
      const out = await getIlmPortfolio(portfolioId || 'agib_core_india');
      setPortfolio(out);
    } catch (err) {
      setError(err?.message || 'Portfolio memory failed');
    } finally {
      setBusy('');
    }
  };

  const onLearningUpdate = async () => {
    setBusy('learning');
    setError('');
    try {
      const out = await updateIlmLearning({
        ticker: ticker || 'HDFCBANK',
        date: new Date().toISOString().slice(0, 10),
        expected: 'base',
        observed: 'lesson_logged',
        difference: 'manual admin learning note',
        reason: 'admin_update',
        lesson: lessonNote || 'Admin-recorded institutional lesson (append-only)',
        updated_knowledge: lessonNote || 'Admin-recorded institutional lesson (append-only)',
      });
      setPack(out.company || out);
      setLessonNote('');
    } catch (err) {
      setError(err?.message || 'Learning update failed');
    } finally {
      setBusy('');
    }
  };

  const learning = pack?.learning?.institutional_learning || {};
  const mistakes = pack?.mistakes?.mistakes || [];
  const theses = pack?.thesis?.evolution || pack?.thesis?.theses || [];
  const decisions = pack?.decisions?.entries || pack?.committee?.decisions || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-teal-800 font-semibold">
            Institutional Learning & Memory Engine v1.0 · soft layer · includes MIE
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <BookMarked className="h-6 w-6 text-teal-800" />
            What have we learned?
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Active institutional learning — theses, committee votes, forecasts and portfolio
            actions preserved, versioned and evaluated against outcomes. Mistakes are classified,
            not merely archived.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-36"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <Button variant="outline" onClick={onCompany} disabled={!!busy}>
            {busy === 'company' ? 'Loading…' : 'Company'}
          </Button>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'ilm'} />
        <Stat
          label="Sample lessons"
          value={pack?.learning?.institutional_learning?.lesson_count ?? dashboard?.sample_lesson_count ?? '—'}
          hint="after outcomes"
        />
        <Stat
          label="Mistakes (MIE)"
          value={pack?.mistakes?.mistake_count ?? dashboard?.sample_mistake_count ?? '—'}
          hint="classified error types"
        />
        <Stat
          label="Thinking improved"
          value={
            (learning.thinking_improved ?? null) === null
              ? '—'
              : learning.thinking_improved
                ? 'Yes'
                : 'No'
          }
          hint="thesis outcomes"
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint="No overwrite · MIE active"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Append learning update</h2>
          <textarea
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm min-h-[88px]"
            value={lessonNote}
            onChange={(e) => setLessonNote(e.target.value)}
            placeholder="Lesson / updated institutional knowledge (append-only)"
          />
          <Button variant="outline" onClick={onLearningUpdate} disabled={!!busy}>
            {busy === 'learning' ? 'Appending…' : 'POST /ilm/learning/update'}
          </Button>
          <p className="text-xs text-slate-400">
            {pack?.report?.executive_summary || dashboard?.sample_summary || 'Load a company pack to inspect lessons.'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Portfolio memory</h2>
          <div className="flex gap-2">
            <input
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-full"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              placeholder="portfolio id"
            />
            <Button variant="outline" onClick={onPortfolio} disabled={!!busy}>
              {busy === 'portfolio' ? 'Loading…' : 'Load'}
            </Button>
          </div>
          {portfolio ? (
            <pre className="text-xs bg-slate-50 border border-slate-100 rounded-lg p-3 overflow-auto max-h-56">
              {JSON.stringify(
                {
                  portfolio_id: portfolio.portfolio_id,
                  actions: (portfolio.actions || portfolio.history || []).slice?.(0, 4) || portfolio.actions,
                  mistakes: portfolio.mistakes,
                  success_rate: portfolio.success_rate,
                },
                null,
                2
              )}
            </pre>
          ) : (
            <p className="text-xs text-slate-400">Track rebalances, allocations and classified portfolio errors.</p>
          )}
        </div>
      </div>

      {pack?.found ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Thesis evolution — {pack.ticker}</h2>
            <ul className="space-y-2 text-slate-600">
              {theses.slice(0, 8).map((t, i) => (
                <li key={i}>
                  <span className="text-xs uppercase tracking-wide text-teal-800 mr-2">
                    {t.date || t.version}
                  </span>
                  {t.stance || t.thesis}
                  <span className="text-slate-400">
                    {' '}
                    · conf {t.confidence}
                    {t.outcome ? ` · ${t.outcome}` : ''}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Mistake Intelligence</h2>
            <ul className="space-y-2 text-slate-600">
              {mistakes.slice(0, 8).map((m, i) => (
                <li key={i}>
                  <span className="text-xs uppercase tracking-wide text-rose-700 mr-2">
                    {(m.error_type || '').replaceAll('_', ' ')}
                  </span>
                  {m.example || m.context}
                  {m.lesson ? <p className="text-xs text-slate-400 mt-0.5">{m.lesson}</p> : null}
                </li>
              ))}
              {!mistakes.length ? <li className="text-slate-400">No classified mistakes in pack.</li> : null}
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Decision journal / committee</h2>
            <ul className="space-y-2 text-slate-600">
              {decisions.slice(0, 6).map((d, i) => (
                <li key={i}>
                  <span className="text-xs uppercase tracking-wide text-teal-800 mr-2">
                    {d.date || d.review_date || d.version}
                  </span>
                  {d.decision || d.consensus || d.question}
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-400 mt-2">{pack?.report?.cio_brief}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Lessons learned</h2>
            <ul className="space-y-2 text-slate-600">
              {(pack?.learning?.lessons || []).slice(0, 6).map((l, i) => (
                <li key={i}>
                  <span className="text-xs text-slate-400 mr-2">{l.date}</span>
                  {l.lesson || l.updated_knowledge}
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-500 mt-2">
              Improved: {(learning.what_improved || []).slice(0, 2).join(' · ') || '—'}
            </p>
            <p className="text-xs text-slate-500">
              Failed: {(learning.what_failed || []).slice(0, 2).join(' · ') || '—'}
            </p>
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
