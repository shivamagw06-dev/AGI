import { useEffect, useState } from 'react';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, EmptyState, InsightCard } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import { getValidationDashboard, listResearchRuns } from '@/lib/intelligenceApi';

function BarRow({ label, value }) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0));
  return (
    <div>
      <div className="mb-1 flex justify-between text-[12px] text-[var(--beta-muted)]">
        <span>{label}</span>
        <span>{value == null ? '—' : `${Number(value).toFixed(0)}%`}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#eef1f6]">
        <div className="h-full rounded-full bg-[var(--beta-navy)]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function ValidationStory() {
  const { isExplain } = useBetaDepth();
  const [dash, setDash] = useState(null);
  const [runs, setRuns] = useState([]);

  useEffect(() => {
    let active = true;
    getValidationDashboard()
      .then((data) => active && setDash(data))
      .catch(() => active && setDash(null));
    listResearchRuns({ limit: '8' })
      .then((data) => active && setRuns(Array.isArray(data) ? data : data?.runs || []))
      .catch(() => active && setRuns([]));
    return () => {
      active = false;
    };
  }, []);

  const hit = dash?.forecast_hit_rate?.overall ?? dash?.forecast_accuracy?.mean;
  const scored = dash?.scored_forecasts ?? dash?.scored_predictions;
  const pending = dash?.pending_predictions;

  return (
    <SurfaceChrome>
      <div className="beta-story-stack">
        <header>
          <p className="beta-kicker">Validation</p>
          <h1 className="beta-h1 mt-2">Charts only. Trust the track record.</h1>
        </header>

        <StorySection title="Forecast accuracy">
          {dash ? (
            <div className="beta-card space-y-4">
              <BarRow label="Hit / accuracy" value={hit != null ? Number(hit) * (hit <= 1 ? 100 : 1) : null} />
              <p className="beta-caption">
                Scored {scored ?? '—'} · Pending {pending ?? '—'}
              </p>
            </div>
          ) : (
            <EmptyState title="Validation API unavailable" detail="When Validation analytics is enabled, accuracy charts render here — never fabricated." />
          )}
        </StorySection>

        {!isExplain && (
          <>
            <StorySection title="Confidence calibration">
              {(dash?.confidence_calibration || []).length ? (
                <div className="beta-card space-y-3">
                  {dash.confidence_calibration.slice(0, 5).map((bin) => (
                    <BarRow
                      key={bin.bin_label}
                      label={bin.bin_label}
                      value={bin.hit_rate != null ? Number(bin.hit_rate) * 100 : bin.mean_accuracy != null ? Number(bin.mean_accuracy) * 100 : null}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState title="No calibration bins yet" />
              )}
            </StorySection>

            <StorySection title="Research evolution">
              {(dash?.research_evolution || runs).length ? (
                <div className="space-y-3">
                  {(dash?.research_evolution || runs).slice(0, 5).map((row) => (
                    <InsightCard
                      key={row.run_id || row.id}
                      title={row.title || row.desk || row.run_id}
                      body={row.query || row.note || row.recommendation}
                      meta={row.created_at ? new Date(row.created_at).toLocaleString('en-IN') : row.status}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState title="No evolution history yet" />
              )}
            </StorySection>
          </>
        )}
      </div>
    </SurfaceChrome>
  );
}
