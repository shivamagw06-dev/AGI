import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, Database, ExternalLink, Globe2, Landmark, Scale, ShieldCheck } from 'lucide-react';
import PageShell from '@/components/Layout/PageShell';
import AskAgiBar from '@/components/Home/AskAgiBar';
import DeskResearchFeed from '@/components/Research/DeskResearchFeed';
import { getMieDataReadiness, getMieG20Matrix, getMieLatestPublicObservations } from '@/lib/intelligenceApi';
import './economicsPage.css';

const PULSE = [
  ['growth', 'Growth', ['gdp_growth', 'gdp', 'investment']],
  ['inflation', 'Inflation', ['cpi', 'core_cpi', 'ppi', 'food_inflation']],
  ['monetary', 'Monetary policy', ['policy_rate', 'real_policy_rate', 'yield_10y']],
  ['fiscal', 'Fiscal', ['government_debt_gdp', 'fiscal_balance_gdp']],
  ['external', 'External', ['current_account_gdp', 'exports', 'imports', 'fx_reserves']],
  ['financial', 'Financial conditions', ['private_credit_gdp', 'credit_growth', 'money_supply']],
];

const TRANSMISSION = [
  ['Rates rise', 'Real estate, leveraged companies, rate-sensitive consumption', 'Banks may benefit or suffer depending on deposit repricing, credit growth and asset quality.'],
  ['INR weakens', 'Import-heavy manufacturers, aviation, consumer margins', 'IT services, pharma and other exporters may receive a translation benefit.'],
  ['Oil rises', 'Aviation, paints, chemicals, logistics and import costs', 'Upstream energy may benefit; downstream effects depend on pass-through.'],
  ['Growth moderates', 'Cyclicals, discretionary consumption and credit demand', 'Defensive earnings and balance-sheet resilience become more relevant.'],
];

const fmt = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return Math.abs(number) >= 1e9 ? `${(number / 1e9).toFixed(1)}bn` : number.toLocaleString('en-IN', { maximumFractionDigits: 2 });
};

function Status({ children, tone = '' }) { return <span className={`eco-status ${tone}`}>{children}</span>; }

export default function EconomicsPage() {
  const [view, setView] = useState('india');
  const [readiness, setReadiness] = useState(null);
  const [publicData, setPublicData] = useState(null);
  const [g20, setG20] = useState(null);
  useEffect(() => { document.title = 'Economic Intelligence | AGI'; }, []);
  useEffect(() => {
    let active = true;
    Promise.allSettled([getMieDataReadiness('India'), getMieLatestPublicObservations('India'), getMieG20Matrix()]).then(([r, o, g]) => {
      if (!active) return;
      if (r.status === 'fulfilled') setReadiness(r.value);
      if (o.status === 'fulfilled') setPublicData(o.value);
      if (g.status === 'fulfilled') setG20(g.value);
    });
    return () => { active = false; };
  }, []);
  const observations = publicData?.observations || [];
  const byId = useMemo(() => Object.fromEntries(observations.map((row) => [row.series_id, row])), [observations]);
  const latest = publicData?.latest_available_at ? new Date(publicData.latest_available_at) : null;
  const age = latest && !Number.isNaN(latest.getTime()) ? Math.max(0, Math.floor((Date.now() - latest.getTime()) / 86400000)) : null;

  return <PageShell title="Economic Intelligence" eyebrow="AGI Economics" description="Macro conditions, economic regimes and transmission across markets." metaTitle="Economic Intelligence | Agarwal Global Investments" wide>
    <div className="eco-root eco-terminal">
      <section className="eco-controls" aria-label="Economics scope">
        <div className="eco-view-switch"><span>View</span><div><button className={view === 'india' ? 'active' : ''} onClick={() => setView('india')}>India</button><button className={view === 'g20' ? 'active' : ''} onClick={() => setView('g20')}>G20</button></div></div><div><span>Universe</span><b>{view === 'g20' ? '19 economies' : 'Core 50'}</b></div><div><span>History</span><b>Building</b></div><div><span>Frequency</span><b>Annual comparable</b></div>
      </section>

      <section className="eco-source-strip">
        <div><Database size={16}/><span>Latest collection</span><b>{latest ? latest.toLocaleDateString('en-IN') : 'Loading'}</b></div>
        <div><Activity size={16}/><span>Data freshness</span><b>{age == null ? 'Checking' : `${age} day${age === 1 ? '' : 's'}`}</b></div>
        <div><Globe2 size={16}/><span>Series coverage</span><b>{view === 'g20' ? `${g20?.observed ?? 0} / ${g20?.total ?? 152}` : `${readiness?.observed ?? 0} / ${readiness?.total ?? 50}`}</b></div>
        <div><ShieldCheck size={16}/><span>Point in time</span><b>PIT limited</b></div>
      </section>

      <section className="eco-ask"><div><span>Research interface</span><h2>Ask what changed, why it matters and what evidence is missing</h2><p>Ask AGI uses persisted evidence and should distinguish observations from interpretation.</p></div><AskAgiBar placeholder="Ask what the current data says about India’s external position..." size="large" buttonLabel="Ask AGI" ariaLabel="Ask AGI about economics"/></section>

      {view === 'g20' && <section className="eco-band eco-g20-terminal">
        <header className="eco-section-head"><div><span>G20 macro monitor</span><h2>Comparable evidence across 19 economies</h2></div><Status tone={g20?.observed === g20?.total ? 'stable' : 'forecast'}>{g20?.status || 'DATA BUILDING'}</Status></header>
        <div className="eco-g20-summary"><div><strong>{g20?.country_count ?? 19}</strong><span>Economies</span></div><div><strong>{g20?.indicator_count ?? 8}</strong><span>Comparable indicators</span></div><div><strong>{g20?.observed ?? 0}<small> / {g20?.total ?? 152}</small></strong><span>Persisted observations</span></div><div><strong>{g20?.coverage_percent ?? 0}%</strong><span>Coverage</span></div></div>
        <div className="eco-g20-note"><AlertTriangle size={15}/><p>This is the observed layer. AGI does not assign country scores, ranks or regimes until historical factor calculations and point-in-time validation are available.</p></div>
        <div className="eco-g20-matrix"><div className="head"><b>Economy</b><b>GDP growth</b><b>Inflation</b><b>Unemployment</b><b>Debt / GDP</b><b>Current account</b><b>Investment</b><b>Private credit</b><b>Coverage</b></div>{(g20?.countries || []).map((row) => {
          const value = (key) => row.indicators?.[key];
          const cell = (key) => { const item=value(key); return <span className={!item ? 'missing' : ''}>{item ? <>{fmt(item.value)}<small>{item.unit} · {String(item.observation_date || '').slice(0,4)}</small></> : <>—<small>DATA BUILDING</small></>}</span>; };
          return <div className={row.iso3 === 'IND' ? 'india' : ''} key={row.iso3}><b>{row.country}<small>{row.iso3}</small></b>{cell('gdp_growth')}{cell('inflation')}{cell('unemployment')}{cell('government_debt_gdp')}{cell('current_account_gdp')}{cell('investment_gdp')}{cell('private_credit_gdp')}<strong>{row.observed} / {row.total}</strong></div>;
        })}</div>
        <footer className="eco-g20-footer"><Database size={14}/><span>Source: World Bank Indicators API · Annual latest available · PROVISIONAL · PIT LIMITED</span></footer>
      </section>}

      <section className="eco-band eco-regime-terminal">
        <header className="eco-section-head"><div><span>Macro regime</span><h2>Classification withheld until factor history is sufficient</h2></div><Status tone="forecast">DATA BUILDING</Status></header>
        <div className="eco-regime-grid">
          <div className="eco-regime-main"><strong>NOT YET CLASSIFIED</strong><p>AGI has current observations for {readiness?.observed ?? 0} of 50 required series. A defensible regime needs time-series history, normalized factor calculations and explicit minimum coverage.</p></div>
          <div><b>Why?</b><p>Rolling trends, z-scores, breadth and acceleration cannot be calculated from a single latest observation.</p></div>
          <div><b>What unlocks it?</b><p>Historical RBI, MoSPI and Commerce vintages plus transparent Growth, Inflation, Liquidity, Fiscal and External factor rules.</p></div>
        </div>
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>Macro pulse</span><h2>Coverage before conclusions</h2></div><p>No pulse score is displayed without sufficient component history.</p></header>
        <div className="eco-pulse-grid">{PULSE.map(([domain, label, ids]) => {
          const available = ids.map((id) => byId[id]).filter(Boolean);
          return <article key={domain}><header><span>{label}</span><Status tone={available.length ? 'stable' : ''}>{available.length ? 'OBSERVED' : 'DATA BUILDING'}</Status></header><strong>{available.length} / {ids.length}</strong><p>{available.length ? available.map((row) => row.label).join(' · ') : 'No persisted observations yet'}</p><footer>Factor score: withheld</footer></article>;
        })}</div>
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>Layer 1 · Observed</span><h2>Latest official/public observations</h2></div><Status tone="stable">{observations.length} VALUES</Status></header>
        <div className="eco-observation-table"><div className="head"><b>Indicator</b><b>Latest</b><b>Observation</b><b>Source</b><b>Quality / PIT</b></div>{observations.map((row) => <div key={row.series_id}><span><b>{row.label}</b><small>{row.frequency}</small></span><strong>{fmt(row.value)} <small>{row.unit}</small></strong><span>{row.observation_date || '—'}</span><a href={row.source_url || '#'} target="_blank" rel="noreferrer">{row.source || 'Official source'} <ExternalLink size={12}/></a><span><Status>{row.quality_status}</Status><small>{row.pit_status}</small></span></div>)}</div>
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>Layers 2–3 · Calculated and regime</span><h2>Factor engine readiness</h2></div><Status tone="forecast">IN DEVELOPMENT</Status></header>
        <div className="eco-factor-table"><div className="head"><b>Module</b><b>Required mathematics</b><b>Minimum evidence</b><b>Status</b></div>
          <div><b>Growth factor</b><span>YoY, momentum, acceleration, rolling z-score</span><span>GDP, IIP, PMI, credit and activity history</span><Status>DATA BUILDING</Status></div>
          <div><b>Inflation pressure</b><span>3M/6M trend, breadth, core divergence</span><span>CPI, core, food, WPI, oil and FX history</span><Status>DATA BUILDING</Status></div>
          <div><b>Financial conditions</b><span>Configured-sign standardized composite</span><span>Rates, curve, credit, FX, liquidity and spreads</span><Status>DATA BUILDING</Status></div>
          <div><b>Macro regime</b><span>Rule-based factor classification</span><span>Minimum component coverage and stable history</span><Status>NOT PIT READY</Status></div>
          <div><b>Economic surprise</b><span>Actual minus contemporaneous consensus</span><span>Historical consensus vintages</span><Status>DATA BUILDING</Status></div>
        </div>
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>Layer 4 · AGI interpretation</span><h2>Macro-to-sector transmission framework</h2></div><p>Research sensitivities, not predicted stock returns or trading signals.</p></header>
        <div className="eco-transmission">{TRANSMISSION.map(([factor, pressure, nuance]) => <article key={factor}><span>{factor}</span><h3>{pressure}</h3><p>{nuance}</p><footer>AGI transmission framework</footer></article>)}</div>
      </section>

      <section className="eco-band eco-two">
        <div className="eco-data-gaps"><header className="eco-section-head"><div><span>Collection priority</span><h2>What the engine needs next</h2></div></header><ul>
          <li><Landmark size={15}/><div><b>RBI</b><span>Policy rate, yields, liquidity, credit, money, reserves, currency and banking conditions.</span></div></li>
          <li><Activity size={15}/><div><b>MoSPI</b><span>CPI, IIP, GDP components and official release/vintage history.</span></div></li>
          <li><Globe2 size={15}/><div><b>Ministry of Commerce</b><span>Monthly exports, imports and trade balance with release dates.</span></div></li>
        </ul></div>
        <div className="eco-methodology"><header className="eco-section-head"><div><span>Governance</span><h2>Publication gates</h2></div></header><ol>
          <li><b>1</b><span>Observed values require persisted source lineage.</span></li><li><b>2</b><span>Calculated factors require visible formulas and coverage.</span></li><li><b>3</b><span>Regimes require sufficient history and PIT controls.</span></li><li><b>4</b><span>Interpretation must cite the evidence that created it.</span></li>
        </ol></div>
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>Data quality</span><h2>Core 50 readiness by domain</h2></div><Status tone={readiness?.status === 'OPERATIONAL' ? 'stable' : 'forecast'}>{readiness?.status || 'DATA BUILDING'}</Status></header>
        <div className="eco-readiness"><div className="eco-readiness-total"><strong>{readiness?.observed ?? 0}<small> / {readiness?.total ?? 50}</small></strong><span>Persisted India series</span><i><em style={{width:`${readiness?.coverage_percent || 0}%`}}/></i><p>{readiness?.policy || 'Only persisted observations count.'}</p></div><div className="eco-readiness-domains">{(readiness?.domains || []).map((row) => <div key={row.domain}><span>{row.domain}</span><b>{row.observed} / {row.total}</b></div>)}</div></div>
      </section>

      <section className="eco-band"><DeskResearchFeed deskId="economics" title="Economics Research"/></section>
      <footer className="eco-disclosure"><AlertTriangle size={15}/><p><b>Research status:</b> World Bank collection is operational. RBI, MoSPI, Ministry of Commerce, IMF, BIS and OECD connectors are registered but not yet verified live. Current observations are PIT limited. Factor scores, country rankings, historical regimes and surprise indices remain withheld until their evidence requirements are met.</p></footer>
    </div>
  </PageShell>;
}
