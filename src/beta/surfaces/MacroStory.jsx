import { Link } from 'react-router-dom';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, EmptyState } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import useMarketDashboard from '@/hooks/useMarketDashboard';

export default function MacroStory() {
  const { isExplain } = useBetaDepth();
  const dash = useMarketDashboard();

  const chips = [
    { label: 'India', value: dash.pulse ? 'In focus' : '—', tone: 'pos' },
    { label: 'Breadth', value: dash.breadth?.advancers != null ? 'Watch' : '—', tone: 'warn' },
    { label: 'Leaders', value: (dash.gainers || []).length ? 'Active' : '—', tone: 'pos' },
    { label: 'Pressure', value: (dash.losers || []).length ? 'Active' : '—', tone: 'neg' },
    { label: 'Oil / Macro', value: 'See Macro page', tone: 'warn' },
    { label: 'Rates', value: 'See Macro page', tone: 'warn' },
  ];

  return (
    <SurfaceChrome>
      <div className="beta-story-stack">
        <header>
          <p className="beta-kicker">Macro Dashboard</p>
          <h1 className="beta-h1 mt-2">Weather for markets</h1>
          <p className="mt-3 max-w-xl text-[var(--beta-ink-soft)]">
            Apple Weather energy — clear states, not indicator dumps.
          </p>
        </header>

        <StorySection>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {chips.slice(0, isExplain ? 4 : 6).map((c) => (
              <div key={c.label} className="beta-card text-center">
                <p className="beta-caption">{c.label}</p>
                <p className="mt-3 font-[family-name:var(--beta-serif)] text-2xl font-semibold text-[var(--beta-navy)]">
                  {c.value}
                </p>
                <span className={`beta-chip beta-chip-${c.tone} mt-3`}>{c.tone === 'pos' ? 'Constructive' : c.tone === 'neg' ? 'Watch' : 'Neutral'}</span>
              </div>
            ))}
          </div>
          {!dash.pulse && <EmptyState title="Macro feed quiet" detail="Chips fill as market intelligence / macro briefings arrive." />}
        </StorySection>

        <Link to="/macro-intelligence" className="beta-btn inline-flex">
          Open Macro Intelligence →
        </Link>
      </div>
    </SurfaceChrome>
  );
}
