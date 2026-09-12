import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, FileText, Loader2, RefreshCw, XCircle } from 'lucide-react';
import { getPublicationClaims, reviewPublicationClaims } from '@/lib/institutionalHoldingsApi';

/**
 * The queue a person works to decide what a pasted document said.
 *
 * 520 claims sat invisible across two documents because the only way to
 * approve one was a SQL statement, which made the layer correct and unusable
 * at the same time.
 *
 * The sentence is the interface. Everything else on a row - the step, the
 * business, whose arithmetic the number is - is a label on that sentence, and
 * a reviewer who cannot read the sentence cannot decide anything. So the
 * sentence gets the full width and normal reading size, and the labels are
 * small and grey around it.
 *
 * Reject sits beside approve, the same size. A queue whose only button is
 * approve launders the extractor's mistakes, and this extractor published a
 * balance-sheet row, five date ranges and a wildfire mitigation filed as a
 * hazard in the course of one day.
 *
 * There is no "approve everything matching this filter". The selection is the
 * rows on screen, which is what makes an approval mean someone saw it.
 */

/** Dark, matching the admin shell rather than the public page. */
const SLOT_LABEL = {
  what_happened: 'What happened?',
  why: 'Why did it happen?',
  how: 'How did the business respond?',
  how_much: 'How much?',
  what_changed: 'What changed vs last year?',
  expectations: 'What does management expect next?',
  risks: 'What could go wrong?',
  holding: 'Disclosed holding',
};

const BASIS_TONE = {
  stated: 'bg-sky-400/10 text-sky-300',
  derived: 'bg-violet-400/10 text-violet-300',
  inferred: 'bg-amber-400/10 text-amber-300',
};

/** The move a change claim records, in the unit the document used. */
function changeLabel(change) {
  if (!change || change.delta === null || change.delta === undefined) return null;
  const unit = change.kind === 'percentage_points' ? 'pp' : change.kind === 'percent' ? '%' : '';
  const arrow = change.direction === 'up' ? '▲' : change.direction === 'down' ? '▼' : '=';
  return `${arrow} ${change.delta}${unit}`;
}

function Row({ claim, checked, onToggle }) {
  const move = changeLabel(claim.change);
  return (
    <li className={`rounded-xl border p-4 transition ${checked
      ? 'border-cyan-400/40 bg-cyan-400/[0.06]'
      : 'border-white/10 bg-white/[0.03] hover:border-white/20'}`}>
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={checked}
          onChange={() => onToggle(claim.id)}
          aria-label={`Select claim: ${claim.source_excerpt.slice(0, 60)}`}
          className="mt-1 h-4 w-4 shrink-0 accent-cyan-400"
        />
        <div className="min-w-0 flex-1">
          {/* The sentence, in full. A truncated quote cannot be judged, and
              judging it is the only thing this screen is for. */}
          <p className="text-[13.5px] leading-6 text-slate-100">{claim.source_excerpt}</p>

          <div className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-[11px]">
            <span className="rounded-full bg-white/[0.06] px-2 py-0.5 font-semibold text-slate-300">
              {SLOT_LABEL[claim.slot || 'holding'] || claim.slot}
            </span>
            {claim.basis ? (
              <span className={`rounded-full px-2 py-0.5 font-semibold ${BASIS_TONE[claim.basis] || 'bg-white/[0.06] text-slate-400'}`}
                title={claim.basis === 'derived'
                  ? 'We computed this delta from two figures the document states'
                  : 'The filer wrote this; the sentence is their words'}>
                {claim.basis}
              </span>
            ) : null}
            {move ? <span className="rounded-full bg-white/[0.06] px-2 py-0.5 font-semibold tabular-nums text-slate-200">{move}</span> : null}
            {claim.metric ? <span className="text-slate-400">{claim.metric}</span> : null}
            {claim.issuer ? <span className="text-slate-400">{claim.issuer}{claim.unit ? ` · ${claim.unit}` : ''}</span> : null}
            {/* Inherited attribution is weaker evidence than a sentence that
                names its own business, and the reviewer is the only one who
                can tell whether a heading twenty-five sentences up still
                applies. */}
            {claim.segment ? (
              <span className={claim.segment_source === 'from_heading' ? 'text-amber-300/80' : 'text-slate-400'}
                title={claim.segment_source === 'from_heading'
                  ? 'Inherited from a section heading, not named in this sentence'
                  : 'Named in this sentence'}>
                {claim.segment}{claim.segment_source === 'from_heading' ? ' (from heading)' : ''}
              </span>
            ) : null}
            {claim.themes?.length ? <span className="text-slate-500">{claim.themes.join(' · ')}</span> : null}
          </div>

          <div className="mt-1.5 text-[10.5px] text-slate-500">
            {claim.manager}{claim.publication ? ` · ${claim.publication}` : ''}
            {claim.status !== 'pending'
              ? ` · ${claim.status}${claim.reviewed_by ? ` by ${claim.reviewed_by}` : ''}`
              : ''}
          </div>
        </div>
      </div>
    </li>
  );
}

export default function PublicationReview() {
  const [status, setStatus] = useState('pending');
  const [slot, setSlot] = useState('');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(() => new Set());
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async (nextOffset = offset) => {
    setLoading(true);
    setError('');
    try {
      const payload = await getPublicationClaims({ status, slot, limit: 50, offset: nextOffset });
      setData(payload);
      // Cleared on every load: a selection that outlives the rows it referred
      // to is how someone approves a claim they are no longer looking at.
      setSelected(new Set());
    } catch (loadError) {
      setError(loadError.message || 'Could not read the review queue.');
    } finally {
      setLoading(false);
    }
  }, [status, slot, offset]);

  useEffect(() => { load(offset); }, [load, offset]);

  const rows = data?.rows || [];
  const counts = data?.counts || [];
  const pendingTotal = useMemo(
    () => counts.reduce((total, entry) => total + entry.pending, 0), [counts],
  );

  const toggle = (id) => setSelected((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const decide = async (decision) => {
    if (!selected.size) return;
    setWorking(decision);
    setError('');
    setMessage('');
    try {
      const result = await reviewPublicationClaims([...selected], decision);
      setMessage(`${result.decided} claim(s) ${decision}.`
        + (result.missing?.length ? ` ${result.missing.length} were already gone.` : ''));
      await load(offset);
    } catch (decideError) {
      setError(decideError.message || 'Could not record the decision.');
    } finally {
      setWorking('');
    }
  };

  return (
    <section className="overflow-hidden rounded-2xl border border-cyan-400/20 bg-[#07151d] text-slate-100 shadow-2xl shadow-slate-950/10">
      <div className="border-b border-white/10 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300">Publication review</div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-white">What a fund said, awaiting a decision</h2>
            <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-400">
              Each row is a sentence from a document someone pasted in. Approving one publishes
              that sentence on the manager card; rejecting one removes it from consideration.
              Nothing here was written by us — read the sentence and decide.
            </p>
          </div>
          <button
            type="button"
            onClick={() => load(offset)}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-semibold text-slate-200 hover:border-cyan-400/40 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </button>
        </div>

        {counts.length ? (
          <div className="mt-5 flex flex-wrap gap-2">
            {/* Clicking a step filters to it. The counts are the whole queue,
                not this page, so the reviewer can see what is left. */}
            <button
              type="button"
              onClick={() => { setSlot(''); setOffset(0); }}
              className={`rounded-xl border px-3 py-2 text-left transition ${slot === ''
                ? 'border-cyan-400/40 bg-cyan-400/[0.08]' : 'border-white/10 bg-white/[0.03] hover:border-white/20'}`}
            >
              <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">All steps</div>
              <div className="mt-0.5 text-lg font-semibold tabular-nums text-white">{pendingTotal}</div>
            </button>
            {counts.filter((entry) => entry.pending > 0).map((entry) => (
              <button
                key={entry.slot}
                type="button"
                onClick={() => { setSlot(entry.slot); setOffset(0); }}
                className={`rounded-xl border px-3 py-2 text-left transition ${slot === entry.slot
                  ? 'border-cyan-400/40 bg-cyan-400/[0.08]' : 'border-white/10 bg-white/[0.03] hover:border-white/20'}`}
              >
                <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                  {SLOT_LABEL[entry.slot] || entry.slot}
                </div>
                <div className="mt-0.5 text-lg font-semibold tabular-nums text-white">{entry.pending}</div>
                <div className="text-[10px] text-slate-500">
                  {entry.approved} approved{entry.by_rule ? ` · ${entry.by_rule} by rule` : ''}
                  {entry.rejected ? ` · ${entry.rejected} rejected` : ''}
                </div>
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 bg-white/[0.02] px-6 py-3">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-500">Showing</span>
          <select
            value={status}
            onChange={(event) => { setStatus(event.target.value); setOffset(0); }}
            className="rounded-lg border border-white/10 bg-[#0d222d] px-2 py-1.5 text-xs text-white outline-none focus:border-cyan-400"
          >
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="all">All</option>
          </select>
          {data?.total !== null && data?.total !== undefined ? (
            <span className="text-slate-500">
              {data.total.toLocaleString()} match{data.total === 1 ? '' : 'es'}
              {rows.length ? ` · showing ${offset + 1}–${offset + rows.length}` : ''}
            </span>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setSelected(new Set(rows.map((claim) => claim.id)))}
            disabled={!rows.length}
            className="rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-300 hover:border-white/25 disabled:opacity-40"
          >
            Select page
          </button>
          <button
            type="button"
            onClick={() => setSelected(new Set())}
            disabled={!selected.size}
            className="rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-300 hover:border-white/25 disabled:opacity-40"
          >
            Clear
          </button>
          {/* Same size, side by side. A queue whose reject button is harder to
              reach approves things by default. */}
          <button
            type="button"
            onClick={() => decide('rejected')}
            disabled={!selected.size || Boolean(working)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-400/30 bg-rose-400/10 px-3 py-1.5 text-xs font-semibold text-rose-200 hover:border-rose-400/60 disabled:opacity-40"
          >
            {working === 'rejected' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <XCircle className="h-3.5 w-3.5" />}
            Reject {selected.size || ''}
          </button>
          <button
            type="button"
            onClick={() => decide('approved')}
            disabled={!selected.size || Boolean(working)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:border-emerald-400/60 disabled:opacity-40"
          >
            {working === 'approved' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            Approve {selected.size || ''}
          </button>
        </div>
      </div>

      {error ? <div className="border-b border-rose-400/20 bg-rose-500/10 px-6 py-3 text-xs text-rose-200">{error}</div> : null}
      {message ? <div className="border-b border-emerald-400/20 bg-emerald-500/10 px-6 py-3 text-xs text-emerald-200">{message}</div> : null}

      <div className="p-6">
        {loading && !rows.length ? (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" /> Reading the queue…
          </div>
        ) : rows.length ? (
          <>
            <ul className="space-y-2.5">
              {rows.map((claim) => (
                <Row key={claim.id} claim={claim} checked={selected.has(claim.id)} onToggle={toggle} />
              ))}
            </ul>
            {data?.more ? (
              <div className="mt-5 flex items-center justify-between text-xs text-slate-400">
                <button
                  type="button"
                  onClick={() => setOffset(Math.max(offset - 50, 0))}
                  disabled={offset === 0}
                  className="rounded-lg border border-white/10 px-3 py-1.5 hover:border-white/25 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  type="button"
                  onClick={() => setOffset(offset + 50)}
                  className="rounded-lg border border-white/10 px-3 py-1.5 hover:border-white/25"
                >
                  Next 50
                </button>
              </div>
            ) : null}
          </>
        ) : (
          <div className="rounded-xl border border-dashed border-white/10 p-10 text-center">
            <FileText className="mx-auto mb-3 h-8 w-8 text-slate-600" />
            <div className="text-sm font-semibold text-slate-300">Nothing waiting here</div>
            <p className="mt-1 text-xs text-slate-500">
              Either the queue is clear for this filter, or no document has been pasted yet.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
