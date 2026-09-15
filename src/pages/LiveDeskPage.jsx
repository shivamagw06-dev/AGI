import { useCallback, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';

import useLiveDesk from '@/hooks/useLiveDesk';
import { BROADCASTS } from '@/lib/liveDeskConfig';
import {
  GLOBAL, INDIA, buildCrossMarket, buildDrivers, buildIntelligence,
} from '@/lib/liveDeskIntelligence';

import CrossAssetMonitor from '@/components/LiveDesk/CrossAssetMonitor';
import CrossMarketIntelligence from '@/components/LiveDesk/CrossMarketIntelligence';
import DualBroadcastGrid from '@/components/LiveDesk/DualBroadcastGrid';
import EvidenceDrawer from '@/components/LiveDesk/EvidenceDrawer';
import LiveAlphaPreview from '@/components/LiveDesk/LiveAlphaPreview';
import LiveBroadcastPlayer from '@/components/LiveDesk/LiveBroadcastPlayer';
import LiveIntelligenceTimeline from '@/components/LiveDesk/LiveIntelligenceTimeline';
import MarketAlertCard from '@/components/LiveDesk/MarketAlertCard';
import MarketDriverPanel from '@/components/LiveDesk/MarketDriverPanel';
import MarketIntelligenceFeed from '@/components/LiveDesk/MarketIntelligenceFeed';
import MarketPulseStrip from '@/components/LiveDesk/MarketPulseStrip';
import MarketRegimeCard from '@/components/LiveDesk/MarketRegimeCard';
import RelatedResearch from '@/components/LiveDesk/RelatedResearch';
import UpcomingEvents from '@/components/LiveDesk/UpcomingEvents';
import { istTime } from '@/components/LiveDesk/Primitives';

import './liveDesk.css';

/**
 * AGI Live Desk — global and India, side by side.
 *
 * Two broadcasts of equal size and weight, and beneath them AGI's own reading
 * of each market plus the linkages between them. The broadcasts are inputs to
 * situational awareness; the product is the layer around them.
 *
 * Nothing on this page is hardcoded market data. Where a source is unavailable
 * the panel says so - see useLiveDesk and liveDeskIntelligence, both of which
 * return empty rather than plausible.
 */
export default function LiveDeskPage() {
  const desk = useLiveDesk();
  const [evidence, setEvidence] = useState(null);
  // At most one floating player. Two videos following the reader around would
  // be worse than none, and the other card keeps its place in the grid.
  const [minimizedId, setMinimizedId] = useState(null);

  // Stable identities: these are props on a memoised player, and a new
  // function each render would restart both streams every refresh.
  const minimize = useCallback((id) => setMinimizedId(id), []);
  const restore = useCallback(() => setMinimizedId(null), []);
  const showEvidence = useCallback((item) => setEvidence(item), []);
  const closeEvidence = useCallback(() => setEvidence(null), []);

  const globalIntel = useMemo(
    () => buildIntelligence(desk.snapshot, GLOBAL),
    [desk.snapshot]
  );
  const indiaIntel = useMemo(
    () => buildIntelligence(desk.snapshot, INDIA, desk.themes),
    [desk.snapshot, desk.themes]
  );
  const timeline = useMemo(
    () => [...globalIntel, ...indiaIntel].sort((a, b) => b.sortKey - a.sortKey),
    [globalIntel, indiaIntel]
  );
  const globalDrivers = useMemo(() => buildDrivers(desk.snapshot, GLOBAL), [desk.snapshot]);
  const indiaDrivers = useMemo(() => buildDrivers(desk.snapshot, INDIA), [desk.snapshot]);
  const crossMarket = useMemo(() => buildCrossMarket(desk.snapshot), [desk.snapshot]);

  const marketError = desk.errors?.home || null;
  const refreshLabel = desk.updatedAt ? istTime(desk.updatedAt) : null;
  const floating = minimizedId ? BROADCASTS.find((b) => b.id === minimizedId) : null;

  return (
    <div className="ld-root">
      <Helmet>
        <title>Live Global &amp; Indian Markets | AGI Live Desk</title>
        <meta
          name="description"
          content="Bloomberg and NDTV Profit live financial broadcasts alongside AGI global and Indian market intelligence, cross-asset monitoring, events and research."
        />
      </Helmet>

      <div className="ld-shell">
        <header className="ld-head">
          <div className="ld-head-row">
            <div>
              <h1 className="ld-title">AGI Live Desk</h1>
              <p className="ld-sub">Global + India Markets · Live Intelligence</p>
            </div>
            <div className="ld-head-meta">
              <span className="ld-live-dot">Live</span>
              <span className={desk.stale ? 'ld-refresh ld-stale' : 'ld-refresh'}>
                {refreshLabel
                  ? `${desk.stale ? 'Data delayed · ' : 'Updated '}${refreshLabel}`
                  : 'Refresh status unavailable'}
              </span>
            </div>
          </div>
        </header>

        <DualBroadcastGrid minimizedId={minimizedId} onMinimize={minimize} />

        <div className="ld-section">
          <MarketPulseStrip
            items={desk.snapshot}
            loading={desk.loading}
            error={marketError}
            stale={desk.stale}
            updatedLabel={refreshLabel}
          />
        </div>

        <div className="ld-section">
          <MarketAlertCard alerts={desk.alerts} loading={desk.loading} />
        </div>

        <div className="ld-grid-2">
          <MarketIntelligenceFeed
            title="AGI Global Intelligence"
            items={globalIntel}
            loading={desk.loading}
            error={marketError}
            updatedAt={desk.updatedAt}
            onEvidence={showEvidence}
            emptyLabel="No high-confidence global intelligence right now."
          />
          <MarketIntelligenceFeed
            title="AGI India Intelligence"
            items={indiaIntel}
            loading={desk.loading}
            error={marketError}
            updatedAt={desk.updatedAt}
            onEvidence={showEvidence}
            emptyLabel="No high-confidence India intelligence right now."
          />
        </div>

        <div className="ld-grid-2">
          <MarketDriverPanel
            title="Why Global Markets Are Moving"
            drivers={globalDrivers}
            loading={desk.loading}
            error={marketError}
            emptyLabel="No single dominant global market driver has been identified."
          />
          <MarketDriverPanel
            title="Why India Is Moving"
            drivers={indiaDrivers}
            loading={desk.loading}
            error={marketError}
            emptyLabel="No single dominant driver has been identified for Indian markets."
          />
        </div>

        <div className="ld-section">
          <CrossMarketIntelligence links={crossMarket} loading={desk.loading} error={marketError} />
        </div>

        <div className="ld-grid-2">
          <UpcomingEvents market="GLOBAL" events={desk.events} loading={desk.loading} error={marketError} />
          <UpcomingEvents market="INDIA" events={desk.events} loading={desk.loading} error={marketError} />
        </div>

        <div className="ld-grid-2">
          <CrossAssetMonitor rows={desk.crossAsset} loading={desk.loading} error={marketError} />
          <MarketRegimeCard
            regime={desk.regime}
            flows={desk.flows}
            loading={desk.loading}
            error={desk.errors?.regime}
          />
        </div>

        <div className="ld-section">
          <LiveIntelligenceTimeline items={timeline} loading={desk.loading} error={marketError} />
        </div>

        <div className="ld-grid-2">
          <LiveAlphaPreview
            liveAlpha={desk.liveAlpha}
            loading={desk.loading}
            error={desk.errors?.liveAlpha}
          />
          <RelatedResearch research={desk.research} loading={desk.loading} error={marketError} />
        </div>

        <footer className="ld-foot">
          For research and informational purposes only. Third-party broadcasts are displayed
          through their official embedded players and remain the property of their respective
          publishers. AGI does not control or endorse third-party broadcasts.
        </footer>
      </div>

      {floating ? (
        <div className="ld-pip">
          <div className="ld-pip-bar">
            <span className="ld-label">{floating.title}</span>
            <button type="button" onClick={restore}>Restore</button>
          </div>
          <LiveBroadcastPlayer broadcast={floating} compact />
        </div>
      ) : null}

      <EvidenceDrawer item={evidence} onClose={closeEvidence} />
    </div>
  );
}
