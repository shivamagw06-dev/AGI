import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, FileText, Loader2, RefreshCw, Upload, XCircle } from 'lucide-react';
import { getPublicationClaims, reviewPublicationClaims, uploadPublication } from '@/lib/institutionalHoldingsApi';

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

/**
 * Short names for the filter tiles.
 *
 * The tiles used the full question and "WHAT DOES MANAGEMENT EXPECT NEXT?"
 * made one tile three times the width of its neighbours, which wrapped the
 * row and left a single tile alone underneath. The full question still
 * appears on every claim, where there is room for it and where it is the
 * thing being answered.
 */
const SLOT_SHORT = {
  what_happened: 'Happened',
  why: 'Why',
  how: 'Response',
  how_much: 'How much',
  what_changed: 'Changed',
  expectations: 'Expects',
  risks: 'Risks',
  holding: 'Holdings',
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

/**
 * A disclosed holding, as columns rather than as prose.
 *
 * These rows came out of a table and reading one back as a sentence gives
 * "ITOCHU Corporation 10.1% 4,165 8,886 181", which is accurate and
 * unreadable. The figures carry the scale the document declared and nothing
 * multiplies them out, so the unit travels with every number.
 */
function HoldingFigures({ claim }) {
  const figure = (value) => (value === null || value === undefined
    ? '—' : `${Number(value).toLocaleString('en-US')}${claim.unit ? ` ${claim.unit}` : ''}`);
  const cells = [
    ['Owned', claim.percent_owned === null || claim.percent_owned === undefined
      ? '—' : `${claim.percent_owned}%`],
    ['Cost', figure(claim.cost_basis)],
    ['Market value', figure(claim.market_value)],
    ['Dividends', figure(claim.dividends)],
  ];
  return (
    <>
      <div className="text-[13.5px] font-semibold leading-6 text-slate-100">{claim.issuer}</div>
      <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-4">
        {cells.map(([label, value]) => (
          <div key={label}>
            <dt className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">{label}</dt>
            <dd className="text-[12.5px] tabular-nums text-slate-200">{value}</dd>
          </div>
        ))}
      </dl>
      {/* The line it came from, kept small. A reviewer approves the figures
          against the text that produced them, and no declared unit means
          nothing downstream may scale them. */}
      <p className="mt-2 text-[10.5px] leading-4 text-slate-500">{claim.source_excerpt}</p>
      {!claim.unit ? (
        <p className="mt-1 text-[10.5px] text-amber-300/80">
          No unit declared in the document — these figures are as written.
        </p>
      ) : null}
    </>
  );
}

function Row({ claim, checked, onToggle }) {
  const move = changeLabel(claim.change);
  const holding = claim.kind === 'disclosed_holding';
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
              judging it is the only thing this screen is for. A holdings row
              is not a sentence and gets its columns instead. */}
          {holding
            ? <HoldingFigures claim={claim} />
            : <p className="text-[13.5px] leading-6 text-slate-100">{claim.source_excerpt}</p>}

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
            {claim.issuer && !holding ? <span className="text-slate-400">{claim.issuer}</span> : null}
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


/**
 * Paste a publication and extract it, without opening a shell.
 *
 * Until now the only way in was a CLI script on the server, which is why one
 * person could add a document and nobody else could.
 *
 * Two things the form insists on, both because they went wrong once.
 *
 * The manager is a list, not a text field. A hand-typed slug is a mismatch
 * waiting to happen, and Norges Bank's annual report was once stored as 177
 * things Berkshire said.
 *
 * Nothing is written until a dry run has been read. The button says "Extract"
 * first and reports what the document yields; only then does "Store" appear.
 * Committing 650 rows to a review queue sight-unseen is how the queue becomes
 * something nobody works.
 */
function UploadPanel({ managers, onStored }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState({ manager_slug: '', title: '', as_of_date: '', source_url: '' });
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [mismatch, setMismatch] = useState(null);

  const set = (key, value) => setDraft((current) => ({ ...current, [key]: value }));
  const ready = draft.manager_slug && draft.title.trim() && text.trim();

  const run = async (apply) => {
    setBusy(apply ? 'store' : 'extract');
    setError('');
    try {
      const result = await uploadPublication({
        ...draft, text, apply, force_manager: Boolean(mismatch) && apply,
      });
      if (apply) {
        setPreview(null);
        setText('');
        setMismatch(null);
        setOpen(false);
        onStored(result);
      } else {
        setPreview(result);
        setMismatch(null);
      }
    } catch (runError) {
      const message = runError.message || 'Could not read the document.';
      // The manager check is a refusal to guess, not a failure. It is offered
      // as an override rather than a dead end, because a letter whose author
      // genuinely does not name itself exists.
      if (/never mentions/.test(message)) setMismatch(message); else setError(message);
    } finally {
      setBusy('');
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-semibold text-cyan-200 hover:border-cyan-400/60"
      >
        <Upload className="h-3.5 w-3.5" /> Paste a publication
      </button>
    );
  }

  return (
    <div className="w-full rounded-xl border border-cyan-400/20 bg-white/[0.02] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-300">Paste a publication</div>
          <p className="mt-1 max-w-xl text-[11px] leading-5 text-slate-400">
            An annual report, a shareholder letter, anything the manager wrote. The text is
            read and discarded — only the extracted sentences are kept, each with the line it
            came from.
          </p>
        </div>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-slate-400 hover:text-slate-200">Close</button>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="block">
          <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Manager</span>
          <select
            value={draft.manager_slug}
            onChange={(event) => set('manager_slug', event.target.value)}
            className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0d222d] px-2.5 py-2 text-xs text-white outline-none focus:border-cyan-400"
          >
            <option value="">Choose…</option>
            {(managers || []).map((manager) => (
              <option key={manager.slug} value={manager.slug}>{manager.display_name}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Title</span>
          <input
            value={draft.title}
            onChange={(event) => set('title', event.target.value)}
            placeholder="2025 Annual Report"
            className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0d222d] px-2.5 py-2 text-xs text-white outline-none placeholder:text-slate-600 focus:border-cyan-400"
          />
        </label>
        <label className="block">
          <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Period</span>
          <input
            type="date"
            value={draft.as_of_date}
            onChange={(event) => set('as_of_date', event.target.value)}
            className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0d222d] px-2.5 py-2 text-xs text-white outline-none focus:border-cyan-400"
          />
        </label>
        <label className="block">
          <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Source URL</span>
          <input
            value={draft.source_url}
            onChange={(event) => set('source_url', event.target.value)}
            placeholder="Optional"
            className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#0d222d] px-2.5 py-2 text-xs text-white outline-none placeholder:text-slate-600 focus:border-cyan-400"
          />
        </label>
      </div>

      <textarea
        value={text}
        onChange={(event) => { setText(event.target.value); setPreview(null); }}
        rows={8}
        placeholder="Paste the document text here…"
        className="mt-3 w-full rounded-lg border border-white/10 bg-[#0d222d] p-3 font-mono text-[11px] leading-5 text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-400"
      />
      <div className="mt-1.5 text-[10.5px] text-slate-500">
        {text.length ? `${text.length.toLocaleString()} characters` : 'Nothing pasted yet'}
      </div>

      {error ? <div className="mt-3 rounded-lg border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">{error}</div> : null}
      {mismatch ? (
        <div className="mt-3 rounded-lg border border-amber-400/25 bg-amber-500/10 px-3 py-2 text-[11px] leading-5 text-amber-200">
          {mismatch}
          <div className="mt-1.5 text-amber-200/70">
            Check the manager and the document. If the author genuinely does not name itself,
            Store will proceed anyway.
          </div>
        </div>
      ) : null}

      {preview ? (
        <div className="mt-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <div className="text-[11px] text-slate-300">
            <span className="font-semibold text-white">{preview.manager}</span>
            {' · '}{preview.characters.toLocaleString()} characters
            {' · '}{preview.holdings} disclosed holding{preview.holdings === 1 ? '' : 's'}
            {' · '}{preview.claims} claim{preview.claims === 1 ? '' : 's'}
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[10.5px]">
            {preview.steps.map((step) => (
              <span key={step.slot} className={step.extractable ? 'text-slate-400' : 'text-slate-600'}>
                {SLOT_SHORT[step.slot] || step.slot}{' '}
                <span className="tabular-nums text-slate-200">
                  {step.extractable ? step.found : 'n/a'}
                </span>
              </span>
            ))}
          </div>
          {/* Nothing is stored yet. The counts above are what Store would put
              into the queue. */}
          <div className="mt-2 text-[10.5px] text-slate-500">Nothing has been written yet.</div>
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => run(false)}
          disabled={!ready || Boolean(busy)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-slate-200 hover:border-cyan-400/40 disabled:opacity-40"
        >
          {busy === 'extract' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          Extract
        </button>
        {/* Only after a dry run has been read. */}
        <button
          type="button"
          onClick={() => run(true)}
          disabled={!ready || !preview || Boolean(busy)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:border-emerald-400/60 disabled:opacity-40"
        >
          {busy === 'store' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          Store {preview ? `${preview.claims + preview.holdings} row${preview.claims + preview.holdings === 1 ? '' : 's'}` : ''}
        </button>
        {!preview ? <span className="text-[10.5px] text-slate-500">Extract first — Store stays disabled until you have seen what the document yields.</span> : null}
      </div>
    </div>
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
  const managers = data?.managers || [];
  const pendingTotal = useMemo(
    () => counts.reduce((total, entry) => total + entry.pending, 0), [counts],
  );
  const approvedTotal = useMemo(
    () => counts.reduce((total, entry) => total + entry.approved, 0), [counts],
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
          <div className="flex items-center gap-2">
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
        </div>

        <div className="mt-4">
          <UploadPanel
            managers={managers}
            onStored={(result) => {
              setMessage(`Stored ${result.claims} claim(s) and ${result.holdings} holding(s) for `
                + `${result.manager}. ${result.approved_by_rule} approved by rule, `
                + `${result.pending} pending.`);
              setOffset(0);
              load(0);
            }}
          />
        </div>

        {counts.length ? (
          <div className="mt-5 flex flex-wrap gap-2">
            {/* Clicking a step filters to it. The counts are the whole queue,
                not this page, so the reviewer can see what is left. */}
            <button
              type="button"
              onClick={() => { setSlot(''); setOffset(0); }}
              className={`min-w-[8.5rem] rounded-xl border px-3 py-2 text-left transition ${slot === ''
                ? 'border-cyan-400/40 bg-cyan-400/[0.08]' : 'border-white/10 bg-white/[0.03] hover:border-white/20'}`}
            >
              <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">All steps</div>
              <div className="mt-0.5 text-lg font-semibold tabular-nums text-white">{pendingTotal}</div>
              {/* A third line so this tile is the same height as the others.
                  Without it, it sat visibly short at the start of the row. */}
              <div className="text-[10px] text-slate-500">{approvedTotal} approved</div>
            </button>
            {counts.filter((entry) => entry.pending > 0).map((entry) => (
              <button
                key={entry.slot}
                type="button"
                onClick={() => { setSlot(entry.slot); setOffset(0); }}
                className={`min-w-[8.5rem] rounded-xl border px-3 py-2 text-left transition ${slot === entry.slot
                  ? 'border-cyan-400/40 bg-cyan-400/[0.08]' : 'border-white/10 bg-white/[0.03] hover:border-white/20'}`}
              >
                <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                  {SLOT_SHORT[entry.slot] || entry.slot}
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
