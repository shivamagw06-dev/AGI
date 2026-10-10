import { useMemo, useState } from 'react';
import PeTerminalLayout from '@/components/private-equity/PeTerminalLayout';
import PeResearchFeed from '@/components/private-equity/PeResearchFeed';
import PeDashboard from '@/components/private-equity/PeDashboard';
import PeFirmRankings from '@/components/private-equity/PeFirmRankings';
import { usePeOverview } from '@/hooks/usePeIntelligence';
import '@/components/private-equity/peTerminal.css';

export default function PrivateEquityIntelligencePage() {
  const [activeSector, setActiveSector] = useState(null);
  const { data, loading, error } = usePeOverview(activeSector);

  const feed = useMemo(() => data?.feed ?? [], [data]);

  return (
    <PeTerminalLayout title="Private Equity Intelligence">
      {loading && <div className="pe-loading">Loading institutional PE intelligence…</div>}
      {error && (
        <div className="pe-loading text-red-400">
          Unable to load PE data. Ensure the API server is running.
        </div>
      )}
      {data && (
        <div className="pe-layout">
          <PeResearchFeed
            items={feed}
            activeSector={activeSector}
            onClearSector={() => setActiveSector(null)}
          />
          <PeDashboard
            data={data}
            activeSector={activeSector}
            onSectorSelect={setActiveSector}
          />
          <PeFirmRankings firms={data.firms} />
        </div>
      )}
    </PeTerminalLayout>
  );
}
