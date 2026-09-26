import { useCallback, useEffect, useState } from 'react';
import { MessageSquare, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getDebateEngineDashboard,
  getDebateEngineHealth,
  getDebateEngineQualityGates,
  planDebateEngine,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value ?? '—'}</p>
      {hint ? <p className="mt-1 text-xs text-slate-400">{hint}</p> : null}
    </div>
  );
}

function tone(position) {
  if (['Strong Support', 'Support'].includes(position)) return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  if (position === 'Neutral') return 'border-slate-200 bg-slate-50 text-slate-700';
  return 'border-rose-200 bg-rose-50 text-rose-800';
}

export default function InstitutionalDebate() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState('Should I buy HDFC Bank?');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getDebateEngineHealth(),
        getDebateEngineDashboard(),
        getDebateEngineQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Institutional Debate');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (nextQuestion = question) => {
    const next = nextQuestion.trim();
    if (!next) return;
    setBusy(true);
    setError('');
    setQuestion(next);
    try {
      setResult(await planDebateEngine({ question: next }));
    } catch (err) {
      setError(err?.message || 'Institutional debate failed');
    } finally {
      setBusy(false);
    }
  };

  const debate = result?.debate || {};
  const positions = debate.analyst_positions || [];
  const disagreement = debate.disagreement || {};
  const consensus = debate.consensus || {};
  const tournament = debate.challenge_tournament || {};
  const scorecard = debate.debate_scorecard || {};

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1450px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-700">
            RQ2 Sprint 8 · Structured Pre-Committee Debate · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <MessageSquare className="h-6 w-6 text-orange-700" />
            Institutional Debate
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Expose disagreement, challenge assumptions, preserve minority views and identify the
            evidence required to settle the debate before the Committee votes.
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <ShieldAlert className="h-4 w-4 shrink-0" /> {error}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Status" value={health?.status || (loading ? '…' : '—')} />
        <Stat label="Version" value={health?.version || '—'} hint={health?.sprint_name} />
        <Stat
          label="Debate Scenarios"
          value={gates?.debate_scenarios?.toLocaleString?.() || '—'}
          hint={gates ? `${gates.passed}/${gates.total} passed` : undefined}
        />
        <Stat
          label="Disagreements Tested"
          value={gates?.analyst_disagreements?.toLocaleString?.() || '—'}
          hint={gates ? `${gates.avg_debate_ms} ms average` : undefined}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && run()}
          />
          <Button onClick={() => run()} disabled={busy}>
            {busy ? 'Debating…' : 'Run Institutional Debate'}
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {(dashboard?.samples || []).map((sample) => (
            <button
              key={sample.question}
              type="button"
              className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs"
              onClick={() => run(sample.question)}
            >
              {sample.question}
            </button>
          ))}
        </div>
      </div>

      {result ? (
        <div className="space-y-5">
          <div className="rounded-xl border border-orange-200 bg-orange-50/60 p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-orange-700">
              Investment Thesis Under Debate
            </p>
            <p className="mt-2 text-base font-semibold text-slate-900">{debate.investment_thesis}</p>
          </div>

          <div>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Analyst Positions
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {positions.map((position) => (
                <div key={position.analyst} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-semibold text-slate-900">{position.analyst}</p>
                    <span className={`rounded-md border px-2 py-0.5 text-[10px] ${tone(position.position)}`}>
                      {position.position}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-600">{position.conclusion}</p>
                  <p className="mt-2 text-[10px] text-slate-400">
                    Confidence {position.confidence_pct}% · revisions {position.revision_count}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Stat label="Agreement" value={`${consensus.agreement_pct ?? '—'}%`} />
            <Stat label="Consensus Confidence" value={`${consensus.confidence_pct ?? '—'}%`} />
            <Stat label="Debate State" value={consensus.state} hint={consensus.vote_ready ? 'Vote ready' : 'More resolution required'} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Disagreement Matrix · {disagreement.disagreement_count} conflicts
              </p>
              {(disagreement.conflicts || []).slice(0, 10).map((conflict) => (
                <div key={conflict.id} className="rounded-lg border border-rose-100 bg-rose-50/40 px-3 py-2">
                  <p className="text-sm font-medium text-slate-800">{conflict.topic}</p>
                  <p className="text-xs text-slate-600">
                    {conflict.analyst_a} ({conflict.position_a}) vs {conflict.analyst_b} ({conflict.position_b})
                  </p>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Evidence Conflicts
              </p>
              {(debate.evidence_conflicts || []).slice(0, 8).map((conflict) => (
                <div key={conflict.id} className="rounded-lg border border-amber-100 bg-amber-50/40 px-3 py-2">
                  <div className="flex justify-between gap-2">
                    <p className="text-sm font-medium text-slate-800">{conflict.topic}</p>
                    <span className="text-xs font-semibold">{conflict.evidence_quality}</span>
                  </div>
                  <p className="text-xs text-slate-600">
                    Need: {(conflict.required_additional_evidence || []).join(', ')}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Challenge Tournament · {tournament.round_count} rounds
            </p>
            {(tournament.rounds || []).map((round) => (
              <div key={round.round} className="rounded-lg border border-orange-100 bg-orange-50/30 p-3">
                <p className="text-xs font-bold text-orange-800">Round {round.round}</p>
                <p className="mt-1 text-sm text-slate-800">
                  <strong>{round.challenger}</strong> → <strong>{round.respondent}</strong>: {round.challenge}
                </p>
                <p className="mt-1 text-xs text-slate-600">{round.response}</p>
                <p className="mt-1 text-[10px] text-slate-400">
                  {round.revision.from_position} → {round.revision.to_position} · confidence{' '}
                  {Math.round(Number(round.revision.confidence_after) * 100)}%
                </p>
              </div>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Minority Report
              </p>
              {(debate.minority_report || []).map((minority) => (
                <div key={minority.analyst} className="rounded-lg border border-violet-100 bg-violet-50/40 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-900">
                    {minority.analyst} · {minority.minority_position}
                  </p>
                  <p className="text-xs text-slate-600">{minority.conclusion}</p>
                  <p className="mt-1 text-[10px] text-violet-700">
                    Becomes majority if: {(minority.conditions_to_become_majority || []).join('; ')}
                  </p>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Debate Scorecard · {scorecard.overall} · {scorecard.grade}
              </p>
              {Object.entries(scorecard.metrics || {}).map(([metric, score]) => (
                <div key={metric} className="flex justify-between text-sm">
                  <span className="text-slate-700">{(scorecard.metric_labels || {})[metric] || metric}</span>
                  <strong>{score}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Moderator</p>
            <p className="mt-1 text-sm text-slate-800">{debate.moderator?.agreement_summary}</p>
            <p className="mt-1 text-sm text-slate-800">{debate.moderator?.disagreement_summary}</p>
            <p className="mt-2 text-xs font-semibold text-orange-800">{debate.moderator?.moderator_conclusion}</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
