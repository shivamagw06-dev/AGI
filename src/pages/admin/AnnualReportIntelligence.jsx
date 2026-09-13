import { useState } from 'react';
import { FileSearch, Loader2 } from 'lucide-react';
import { judgeAnnualReport, readAnnualReport } from '@/lib/institutionalHoldingsApi';

/**
 * An annual report, read against the hundred questions an underwriter asks.
 *
 * Not tied to a manager. The publication pipeline answers "what did this fund
 * say" and is keyed to fifty 13F filers; these questions are about what an
 * operating company is worth, and any company has an annual report.
 *
 * Every row says how it was answered or why it was not, because most of them
 * are not answered from any one document and a blank row claims otherwise.
 */
const LABEL = {
  answered: 'from the report',
  computed: 'from the statements',
  silent: 'the report is silent',
  no_rule: 'no rule written yet',
  judgment: 'needs a reviewer',
  needs_data: 'needs statements',
};
const TONE = {
  answered: 'text-emerald-300',
  computed: 'text-sky-300',
  silent: 'text-slate-400',
  no_rule: 'text-slate-500',
  judgment: 'text-cyan-300/80',
  needs_data: 'text-amber-300/80',
};

/** A computed figure, in the units the statements were reported in. */
function figure(value) {
  if (value === null || value === undefined) return null;
  const rounded = Math.abs(value) < 10 ? Math.round(value * 10000) / 10000
    : Math.round(value * 100) / 100;
  return rounded.toLocaleString('en-US');
}

export default function AnnualReportIntelligence() {
  const [text, setText] = useState('');
  const [ticker, setTicker] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [judging, setJudging] = useState(false);
  const [judgements, setJudgements] = useState(null);
  const [auto, setAuto] = useState(false);

  const read = async () => {
    setBusy(true);
    setError('');
    try {
      setJudgements(null);
      setResult(await readAnnualReport({ text, ticker }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const runJudgements = async () => {
    setJudging(true);
    setError('');
    try {
      setJudgements(await judgeAnnualReport({ text, ticker, auto }));
    } catch (err) {
      setError(err.message);
    } finally {
      setJudging(false);
    }
  };

  // A computed question is answered when the arithmetic ran, and otherwise
  // carries the reason - which names the line item that was missing, and is
  // therefore the specification for what to load next.
  const rows = (result?.questions || []).map((question) => {
    const computed = result?.computed?.answers?.[question.n];
    const judged = (judgements?.judgements || []).find((entry) => entry.n === question.n) || null;
    if (question.kind === 'judgment') return { ...question, computed: null, judged };
    if (question.kind !== 'computed') return { ...question, computed: null, judged: null };
    if (computed && computed.reason === null) {
      return { ...question, status: 'computed', computed, judged: null };
    }
    return { ...question, status: 'needs_data', computed: computed || null, judged: null };
  });
  const counts = rows.reduce((tally, row) => (
    { ...tally, [row.status]: (tally[row.status] || 0) + 1 }), {});

  return (
    <section className="rounded-2xl border border-cyan-400/20 bg-[#07151d] p-6 text-slate-100 shadow-xl">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.24em] text-cyan-300">
        <FileSearch className="h-4 w-4" /> Annual report intelligence
      </div>
      <h2 className="mt-2 text-2xl font-semibold">A hundred questions, against one report</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
        Paste an annual report. Every question is answered from a sentence in the document,
        computed from statements already imported for the ticker, or marked with the reason it
        cannot be answered. The text is read and discarded — nothing is stored.
      </p>

      <div className="mt-5 grid gap-3 sm:grid-cols-4">
        <label className="block">
          <span className="text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">Ticker (optional)</span>
          <input
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
            placeholder="BRK.A"
            className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0d222d] px-2.5 py-2 text-xs text-white outline-none placeholder:text-slate-600 focus:border-cyan-400"
          />
          <span className="mt-1 block text-[10px] leading-4 text-slate-600">
            Joins the imported financial statements. Without it the computed questions
            name the line items they need instead.
          </span>
        </label>
      </div>

      <textarea
        value={text}
        onChange={(event) => { setText(event.target.value); setResult(null); }}
        rows={8}
        placeholder="Paste the annual report here…"
        className="mt-3 w-full rounded-lg border border-white/10 bg-[#0d222d] p-3 font-mono text-[11px] leading-5 text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-400"
      />
      <div className="mt-1.5 text-[10.5px] text-slate-500">
        {text.length ? `${text.length.toLocaleString()} characters` : 'Nothing pasted yet'}
      </div>

      {error ? (
        <div className="mt-3 rounded-lg border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">{error}</div>
      ) : null}

      <button
        type="button"
        onClick={read}
        disabled={!text.trim() || busy}
        className="mt-3 inline-flex items-center gap-2 rounded-xl bg-cyan-300 px-5 py-2.5 text-sm font-bold text-slate-950 disabled:opacity-40"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
        Read the report
      </button>

      {result ? (
        <div className="mt-6">
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-[11px]">
            {['answered', 'computed', 'needs_data', 'silent', 'no_rule', 'judgment'].map((status) => (
              <span key={status} className={TONE[status]}>
                <span className="tabular-nums font-semibold">{counts[status] || 0}</span>{' '}
                <span className="text-slate-500">{LABEL[status]}</span>
              </span>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={runJudgements}
              disabled={judging}
              className="inline-flex items-center gap-2 rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-1.5 text-xs font-semibold text-cyan-200 hover:border-cyan-400/60 disabled:opacity-40"
            >
              {judging ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              {judgements ? 'Run again' : auto ? 'Try every unanswered question' : 'Answer the nine judgement questions'}
            </button>
            <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-300">
              <input
                type="checkbox"
                checked={auto}
                onChange={(event) => setAuto(event.target.checked)}
                className="h-3.5 w-3.5 accent-cyan-400"
              />
              Try every unanswered question
            </label>
            <span className="max-w-xl text-[10.5px] leading-4 text-slate-500">
              {auto
                ? 'One model request per unanswered question, reasoning only over sentences '
                  + 'retrieved from this report. A question the report is silent on comes back '
                  + 'refused — that is the correct answer, not a failure to reach a hundred.'
                : 'Nine model requests, reasoning only over the answers above. Every figure in a '
                  + 'conclusion is checked against them; nothing is published without a reviewer.'}
            </span>
          </div>

          {result.computed?.reason ? (
            <div className="mt-2 text-[10.5px] text-amber-300/80">{result.computed.reason}</div>
          ) : null}
          {result.computed?.periods ? (
            <div className="mt-2 text-[10.5px] text-slate-500">
              {`${result.computed.ticker}: ${result.computed.periods.periods} annual periods, `
                + `${result.computed.periods.from} to ${result.computed.periods.to}, `
                + result.computed.periods.units.join(', ')}
            </div>
          ) : null}

          <ol className="mt-4 space-y-2.5 border-t border-white/10 pt-4">
            {rows.map((row) => (
              <li key={row.n} className="grid grid-cols-[1.9rem_1fr] gap-2">
                <span className="pt-0.5 text-[10.5px] tabular-nums text-slate-600">{row.n}</span>
                <div className="min-w-0">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[11.5px] text-slate-200">{row.ask}</span>
                    <span className={`shrink-0 text-[10px] ${TONE[row.status]}`}>{LABEL[row.status]}</span>
                  </div>
                  {row.answer ? (
                    <p className="mt-0.5 text-[11px] leading-[1.55] text-slate-400">
                      {row.answer}
                      {row.more ? <span className="text-slate-600">{` · ${row.more} more`}</span> : null}
                    </p>
                  ) : null}
                  {row.computed && row.computed.reason === null ? (
                    <p className="mt-0.5 text-[11px] leading-[1.55] text-sky-200/90">
                      <span className="font-semibold tabular-nums">{figure(row.computed.value)}</span>
                      {/* The formula is shown beside the figure so a reader can
                          check it rather than take it. */}
                      <span className="text-slate-500">{` — ${row.computed.formula}`}</span>
                    </p>
                  ) : null}
                  {/* What it would take, never a blank. */}
                  {row.computed && row.computed.reason ? (
                    <p className="mt-0.5 text-[10.5px] text-slate-600">{row.computed.reason}</p>
                  ) : null}
                  {!row.computed && !row.answer && row.needs ? (
                    <p className="mt-0.5 text-[10.5px] text-slate-600">{`needs ${row.needs.join(', ')}`}</p>
                  ) : null}
                  {!row.answer && row.note && !row.judged ? (
                    <p className="mt-0.5 text-[10.5px] text-slate-600">{row.note}</p>
                  ) : null}
                  {/* A conclusion, with the count of evidence behind it. The
                      evidence itself is returned too: a judgement a reader
                      cannot check against what produced it is not reviewable. */}
                  {row.judged?.judgement ? (
                    <p className="mt-0.5 text-[11px] leading-[1.55] text-cyan-100/90">
                      {row.judged.judgement.conclusion}
                      <span className="text-slate-500">
                        {` — from ${row.judged.judgement.evidence_ids.length} of `
                          + `${row.judged.evidence_count} evidence items, awaiting review`}
                      </span>
                    </p>
                  ) : null}
                  {row.judged?.refused ? (
                    <p className="mt-0.5 text-[10.5px] text-amber-300/80">
                      {`refused: ${row.judged.refused}`}
                    </p>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
