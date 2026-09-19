import { useEffect, useState } from 'react';
import { Clock3, Eye, Sparkles, Sunrise, Sunset } from 'lucide-react';

const TABS = [
  { id: 'preMarket', label: 'Pre-Market', icon: Sunrise },
  { id: 'midDay', label: '12 PM', icon: Clock3 },
  { id: 'postMarket', label: 'Market Close', icon: Sunset },
];

function tone(value = '') {
  const text = String(value).toLowerCase();
  if (/bearish|negative|weak/i.test(text)) return 'border-[#f7c5c0] bg-[#fff1f0] text-[#b42318]';
  if (/bullish|positive|strong|leading/i.test(text)) return 'border-[#b7ebcc] bg-[#ecfdf3] text-[#087443]';
  return 'border-[#f4d99d] bg-[#fff8e8] text-[#966a00]';
}

function Pill({ children }) {
  return <span className={`inline-flex w-fit border px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${tone(children)}`}>{children}</span>;
}

export default function InstitutionalIntelligenceLayer({ briefing, loading }) {
  const notes = briefing?.intelligence?.sessionNotes || {};
  const [active, setActive] = useState(notes.active || 'preMarket');

  useEffect(() => {
    if (notes.active) setActive(notes.active);
  }, [notes.active]);

  const note = notes[active] || notes.preMarket || briefing?.intelligence?.activeSessionNote;
  const mood = note?.outlook || briefing?.intelligence?.mood?.label || 'Neutral';

  if (loading) {
    return (
      <section className="mt-8 space-y-4" aria-label="Loading session notes">
        <div className="h-80 animate-pulse border border-[#dde1e6] bg-white" />
      </section>
    );
  }

  if (!note) {
    return (
      <section className="mt-8 border border-dashed border-[#cbd2da] bg-white p-8 text-sm text-[#667085]">
        Session notes will appear after the next briefing refresh.
      </section>
    );
  }

  return (
    <section className="mt-8" aria-label="AGI session notes">
      <article className="border border-[#cbd9e8] bg-white">
        <div className="border-b border-[#edf0f2] px-5 py-5 sm:px-7">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-2">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[#274c77]" />
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#274c77]">AGI Strategy Desk</p>
                <h2 className="mt-1 text-2xl font-bold tracking-tight text-[#18202b]">Daily Market Notes</h2>
                <p className="mt-1 text-xs text-[#737982]">Mint-style Pre-Market, 12 PM and Market Close notes. Direction only — no live prices.</p>
              </div>
            </div>
            <div className="text-right">
              <Pill>{mood}</Pill>
              <p className="mt-2 flex items-center justify-end gap-1 text-[11px] text-[#737982]">
                <Clock3 className="h-3.5 w-3.5" />
                {briefing?.updatedAt ? new Date(briefing.updatedAt).toLocaleString('en-IN') : 'Awaiting refresh'}
              </p>
            </div>
          </div>

          <div className="mt-5 flex gap-2 overflow-x-auto">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const selected = active === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActive(tab.id)}
                  className={`inline-flex shrink-0 items-center gap-2 border px-3 py-2 text-xs font-bold transition-colors ${selected ? 'border-[#274c77] bg-[#274c77] text-white' : 'border-[#d9dee5] bg-white text-[#59616d] hover:border-[#98a2b3]'}`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {tab.label}
                  {notes.active === tab.id && <span className={`rounded-full px-1.5 py-0.5 text-[9px] uppercase ${selected ? 'bg-white/20' : 'bg-[#edf3fa] text-[#274c77]'}`}>Live</span>}
                </button>
              );
            })}
          </div>
        </div>

        <div className="px-5 py-6 sm:px-7">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-xl font-bold text-[#18202b]">{note.title}</h3>
            <Pill>{note.outlook || mood}</Pill>
            {note.confidence != null && (
              <span className="text-[11px] font-semibold text-[#737982]">Confidence {note.confidence}%</span>
            )}
          </div>
          <p className="mt-1 text-xs font-medium uppercase tracking-[0.12em] text-[#737982]">{note.subtitle}</p>

          <p className="mt-5 text-base font-semibold leading-7 text-[#18202b]">{note.lead}</p>
          <p className="mt-4 text-sm leading-7 text-[#374151]">{note.body}</p>

          <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2">
            <div className="border border-[#edf0f2] bg-[#fafbfd] p-4">
              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#274c77]">Why AGI sees it this way</p>
              <ul className="mt-3 space-y-2">
                {(note.why || []).map((item) => (
                  <li key={item} className="text-sm leading-relaxed text-[#4b5563]">• {item}</li>
                ))}
              </ul>
            </div>
            <div className="border border-[#edf0f2] bg-[#fafbfd] p-4">
              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#274c77]">What institutions are watching</p>
              <ul className="mt-3 space-y-2">
                {(note.watch || []).map((item) => (
                  <li key={item} className="flex gap-2 text-sm leading-relaxed text-[#4b5563]">
                    <Eye className="mt-0.5 h-4 w-4 shrink-0 text-[#274c77]" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </article>

      <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        {(briefing?.snapshot?.indices || []).map((index) => (
          <div key={index.name} className="border border-[#dde1e6] bg-white p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">{index.name}</p>
            <p className={`mt-2 inline-flex border px-2 py-1 text-xs font-bold uppercase ${tone(index.direction)}`}>{index.direction}</p>
          </div>
        ))}
        {briefing?.snapshot?.breadth?.label && (
          <div className="border border-[#dde1e6] bg-white p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Market Breadth</p>
            <p className={`mt-2 inline-flex border px-2 py-1 text-xs font-bold uppercase ${tone(briefing.snapshot.breadth.label)}`}>{briefing.snapshot.breadth.label}</p>
          </div>
        )}
      </div>
    </section>
  );
}
