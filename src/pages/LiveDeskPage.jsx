import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';

import useLiveDesk from '@/hooks/useLiveDesk';
import { buildIntelligence } from '@/lib/liveDeskIntelligence';

import BloombergLivePlayer from '@/components/LiveDesk/BloombergLivePlayer';
import CrossAssetMonitor from '@/components/LiveDesk/CrossAssetMonitor';
import EvidenceDrawer from '@/components/LiveDesk/EvidenceDrawer';
import KeyEvents from '@/components/LiveDesk/KeyEvents';
import LiveAlphaPreview from '@/components/LiveDesk/LiveAlphaPreview';
import LiveIntelligenceTimeline from '@/components/LiveDesk/LiveIntelligenceTimeline';
import MarketAlertCard from '@/components/LiveDesk/MarketAlertCard';
import MarketDriverPanel from '@/components/LiveDesk/MarketDriverPanel';
import MarketIntelligenceFeed from '@/components/LiveDesk/MarketIntelligenceFeed';
import MarketPulse from '@/components/LiveDesk/MarketPulse';
import MarketRegimeCard from '@/components/LiveDesk/MarketRegimeCard';
import RelatedResearch from '@/components/LiveDesk/RelatedResearch';
import { istTime } from '@/components/LiveDesk/Primitives';

import './liveDesk.css';

/**
 * AGI Live Desk.
 *
 * Bloomberg's broadcast is one source on this page, not the page. The layout
 * gives the video roughly 65% of the top row and AGI's own intelligence the
 * rest, and every panel below the fold is AGI's: what is moving, why, what is
 * scheduled, what needs attention, and where to research it.
 *
 * Nothing on this page is hardcoded market data. Where a source is
 * unavailable the panel says so - see useLiveDesk and liveDeskIntelligence,
 * both of which return empty rather than plausible.
 */
export default function LiveDeskPage() {
  const desk = useLiveDesk();
  const [evidence, setEvidence] = useState(null);
  // 'full' | 'pip' | 'closed'. The stream never follows the reader off this
  // route: the component unmounts with the page.
  const [player, setPlayer] = useState('full');

  const intelligence = useMemo(
    () => buildIntelligence(desk.snapshot, desk.themes),
    [desk.snapshot, desk.themes]
  );

  const marketError = desk.errors?.home || null;
  const refreshLabel = desk.updatedAt ? istTime(desk.updatedAt) : null;

  return (
    <div className="ld-root">
      <Helmet>
        <title>Live Financial Markets &amp; Intelligence | Agarwal Global Investments</title>
        <meta
          name="description"
          content="Live financial television, cross-asset market monitoring, macro events and AGI market intelligence in one institutional research workspace."
        />
      </Helmet>

      <div className="ld-shell">
        <header className="ld-head">
          <div className="ld-head-row">
            <div>
              <h1 className="ld-title">AGI Live Desk</h1>
              <p className="ld-sub">Live markets, events and intelligence</p>
            </div>
            <div className="ld-head-meta">
              <span className="ld-live-dot">Live</span>
              <span className={desk.stale ? 'ld-refresh ld-stale' : 'ld-refresh'}>
                {refreshLabel
                  ? `${desk.stale ? 'Data delayed · ' : 'Last intelligence refresh: '}${refreshLabel}`
                  : 'Refresh status unavailable'}
              </span>
            </div>
          </div>
        </header>

        <div className="ld-main">
          <div>
            {player === 'full' ? (
              <BloombergLivePlayer onMinimize={() => setPlayer('pip')} />
            ) : (
              <section className="ld-card">
                <div className="ld-card-head">
                  <span className="ld-label">Live Financial TV</span>
                  <button
                    type="button"
                    className="ld-evidence"
                    style={{ marginTop: 0 }}
                    onClick={() => setPlayer('full')}
                  >
                    Restore player
                  </button>
                </div>
                <div className="ld-state">
                  {player === 'pip'
                    ? 'Bloomberg Live is playing in the minimised player.'
                    : 'Bloomberg Live is closed.'}
                </div>
              </section>
            )}
          </div>

          <MarketIntelligenceFeed
            items={intelligence}
            loading={desk.loading}
            error={marketError}
            updatedAt={desk.updatedAt}
            onEvidence={setEvidence}
          />
        </div>

        <div style={{ marginTop: '1rem' }}>
          <MarketPulse
            items={desk.snapshot}
            loading={desk.loading}
            error={marketError}
            stale={desk.stale}
          />
        </div>

        <div style={{ marginTop: '1rem' }}>
          <MarketAlertCard alerts={desk.alerts} loading={desk.loading} />
        </div>

        <div className="ld-grid-2">
          <MarketDriverPanel drivers={desk.drivers} loading={desk.loading} error={marketError} />
          <KeyEvents events={desk.events} loading={desk.loading} error={marketError} />
        </div>

        <div className="ld-grid-2">
          <CrossAssetMonitor rows={desk.crossAsset} loading={desk.loading} error={marketError} />
          <MarketRegimeCard regime={desk.regime} loading={desk.loading} error={desk.errors?.regime} />
        </div>

        <div className="ld-grid-2">
          <LiveIntelligenceTimeline
            items={intelligence}
            loading={desk.loading}
            error={marketError}
          />
          <div style={{ display: 'grid', gap: '1rem', alignContent: 'start' }}>
            <LiveAlphaPreview
              liveAlpha={desk.liveAlpha}
              loading={desk.loading}
              error={desk.errors?.liveAlpha}
            />
            <RelatedResearch
              research={desk.research}
              loading={desk.loading}
              error={marketError}
            />
          </div>
        </div>

        <footer className="ld-foot">
          For research and informational purposes only. Third-party video content is provided
          through its official embedded player and remains the property of its respective
          publisher. AGI does not control or endorse third-party broadcasts.
        </footer>
      </div>

      {player === 'pip' ? (
        <BloombergLivePlayer
          pip
          onRestore={() => setPlayer('full')}
          onClose={() => setPlayer('closed')}
        />
      ) : null}

      <EvidenceDrawer item={evidence} onClose={() => setEvidence(null)} />
    </div>
  );
}
