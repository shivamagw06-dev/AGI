import { useBetaDepth, DEPTH } from '@/beta/BetaDepthContext';

const OPTIONS = [
  { id: DEPTH.explain, label: 'Explain in 30s' },
  { id: DEPTH.research, label: 'Research Report' },
  { id: DEPTH.professional, label: 'Professional' },
];

export default function DepthSwitch() {
  const { depth, setDepth } = useBetaDepth();
  return (
    <div
      className="inline-flex rounded-full border border-[var(--beta-border-strong)] bg-white p-1"
      role="tablist"
      aria-label="Reading depth"
    >
      {OPTIONS.map((opt) => {
        const active = depth === opt.id;
        return (
          <button
            key={opt.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => setDepth(opt.id)}
            className={`rounded-full px-3 py-1.5 text-[11px] font-semibold transition-colors ${
              active
                ? 'bg-[var(--beta-navy)] text-white'
                : 'text-[var(--beta-muted)] hover:text-[var(--beta-ink)]'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
