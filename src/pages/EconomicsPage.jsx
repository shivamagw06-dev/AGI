import { useEffect, useMemo, useState } from 'react';
import { Activity, ArrowRight, BarChart3, ChevronDown, Database, ExternalLink, Globe2, Landmark, RefreshCw, ShieldCheck, TrendingUp } from 'lucide-react';
import PageShell from '@/components/Layout/PageShell';
import AskAgiBar from '@/components/Home/AskAgiBar';
import DeskResearchFeed from '@/components/Research/DeskResearchFeed';
import { getMieDataReadiness, getMieG20Matrix, getMieLatestPublicObservations, getMieSupplementalObservations } from '@/lib/intelligenceApi';
import './economicsPage.css';

const LENSES = [
  { id: 'growth', label: 'Growth', ids: ['gdp_growth', 'gdp', 'investment', 'industrial_production'], summary: 'Output, investment and industrial momentum', color: '#ff9f43' },
  { id: 'inflation', label: 'Inflation', ids: ['cpi', 'core_cpi', 'food_inflation', 'ppi'], summary: 'Price pressure and household purchasing power', color: '#ef5b5b' },
  { id: 'monetary', label: 'Rates', ids: ['policy_rate', 'real_policy_rate', 'yield_10y', 'yield_2y'], summary: 'RBI stance, real rates and the sovereign curve', color: '#4e8cff' },
  { id: 'external', label: 'External', ids: ['usd_fx', 'current_account_gdp', 'exports', 'imports', 'fx_reserves'], summary: 'Currency, trade and external resilience', color: '#18b77a' },
  { id: 'credit', label: 'Credit', ids: ['bank_credit', 'credit_growth', 'private_credit_gdp', 'debt_service_ratio'], summary: 'Funding, leverage and domestic demand', color: '#a778e8' },
  { id: 'global', label: 'Global', ids: ['oil', 'gas', 'copper', 'gold', 'global_risk'], summary: 'Input costs, risk appetite and world demand', color: '#e4b53f' },
];

const TRANSMISSION = [
  { trigger: 'Rates stay restrictive', effect: 'Banks, housing and duration', detail: 'Deposit repricing, credit demand and refinancing costs become the decisive transmission channels.' },
  { trigger: 'Oil moves higher', effect: 'Inflation and margins', detail: 'Import costs pressure aviation, logistics, paints and consumption; upstream energy benefits.' },
  { trigger: 'INR weakens', effect: 'Exporters versus importers', detail: 'IT and pharma may receive translation support while import-intensive businesses face margin pressure.' },
  { trigger: 'Growth broadens', effect: 'Domestic cyclicals', detail: 'Credit, capital goods and discretionary demand improve when investment and consumption move together.' },
];

const SOURCE_STACK = [
  ['India official', 'RBI · MoSPI · Ministry of Commerce', 'Primary releases and policy evidence'],
  ['Global official', 'World Bank · BIS · OECD · ILO', 'Comparable history and cross-country context'],
  ['Market context', 'Yahoo Finance · FMP', 'FX, commodities, yields and release calendar'],
];

const fmt = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return 'Awaiting release';
  if (Math.abs(number) >= 1e9) return `${(number / 1e9).toFixed(1)}bn`;
  return number.toLocaleString('en-IN', { maximumFractionDigits: 2 });
};

const shortDate = (value) => {
  if (!value) return 'Date pending';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
};

function LensCard({ lens, observations, onOpen }) {
  const rows = lens.ids.map((id) => observations[id]).filter(Boolean);
  const lead = rows[0];
  return <button type="button" className="eco-client-lens" style={{ '--lens': lens.color }} onClick={() => onOpen(lens)}>
    <span className="eco-client-lens-mark"><Activity size={15} />{lens.label}</span>
    <strong>{lead ? fmt(lead.value) : 'Building'}</strong>
    <small>{lead ? `${lead.label} · ${lead.unit || ''}` : lens.summary}</small>
    <footer><span>{rows.length} of {lens.ids.length} inputs</span><ArrowRight size={15} /></footer>
  </button>;
}

function EvidenceDrawer({ lens, observations, onClose }) {
  return <div className="eco-client-drawer">
    <header><div><small>Macro lens</small><h3>{lens.label}</h3><p>{lens.summary}</p></div><button type="button" onClick={onClose}>Close</button></header>
    <div>{lens.ids.map((id) => {
      const row = observations[id];
      return <article key={id} className={!row ? 'missing' : ''}>
        <span>{row?.label || id.replaceAll('_', ' ')}</span>
        <strong>{row ? `${fmt(row.value)} ${row.unit || ''}` : 'Awaiting official source'}</strong>
        <small>{row ? `${shortDate(row.observation_date)} · ${row.source || 'Official/public source'}` : 'Not inferred or estimated'}</small>
      </article>;
    })}</div>
    <footer><ShieldCheck size={15} /> AGI separates observed data from interpretation and does not manufacture missing values.</footer>
  </div>;
}

function G20View({ matrix }) {
  const countries = matrix?.countries || [];
  return <section className="eco-client-section">
    <header className="eco-client-heading"><div><small>Global comparison</small><h2>G20 macro pulse</h2><p>Comparable evidence across major economies. Select indicators remain under construction.</p></div><span>{matrix?.coverage_percent ?? 0}% coverage</span></header>
    <div className="eco-client-g20">
      <div className="head"><b>Economy</b><b>Growth</b><b>Inflation</b><b>Unemployment</b><b>Debt / GDP</b><b>Coverage</b></div>
      {countries.map((country) => {
        const cell = (id) => country.indicators?.[id] ? `${fmt(country.indicators[id].value)} ${country.indicators[id].unit || ''}` : '—';
        return <div key={country.iso3} className={country.iso3 === 'IND' ? 'india' : ''}><b>{country.country}<small>{country.iso3}</small></b><span>{cell('gdp_growth')}</span><span>{cell('inflation')}</span><span>{cell('unemployment')}</span><span>{cell('government_debt_gdp')}</span><strong>{country.observed} / {country.total}</strong></div>;
      })}
    </div>
  </section>;
}

export default function EconomicsPage() {
  const [scope, setScope] = useState('india');
  const [readiness, setReadiness] = useState(null);
  const [publicData, setPublicData] = useState(null);
  const [supplemental, setSupplemental] = useState(null);
  const [g20, setG20] = useState(null);
  const [selectedLens, setSelectedLens] = useState(null);
  const [methodOpen, setMethodOpen] = useState(false);

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([getMieDataReadiness('India'), getMieLatestPublicObservations('India'), getMieSupplementalObservations(), getMieG20Matrix()]).then(([ready, latest, extra, matrix]) => {
      if (!mounted) return;
      if (ready.status === 'fulfilled') setReadiness(ready.value);
      if (latest.status === 'fulfilled') setPublicData(latest.value);
      if (extra.status === 'fulfilled') setSupplemental(extra.value);
      if (matrix.status === 'fulfilled') setG20(matrix.value);
    });
    return () => { mounted = false; };
  }, []);

  const observations = useMemo(() => [...(publicData?.observations || []), ...(supplemental?.observations || [])], [publicData, supplemental]);
  const byId = useMemo(() => Object.fromEntries(observations.map((row) => [row.series_id, row])), [observations]);
  const latestAt = publicData?.latest_available_at;
  const coverage = readiness?.coverage_percent ?? 0;
  const headline = byId.gdp_growth || byId.gdp || observations[0];
  const tape = observations.slice(0, 7);

  return <PageShell title="India Economic Intelligence" eyebrow="AGI Economics" description="The forces shaping growth, inflation, rates and Indian assets." metaTitle="India Economic Intelligence | Agarwal Global Investments" wide>
    <div className="eco-client-root">
      <section className="eco-client-hero">
        <div className="eco-client-hero-copy">
          <span><i /> Evidence updated {shortDate(latestAt)}</span>
          <h1>Read the economy.<br /><em>Understand the market.</em></h1>
          <p>Official economic releases, global context and AGI's market-transmission framework in one concise research view.</p>
          <div className="eco-client-scope"><button className={scope === 'india' ? 'active' : ''} onClick={() => setScope('india')}>India</button><button className={scope === 'g20' ? 'active' : ''} onClick={() => setScope('g20')}>G20 comparison</button></div>
        </div>
        <aside>
          <span>Latest macro evidence</span>
          <strong>{headline ? fmt(headline.value) : 'Collecting'}</strong>
          <b>{headline?.label || 'India Core 50'}</b>
          <p>{headline ? `${headline.unit || ''} · observation ${shortDate(headline.observation_date)}` : 'AGI is refreshing official and public sources.'}</p>
          <div><span><Database size={15} />{readiness?.observed ?? 0} series observed</span><span><RefreshCw size={15} />{coverage}% coverage</span></div>
        </aside>
      </section>

      <section className="eco-client-ask"><div><small>Ask AGI</small><h2>What does the macro picture mean for investors?</h2></div><AskAgiBar placeholder="Ask how rates, oil or growth affect Indian sectors..." size="large" buttonLabel="Ask AGI" ariaLabel="Ask AGI about economics" /></section>

      {scope === 'india' ? <>
        <section className="eco-client-section">
          <header className="eco-client-heading"><div><small>India dashboard</small><h2>Six lenses that shape the investment environment</h2><p>Open a lens to see the underlying evidence and fields still awaiting official data.</p></div><span>{readiness?.observed ?? 0} / {readiness?.total ?? 50} core series</span></header>
          <div className="eco-client-lenses">{LENSES.map((lens) => <LensCard key={lens.id} lens={lens} observations={byId} onOpen={setSelectedLens} />)}</div>
          {selectedLens ? <EvidenceDrawer lens={selectedLens} observations={byId} onClose={() => setSelectedLens(null)} /> : null}
        </section>

        <section className="eco-client-section eco-client-tape-wrap">
          <header className="eco-client-heading"><div><small>Latest evidence</small><h2>Macro release tape</h2><p>Persisted observations with dates and source links.</p></div><span>Observed, not forecast</span></header>
          <div className="eco-client-tape">{tape.length ? tape.map((row) => <article key={row.series_id}><div><span>{row.label}</span><small>{shortDate(row.observation_date)}</small></div><strong>{fmt(row.value)} <small>{row.unit}</small></strong>{row.source_url ? <a href={row.source_url} target="_blank" rel="noreferrer" title="Open source"><ExternalLink size={15} /></a> : <ShieldCheck size={15} />}</article>) : <p>AGI is refreshing the latest official releases.</p>}</div>
        </section>

        <section className="eco-client-section">
          <header className="eco-client-heading"><div><small>Investment transmission</small><h2>How macro changes reach markets</h2><p>Research pathways, not automatic trade signals.</p></div></header>
          <div className="eco-client-transmission">{TRANSMISSION.map((item, index) => <article key={item.trigger}><span>0{index + 1}</span><b>{item.trigger}</b><ArrowRight size={17} /><h3>{item.effect}</h3><p>{item.detail}</p></article>)}</div>
        </section>
      </> : <G20View matrix={g20} />}

      <section className="eco-client-section eco-client-sources">
        <header className="eco-client-heading"><div><small>Evidence architecture</small><h2>Automatic, source-aware collection</h2><p>AGI refreshes connected feeds without requiring manual spreadsheets.</p></div><button type="button" onClick={() => setMethodOpen((value) => !value)}>Methodology <ChevronDown size={15} /></button></header>
        <div>{SOURCE_STACK.map(([tier, source, use]) => <article key={tier}><span>{tier}</span><strong>{source}</strong><p>{use}</p></article>)}</div>
        {methodOpen ? <aside><ShieldCheck size={17} /><p><b>Evidence policy.</b> Every observation retains its source, period, collection time and quality status. Missing data is shown explicitly and is never estimated on page load. Interpretation remains separate from observed facts.</p></aside> : null}
      </section>

      <section className="eco-client-research"><header><div><small>AGI Research</small><h2>Economics desk</h2></div><BarChart3 size={24} /></header><DeskResearchFeed deskId="economics" title="Latest economics research" /></section>
      <footer className="eco-client-footer"><Landmark size={16} /><p>AGI Economics is institutional research context, not personalised investment advice. Source availability and publication schedules vary.</p><span><Globe2 size={15} /> India + G20</span><span><TrendingUp size={15} /> Market transmission</span></footer>
    </div>
  </PageShell>;
}
