import React from 'react';
import { fetchLive, fetchUniverse } from '@/lib/indiaAiApi';

/**
 * India AI Intelligence.
 *
 * The page is built around a universe that is deliberately incomplete, and it
 * says so at the top rather than in a footnote. A partial, evidence-qualified
 * universe that shows its evidence is more credible than a full one that
 * cannot say why anything is in it - so the admission reason, the document it
 * came from and the excerpt are first-class content here, not a tooltip.
 *
 * Every number on this page can be absent, and absence is rendered as the
 * reason for it. A basket that cannot be priced says which members are
 * missing; a company with no volume baseline says NO_BASELINE; an empty
 * sub-layer says nothing was disclosed beyond intent. None of them render as
 * a zero, because a zero is a claim.
 */

const LAYER_LABEL = {
  power: 'Power',
  data_centre: 'Data Centre',
  semiconductor: 'Semiconductor',
};

const SUB_LAYER_LABEL = {
  generation: 'Generation', transmission: 'Transmission', equipment: 'Equipment',
  developer: 'Developer', operator: 'Operator', hardware: 'Hardware',
  osat: 'OSAT', materials: 'Materials',
};

const ALL_SUB_LAYERS = [
  ['power', 'generation'], ['power', 'transmission'], ['power', 'equipment'],
  ['data_centre', 'developer'], ['data_centre', 'operator'], ['data_centre', 'hardware'],
  ['semiconductor', 'osat'], ['semiconductor', 'materials'], ['semiconductor', 'hardware'],
];

const KIND_LABEL = {
  order: 'Signed order', capex: 'Committed capex', operating: 'Operating disclosure',
  partnership: 'Partnership', language: 'Transcript language', news: 'Press item',
};

const pp = (value) => {
  if (!Number.isFinite(Number(value))) return '—';
  const n = Number(value);
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}pp`;
};

const pct = (value) => {
  if (!Number.isFinite(Number(value))) return '—';
  const n = Number(value) * 100;
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
};

const tone = (value) => {
  const n = Number(value);
  if (!Number.isFinite(n) || n === 0) return 'text-[#5d6b76]';
  return n > 0 ? 'text-[#17633a]' : 'text-[#a13a2b]';
};

function Card({ title, right, children, className = '' }) {
  return (
    <section className={`overflow-hidden rounded-2xl border border-[#d8d5cc] bg-white ${className}`}>
      <header className="flex items-baseline justify-between border-b border-[#e4e1da] px-4 py-2.5">
        <h2 className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#91a8b7]">{title}</h2>
        {right}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

/**
 * The refusal, rendered as itself.
 *
 * The index has three refusal states and each means something different. A
 * page that renders all of them as "—" throws away the only information
 * available at the moment it is most needed.
 */
function Refusal({ index }) {
  if (!index) return <p className="text-sm text-[#5d6b76]">No basket computed yet.</p>;
  const detail = {
    insufficient_coverage: 'Too few members priced to compute a basket.',
    missing_float_data: 'Cap weighting needs free-float shares, which the universe does not carry yet.',
  }[index.status] || 'The basket is not computable right now.';
  return (
    <div className="space-y-2">
      <p className="font-mono text-xs uppercase tracking-wider text-[#805d1f]">{index.status}</p>
      <p className="text-sm text-[#102433]">{detail}</p>
      {index.reason ? <p className="text-xs text-[#727c84]">{index.reason}</p> : null}
      {index.missing?.length ? (
        <p className="text-xs text-[#727c84]">
          Not priced: <span className="font-mono">{index.missing.join(', ')}</span>
        </p>
      ) : null}
    </div>
  );
}

function BasketHeader({ live }) {
  const index = live?.index;
  const ok = index?.status === 'ok';
  const quality = live?.quality;
  return (
    <Card
      title="AGI AI Enablers · equal-weighted"
      right={
        <span className="flex items-center gap-2 text-[11px] text-[#727c84]">
          <span className={`h-1.5 w-1.5 rounded-full ${quality?.live ? 'bg-[#17633a]' : 'bg-[#c3ccd2]'}`} />
          {quality?.live ? `${quality.live} live` : 'no live prices'}
          {quality?.last_good ? ` · ${quality.last_good} last-good` : ''}
        </span>
      }
    >
      {ok ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-[#727c84]">Basket today</p>
            <p className={`mt-1 text-2xl font-semibold tabular-nums ${tone(index.return_pp)}`}>{pp(index.return_pp)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-[#727c84]">vs Nifty 50</p>
            <p className={`mt-1 text-2xl font-semibold tabular-nums ${tone(index.relative?.excess_pp)}`}>
              {index.relative ? pp(index.relative.excess_pp) : '—'}
            </p>
            {!index.relative ? <p className="text-[10px] text-[#91a8b7]">benchmark not priced</p> : null}
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-[#727c84]">Breadth</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-[#102433]">
              {index.breadth ? `${index.breadth.advancing}/${index.priced}` : '—'}
            </p>
            <p className="text-[10px] text-[#91a8b7]">advancing</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-[#727c84]">Coverage</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-[#102433]">
              {Number.isFinite(index.coverage) ? `${Math.round(index.coverage * 100)}%` : '—'}
            </p>
            <p className="text-[10px] text-[#91a8b7]">{index.priced} of {index.total} priced</p>
          </div>
        </div>
      ) : (
        <Refusal index={index} />
      )}
    </Card>
  );
}

function LayerPerformance({ live }) {
  const index = live?.index;
  const rows = index?.contributions?.byLayer || [];
  const subRows = index?.contributions?.bySubLayer || [];
  if (index?.status !== 'ok' || !rows.length) {
    return <Card title="Layer performance"><p className="text-sm text-[#727c84]">Available when the basket is priced.</p></Card>;
  }
  const widest = Math.max(...rows.map((one) => Math.abs(one.contribution_pp)), 0.01);
  return (
    <Card title="Layer performance" right={<span className="text-[11px] text-[#727c84]">contribution, pp</span>}>
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.layer}>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-[#102433]">{LAYER_LABEL[row.layer] || row.layer}</span>
              <span className={`font-mono tabular-nums ${tone(row.contribution_pp)}`}>{pp(row.contribution_pp)}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-[#eeebe3]">
              <div
                className={`h-1.5 rounded-full ${row.contribution_pp >= 0 ? 'bg-[#17633a]' : 'bg-[#a13a2b]'}`}
                style={{ width: `${Math.max(2, (Math.abs(row.contribution_pp) / widest) * 100)}%` }}
              />
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 pl-2">
              {subRows.filter((one) => one.subLayer.startsWith(`${row.layer}/`)).map((one) => (
                <span key={one.subLayer} className="text-[11px] text-[#727c84]">
                  {SUB_LAYER_LABEL[one.subLayer.split('/')[1]] || one.subLayer}
                  <span className={`ml-1 font-mono tabular-nums ${tone(one.contribution_pp)}`}>{pp(one.contribution_pp)}</span>
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
      {index.subLayerResidual_ok === false ? (
        <p className="mt-3 border-t border-[#e4e1da] pt-2 text-[11px] text-[#805d1f]">
          Sub-layer contributions are short by {pp(index.subLayerResidual_pp)}
          {index.unclassified?.length ? `: ${index.unclassified.join(', ')} sits in no sub-layer.` : '.'}
        </p>
      ) : null}
    </Card>
  );
}

/** One admitted company, with the evidence that admitted it kept visible. */
function MemberRow({ member, live }) {
  const [open, setOpen] = React.useState(false);
  const contribution = live?.index?.contributions?.byName?.find((one) => one.symbol === member.symbol);
  const volume = live?.volumes?.[member.symbol];
  const priced = Boolean(contribution);
  return (
    <div className="border-b border-[#ece9e2] last:border-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-3 px-1 py-2.5 text-left hover:bg-[#f6f4ee]"
      >
        <span className="w-4 shrink-0 text-center text-xs text-[#91a8b7]">{open ? '−' : '+'}</span>
        <span className="w-28 shrink-0 font-mono text-sm text-[#102433]">{member.symbol}</span>
        <span className="min-w-0 flex-1 truncate text-sm text-[#5d6b76]">{member.name}</span>
        <span className="hidden w-44 shrink-0 text-[11px] text-[#727c84] sm:block">
          {LAYER_LABEL[member.layer]} · {member.subLayers.map((one) => SUB_LAYER_LABEL[one] || one).join(' + ')}
        </span>
        <span className={`w-20 shrink-0 text-right font-mono text-sm tabular-nums ${priced ? tone(contribution.return_pct) : 'text-[#91a8b7]'}`}>
          {priced ? pct(contribution.return_pct) : '—'}
        </span>
        <span className={`w-20 shrink-0 text-right font-mono text-xs tabular-nums ${priced ? tone(contribution.contribution_pp) : 'text-[#91a8b7]'}`}>
          {priced ? pp(contribution.contribution_pp) : ''}
        </span>
        <span className="hidden w-16 shrink-0 text-right font-mono text-xs tabular-nums text-[#727c84] sm:block">
          {volume?.ratio != null ? `${volume.ratio.toFixed(1)}×` : '—'}
        </span>
      </button>
      {open ? (
        <div className="space-y-3 bg-[#faf9f5] px-8 pb-4 pt-1">
          {!priced ? (
            <p className="text-[11px] text-[#805d1f]">Not priced right now — excluded from the basket.</p>
          ) : null}
          {volume && volume.ratio == null ? (
            <p className="text-[11px] text-[#727c84]">
              Volume ratio unavailable: <span className="font-mono">{volume.reason}</span>
            </p>
          ) : null}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-[#727c84]">Why this company is in the index</p>
            <ul className="mt-2 space-y-2">
              {member.admittedOn.map((evidence, i) => (
                <li key={i} className="border-l-2 border-[#9fc9ad] pl-3">
                  <p className="text-[11px] text-[#5d6b76]">
                    <span className="font-medium text-[#17633a]">{KIND_LABEL[evidence.kind] || evidence.kind}</span>
                    {' · '}{evidence.document}{evidence.date ? ` · ${evidence.date}` : ''}
                  </p>
                  <p className="mt-1 text-[13px] leading-relaxed text-[#102433]">“{evidence.excerpt}”</p>
                </li>
              ))}
            </ul>
          </div>
          <p className="text-[10px] text-[#91a8b7]">
            ISIN {member.isin} · admitted on {member.basis} evidence
            {member.reviewedBy ? ` · reviewed by ${member.reviewedBy}` : ' · not yet reviewed by an analyst'}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function AdmittedCompanies({ universe, live }) {
  const members = universe?.members || [];
  return (
    <Card
      title={`Admitted companies · ${members.length}`}
      right={<span className="hidden text-[10px] uppercase tracking-wider text-[#91a8b7] sm:block">day · contribution · volume</span>}
    >
      <p className="mb-2 text-[11px] text-[#727c84]">
        Each admitted on at least one hard, first-party disclosure. Expand a row for the filing.
      </p>
      <div>{members.map((member) => <MemberRow key={member.symbol} member={member} live={live} />)}</div>
    </Card>
  );
}

/** The candidates, and — the point of the panel — why each was refused. */
function Candidates({ universe }) {
  const candidates = universe?.candidates || [];
  const [open, setOpen] = React.useState(null);
  return (
    <Card title={`Candidates · ${candidates.length}`}>
      <p className="mb-3 text-[11px] text-[#727c84]">
        Found by the screen and not admitted. Soft evidence alone never admits a company.
      </p>
      <div className="space-y-1.5">
        {candidates.map((candidate) => (
          <div key={candidate.symbol} className="rounded border border-[#e4e1da] bg-[#faf9f5]">
            <button
              type="button"
              onClick={() => setOpen(open === candidate.symbol ? null : candidate.symbol)}
              className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-[#f6f4ee]"
            >
              <span className="w-24 shrink-0 font-mono text-xs text-[#102433]">{candidate.symbol}</span>
              <span className="min-w-0 flex-1 truncate text-xs text-[#727c84]">{candidate.name}</span>
              <span className="shrink-0 rounded bg-[#eeebe3] px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-[#5d6b76]">
                {candidate.suggestedSubLayers?.length
                  ? `${LAYER_LABEL[candidate.suggestedLayer]} · ${candidate.suggestedSubLayers.map((o) => SUB_LAYER_LABEL[o] || o).join(', ')}`
                  : 'no sub-layer'}
              </span>
            </button>
            {open === candidate.symbol ? (
              <div className="space-y-2 border-t border-[#e4e1da] px-3 py-2.5">
                <p className="text-[13px] leading-relaxed text-[#102433]">{candidate.note}</p>
                {candidate.evidence?.map((evidence, i) => (
                  <p key={i} className="border-l-2 border-[#d8d5cc] pl-3 text-[12px] leading-relaxed text-[#727c84]">
                    <span className="text-[#5d6b76]">{evidence.document}{evidence.date ? ` · ${evidence.date}` : ''}</span>
                    <br />“{evidence.excerpt}”
                  </p>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </Card>
  );
}

/** Every filing that admitted somebody, newest first. */
function EvidenceTrail({ universe }) {
  const rows = (universe?.members || []).flatMap((member) =>
    (member.admittedOn || []).map((evidence) => ({ ...evidence, symbol: member.symbol })));
  rows.sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
  return (
    <Card title="Evidence trail" right={<span className="text-[11px] text-[#727c84]">{rows.length} filings</span>}>
      <div className="space-y-2.5">
        {rows.map((row, i) => (
          <div key={i} className="flex gap-3 border-b border-[#ece9e2] pb-2.5 last:border-0 last:pb-0">
            <span className="w-20 shrink-0 font-mono text-[11px] text-[#727c84]">{row.date || '—'}</span>
            <div className="min-w-0">
              <p className="text-[11px]">
                <span className="font-mono text-[#102433]">{row.symbol}</span>
                <span className="text-[#91a8b7]"> · </span>
                <span className="text-[#17633a]">{KIND_LABEL[row.kind] || row.kind}</span>
                <span className="text-[#91a8b7]"> · {row.document}</span>
              </p>
              <p className="mt-0.5 line-clamp-2 text-[12px] leading-relaxed text-[#5d6b76]">“{row.excerpt}”</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/**
 * The empty sub-layers.
 *
 * On most products this panel would not exist. It is here because an empty
 * layer is a finding: India's semiconductor materials and fab-equipment names
 * disclose intent and not action, and showing the gap is more honest than a
 * taxonomy that quietly only ever renders seven of its nine boxes.
 */
function EmptyLayers({ universe }) {
  const filled = new Set();
  for (const member of universe?.members || []) {
    for (const sub of member.subLayers || []) filled.add(`${member.layer}/${sub}`);
  }
  const empty = ALL_SUB_LAYERS.filter(([layer, sub]) => !filled.has(`${layer}/${sub}`));
  return (
    <Card title="Empty layers" right={<span className="text-[11px] text-[#727c84]">{empty.length} of {ALL_SUB_LAYERS.length}</span>}>
      {empty.length === 0 ? (
        <p className="text-sm text-[#5d6b76]">Every sub-layer has at least one admitted company.</p>
      ) : (
        <>
          <p className="mb-3 text-[11px] leading-relaxed text-[#727c84]">
            These are empty because nothing was disclosed beyond intent — not because the screen
            has not looked. Every company found in them talks about the opportunity and reports
            no order, no committed capex and no segment revenue. Admitting one would mean
            admitting on intent.
          </p>
          <div className="space-y-1.5">
            {empty.map(([layer, sub]) => (
              <div key={`${layer}/${sub}`} className="flex items-center gap-3 rounded border border-dashed border-[#cdc6b6] px-3 py-2">
                <span className="text-xs text-[#5d6b76]">
                  {LAYER_LABEL[layer]} <span className="text-[#91a8b7]">→</span> {SUB_LAYER_LABEL[sub] || sub}
                </span>
                <span className="ml-auto text-[10px] uppercase tracking-wider text-[#91a8b7]">pre-revenue</span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}

export default function IndiaAiIntelligencePage() {
  const [universe, setUniverse] = React.useState(null);
  const [live, setLive] = React.useState(null);
  const [liveError, setLiveError] = React.useState(null);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;
    fetchUniverse()
      .then((payload) => { if (!cancelled) setUniverse(payload); })
      .catch((err) => { if (!cancelled) setError(String(err?.message || err)); });
    return () => { cancelled = true; };
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    const load = () => fetchLive()
      .then((payload) => { if (!cancelled) { setLive(payload); setLiveError(null); } })
      .catch((err) => { if (!cancelled) setLiveError(String(err?.message || err)); });
    load();
    const timer = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16">
        <p className="text-sm text-[#a13a2b]">Could not load the universe: {error}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f3f0e8] text-[#102433]">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
        <section className="relative mb-5 overflow-hidden rounded-2xl bg-[#092536] text-white">
          <div className="absolute -right-32 -top-32 h-[420px] w-[420px] rounded-full bg-[#b98047]/15 blur-3xl" />
          <div className="relative px-5 py-6 sm:px-8 sm:py-8">
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#ddb77e]">
              Research › Themes › India AI Infrastructure
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight sm:text-4xl">
              India AI Intelligence
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-[#bfd0da]">
              The listed companies building India&rsquo;s AI infrastructure — power, data centres and
              silicon — admitted to AGI&rsquo;s own basket only on first-party disclosure.
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-[#ddb77e]/40 bg-[#ddb77e]/10 px-3 py-1 text-[11px] font-semibold text-[#ddb77e]">
                Universe status: {universe?.status === 'partial' ? 'Partial' : universe?.status || '—'} · Evidence-qualified
              </span>
              {universe?.version ? (
                <span className="text-[11px] text-[#9fb3bf]">screen run {universe.version}</span>
              ) : null}
            </div>
            {universe?.note ? (
              <p className="mt-4 max-w-3xl border-l-2 border-white/20 pl-4 text-[11px] leading-6 text-[#9fb3bf]">
                {universe.note}
              </p>
            ) : null}
          </div>
        </section>

        {liveError ? (
          <p className="mb-4 rounded-xl border border-[#d7c39c] bg-[#fff7e7] px-4 py-2.5 text-[12px] text-[#805d1f]">
            Live prices unavailable: {liveError}
          </p>
        ) : null}

        <div className="space-y-4">
          <BasketHeader live={live} />
          <div className="grid gap-4 lg:grid-cols-2">
            <LayerPerformance live={live} />
            <EmptyLayers universe={universe} />
          </div>
          <AdmittedCompanies universe={universe} live={live} />
          <div className="grid gap-4 lg:grid-cols-2">
            <Candidates universe={universe} />
            <EvidenceTrail universe={universe} />
          </div>
        </div>

        <footer className="mt-8 border-t border-[#e4e1da] pt-4 text-[11px] leading-relaxed text-[#91a8b7]">
          <p>
            AGI&rsquo;s own screen over public filings. Admission requires at least one hard,
            first-party disclosure — a signed order, committed capex or an operating figure.
            Partnerships, memoranda and sector forecasts do not admit a company. Prices from
            Upstox; a basket below its coverage floor reports coverage instead of a level.
          </p>
        </footer>
      </div>
    </div>
  );
}
