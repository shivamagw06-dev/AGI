import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, ChevronRight, Database, ExternalLink, Globe2, Landmark, Scale, ShieldCheck, X } from 'lucide-react';
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

const MACRO_MODULES = [
  { id:'central-bank', index:'01', name:'Central Bank', ids:['policy_rate','real_policy_rate','yield_10y','fx_reserves'], required:['Policy rate history','Next meeting','Real policy rate','Balance sheet and liquidity operations','Forward guidance'], implication:'Rates, banks, duration and leveraged balance sheets' },
  { id:'fiscal', index:'02', name:'Fiscal Intelligence', ids:['government_debt_gdp','fiscal_balance_gdp','investment'], required:['Fiscal and primary balance','Revenue and expenditure','Government capex','Borrowing and maturity profile'], implication:'Infrastructure, capital goods, sovereign yields and crowding out' },
  { id:'inflation', index:'03', name:'Inflation', ids:['inflation','g20_ind_inflation','cpi','core_cpi','food_inflation','ppi'], required:['CPI and core history','Food, energy, goods and services decomposition','3M/6M annualised momentum','Consensus surprise vintages'], implication:'Policy path, bonds, consumer margins and real income' },
  { id:'growth', index:'04', name:'Growth', ids:['gdp_growth','g20_ind_gdp_growth','gdp','investment','unemployment'], required:['Quarterly real and nominal GDP','PMI and industrial production','Consumption and investment components','Nowcast history'], implication:'Cyclicals, earnings breadth, credit demand and defensives' },
  { id:'rates', index:'05', name:'Rates & Curve', ids:['policy_rate','yield_2y','yield_5y','yield_10y','yield_30y'], required:['1M–30Y sovereign curve','2Y–10Y and 3M–10Y slopes','Real yields','Breakevens and term premium'], implication:'Duration, banks, housing, valuation multiples and refinancing' },
  { id:'liquidity', index:'06', name:'Liquidity', ids:['money_supply','private_credit_gdp','credit_growth'], required:['Central-bank balance sheet','Reserves, repo and funding spreads','Deposits and loan/deposit ratio','Market-liquidity measures'], implication:'Risk appetite, credit creation, funding stress and asset multiples' },
  { id:'credit', index:'07', name:'Credit Cycle', ids:['private_credit_gdp','credit_growth','unemployment'], required:['Bank lending and deposits','NPLs and provisioning','Corporate spreads and defaults','Household delinquencies'], implication:'Banks, leveraged companies, defaults and domestic demand' },
  { id:'fx', index:'08', name:'FX & External', ids:['current_account_gdp','exports','imports','fx_reserves'], required:['Spot and forward history','REER, carry and volatility','Portfolio and capital flows','Dollar-liquidity indicators'], implication:'Importers, exporters, inflation, reserves and capital flows' },
  { id:'commodities', index:'09', name:'Commodities', ids:['brent','oil','gold','copper'], required:['Energy, metals and agriculture curves','Country import/export exposure','Commodity-inflation transmission','Inventory and supply indicators'], implication:'Inflation, trade balances, producers and input-cost margins' },
];

const fmt = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return Math.abs(number) >= 1e9 ? `${(number / 1e9).toFixed(1)}bn` : number.toLocaleString('en-IN', { maximumFractionDigits: 2 });
};

function Status({ children, tone = '' }) { return <span className={`eco-status ${tone}`}>{children}</span>; }

function moduleEvidence(module, byId) {
  return [...new Map(module.ids.map((id) => byId[id]).filter(Boolean).map((row) => [row.series_id, row])).values()];
}

function GlobalState({ byId }) {
  const dimensions = [
    ['Growth', ['gdp_growth','g20_ind_gdp_growth']], ['Inflation', ['inflation','g20_ind_inflation','cpi']],
    ['Rates', ['policy_rate','yield_10y']], ['Liquidity', ['money_supply','credit_growth']],
    ['Credit', ['private_credit_gdp']], ['External', ['current_account_gdp','fx_reserves']],
  ];
  return <section className="eco-band eco-global-state">
    <header className="eco-section-head"><div><span>Global macro state</span><h2>State, evidence and publication authority</h2></div><Status tone="forecast">REGIME WITHHELD</Status></header>
    <div className="eco-state-grid"><div className="eco-state-regime"><span>AGI macro regime</span><strong>NOT YET CLASSIFIED</strong><p>A regime will be published only after comparable history, release vintages and minimum factor coverage pass validation.</p></div>{dimensions.map(([label, ids]) => { const count=ids.filter((id)=>byId[id]).length; return <div key={label}><span>{label}</span><b>{count ? 'OBSERVED · INCOMPLETE' : 'DATA REQUIRED'}</b><small>{count} / {ids.length} anchor series</small></div>; })}</div>
  </section>;
}

function MacroTape({ observations }) {
  const rows = observations.slice(0, 8);
  return <section className="eco-band"><header className="eco-section-head"><div><span>Macro evidence tape</span><h2>Latest persisted releases</h2></div><p>Release observations, not live market quotes. Dates and sources remain attached.</p></header><div className="eco-tape">{rows.length ? rows.map((row)=><div key={row.series_id}><span>{row.label}</span><strong>{fmt(row.value)} <small>{row.unit}</small></strong><b>{String(row.observation_date || 'Date unavailable')}</b><Status>{row.pit_status || 'PIT LIMITED'}</Status></div>) : <p>No persisted macro releases are currently available.</p>}</div></section>;
}

function MacroModules({ byId }) {
  const [selected, setSelected] = useState(null);
  const module = MACRO_MODULES.find((item) => item.id === selected);
  const evidence = module ? moduleEvidence(module, byId) : [];
  return <section className="eco-band">
    <header className="eco-section-head"><div><span>Interpretation engine</span><h2>Nine macro intelligence modules</h2></div><p>Select a module to inspect value → context → missing evidence → market transmission.</p></header>
    <div className="eco-module-grid">{MACRO_MODULES.map((item)=>{ const found=moduleEvidence(item,byId); const state=found.length >= 2 ? 'PARTIAL' : found.length ? 'OBSERVED' : 'DATA REQUIRED'; return <button key={item.id} type="button" onClick={()=>setSelected(item.id)}><span>{item.index}</span><div><h3>{item.name}</h3><p>{item.implication}</p></div><Status tone={state==='DATA REQUIRED'?'':state==='PARTIAL'?'forecast':'stable'}>{state}</Status><ChevronRight size={15}/><small>{found.length} persisted inputs · Why?</small></button>;})}</div>
    {module ? <div className="eco-module-detail" role="dialog" aria-modal="false" aria-label={`${module.name} intelligence`}><header><div><span>{module.index} · Intelligence drill-down</span><h3>{module.name}</h3></div><button type="button" onClick={()=>setSelected(null)} title="Close"><X size={17}/></button></header><div className="eco-module-detail-grid"><section><b>Observed evidence</b>{evidence.length ? evidence.map((row)=><div className="eco-evidence-row" key={row.series_id}><span>{row.label}</span><strong>{fmt(row.value)} {row.unit}</strong><small>{row.observation_date || 'Date unavailable'} · {row.source || 'Source unavailable'}</small></div>) : <p>No approved observation is mapped to this module.</p>}</section><section><b>What is still required</b><ul>{module.required.map((item)=><li key={item}>{item}</li>)}</ul></section><section><b>Why it matters</b><p>{module.implication}.</p><b>AGI interpretation</b><p>{evidence.length >= 2 ? 'Evidence exists, but history and point-in-time coverage are insufficient for a directional regime or investment conclusion.' : 'DATA_REQUIRED. AGI will not infer a directional conclusion from absent or isolated evidence.'}</p></section></div></div> : null}
  </section>;
}

export default function EconomicsPage() {
  const [view, setView] = useState('g20');
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
        <div className="eco-view-switch"><span>View</span><div><button className={view === 'global' ? 'active' : ''} onClick={() => setView('global')}>Global</button><button className={view === 'g20' ? 'active' : ''} onClick={() => setView('g20')}>G20</button><button className={view === 'india' ? 'active' : ''} onClick={() => setView('india')}>India</button></div></div><div><span>Universe</span><b>{view === 'india' ? 'India Core 50' : '19 economies'}</b></div><div><span>History</span><b>Building</b></div><div><span>Frequency</span><b>Annual comparable</b></div>
      </section>

      <section className="eco-source-strip">
        <div><Database size={16}/><span>Latest collection</span><b>{latest ? latest.toLocaleDateString('en-IN') : 'Loading'}</b></div>
        <div><Activity size={16}/><span>Data freshness</span><b>{age == null ? 'Checking' : `${age} day${age === 1 ? '' : 's'}`}</b></div>
        <div><Globe2 size={16}/><span>Series coverage</span><b>{view === 'g20' ? `${g20?.observed ?? 0} / ${g20?.total ?? 152}` : `${readiness?.observed ?? 0} / ${readiness?.total ?? 50}`}</b></div>
        <div><ShieldCheck size={16}/><span>Point in time</span><b>PIT limited</b></div>
      </section>

      <section className="eco-ask"><div><span>Research interface</span><h2>Ask what changed, why it matters and what evidence is missing</h2><p>Ask AGI uses persisted evidence and should distinguish observations from interpretation.</p></div><AskAgiBar placeholder="Ask what the current data says about India’s external position..." size="large" buttonLabel="Ask AGI" ariaLabel="Ask AGI about economics"/></section>

      <GlobalState byId={byId} />
      <MacroTape observations={observations} />
      <MacroModules byId={byId} />

      {view !== 'india' && <section className="eco-band eco-g20-terminal">
        <header className="eco-section-head"><div><span>G20 macro monitor</span><h2>Comparable evidence across 19 economies</h2></div><Status tone={g20?.observed === g20?.total ? 'stable' : 'forecast'}>{g20?.status || 'DATA BUILDING'}</Status></header>
        <div className="eco-g20-summary"><div><strong>{g20?.country_count ?? 19}</strong><span>Economies</span></div><div><strong>{g20?.indicator_count ?? 8}</strong><span>Comparable indicators</span></div><div><strong>{g20?.observed ?? 0}<small> / {g20?.total ?? 152}</small></strong><span>Persisted observations</span></div><div><strong>{g20?.coverage_percent ?? 0}%</strong><span>Coverage</span></div></div>
        <div className="eco-g20-note"><AlertTriangle size={15}/><p>AGI Macro Regime Score: WITHHELD. Green/red direction is not inferred from isolated values; country scores require historical normalization, configured economic signs and point-in-time validation.</p></div>
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
