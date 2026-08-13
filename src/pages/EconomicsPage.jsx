import { useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CalendarClock,
  Database,
  Globe2,
  Landmark,
  Scale,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import PageShell from '@/components/Layout/PageShell';
import AskAgiBar from '@/components/Home/AskAgiBar';
import DeskResearchFeed from '@/components/Research/DeskResearchFeed';
import './economicsPage.css';

const OUTLOOK = [
  { label: 'Growth', state: 'Robust, moderating', direction: 'down', confidence: 'High', explanation: 'Underlying activity remains strong by global standards, although the forward growth profile eases from the prior year.' },
  { label: 'Inflation', state: 'Reaccelerating', direction: 'up-risk', confidence: 'Medium', explanation: 'The source profile points to renewed consumer-price pressure and a sharper producer-price impulse.' },
  { label: 'External balance', state: 'Deteriorating', direction: 'down', confidence: 'High', explanation: 'Import growth outpaces export expansion, increasing the projected current-account burden.' },
  { label: 'Fiscal position', state: 'Still constrained', direction: 'flat', confidence: 'Medium', explanation: 'The consolidated budget balance remains a macro vulnerability despite the sovereign upgrade.' },
];

const TRANSMISSION = [
  ['Rates', 'Less room for rapid easing', 'Reaccelerating price pressure can keep real-rate and policy caution elevated.'],
  ['INR', 'External pressure remains relevant', 'A wider external funding requirement increases sensitivity to oil, USD strength and portfolio flows.'],
  ['Equities', 'Growth support, margin selectivity', 'Domestic growth remains constructive, but input-cost and financing sensitivity should matter more by sector.'],
  ['Credit', 'Sovereign anchor improved', 'The public BBB/Stable sovereign rating supports the credit backdrop, while fiscal and external risks remain.'],
];

const RISK_MAP = [
  ['Growth shock', 'Low–Medium', 'Domestic resilience', 'Global slowdown, weaker investment or consumption'],
  ['Inflation shock', 'Medium', 'Recent disinflation base', 'Food, energy and producer-price pass-through'],
  ['Fiscal slippage', 'Medium', 'Policy commitment to consolidation', 'Subsidies, capex pressure or weaker revenue'],
  ['External shock', 'Medium–High', 'Large, diversified economy', 'Oil, USD strength and abrupt capital outflows'],
  ['Operational risk', 'High', 'Infrastructure and reform momentum', 'Execution bottlenecks and uneven institutional capacity'],
  ['Security risk', 'High', 'Established policy framework', 'Regional geopolitical escalation'],
];

const PUBLIC_FACTS = [
  ['S&P sovereign rating', 'BBB', 'Stable outlook · upgraded from BBB− in Aug 2025'],
  ['Composite PMI', 'Expansion', 'Latest profile reading remains above the neutral 50 threshold'],
  ['Manufacturing PMI', 'Expansion', 'Positive activity, with softer month-on-month momentum'],
  ['Services PMI', 'Expansion', 'Positive activity, with softer month-on-month momentum'],
];

function Status({ children, tone = '' }) {
  return <span className={`eco-status ${tone}`}>{children}</span>;
}

function Direction({ type }) {
  if (type === 'down') return <span className="eco-direction negative"><ArrowDownRight size={15} /> Moderating</span>;
  if (type === 'up-risk') return <span className="eco-direction negative"><ArrowUpRight size={15} /> Risk rising</span>;
  return <span className="eco-direction"><ArrowRight size={15} /> Persistent</span>;
}

export default function EconomicsPage() {
  useEffect(() => { document.title = 'India Economics Intelligence | AGI'; }, []);

  return <PageShell
    title="India Economics Intelligence"
    eyebrow="AGI Economics"
    description="A research view of India’s growth, inflation, external balance, sovereign position and market transmission."
    metaTitle="India Economics Intelligence | Agarwal Global Investments"
    wide
  >
    <div className="eco-root">
      <section className="eco-source-strip">
        <div><Database size={16} /><span>Evidence source</span><b>Licensed country profile</b></div>
        <div><CalendarClock size={16} /><span>Evidence date</span><b>13 Aug 2026</b></div>
        <div><TrendingUp size={16} /><span>AGI interpretation</span><b>Forward macro outlook</b></div>
        <div><ShieldCheck size={16} /><span>Publication policy</span><b>Derived commentary</b></div>
      </section>

      <section className="eco-ask">
        <div><span>AGI economics desk</span><h2>Ask what is changing in India’s macro picture</h2><p>Interrogate the growth, inflation, fiscal, external and sovereign implications of the current evidence.</p></div>
        <AskAgiBar placeholder="Ask why growth can remain robust while macro risks rise..." size="large" buttonLabel="Ask AGI" ariaLabel="Ask AGI about India economics" />
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>AGI macro regime</span><h2>Resilient growth, narrower policy margin</h2></div><Status tone="forecast">DERIVED OUTLOOK</Status></header>
        <div className="eco-regime-summary">
          <div><strong>Base case</strong><p>India remains one of the stronger major-economy growth environments, but the forward mix is less comfortable: momentum moderates as inflation, the external deficit and producer-price pressure become more demanding.</p></div>
          <div><strong>Investment implication</strong><p>The setup still supports domestic earnings, but it argues for greater selectivity toward pricing power, lower balance-sheet sensitivity and businesses less exposed to imported input costs.</p></div>
          <div><strong>What would change the view</strong><p>A durable inflation improvement and stronger export contribution would broaden the opportunity set. Oil, currency or geopolitical shocks would tighten it.</p></div>
        </div>
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>Macro dashboard</span><h2>Directional outlook</h2></div><p>Signals are AGI interpretations of the licensed profile. Provider forecast tables are not reproduced.</p></header>
        <div className="eco-outlook-grid">{OUTLOOK.map((item) => <article key={item.label}>
          <header><span>{item.label}</span><Status>{item.confidence} CONFIDENCE</Status></header>
          <h3>{item.state}</h3><Direction type={item.direction} /><p>{item.explanation}</p>
        </article>)}</div>
      </section>

      <section className="eco-band eco-pmi-risk">
        <div className="eco-public-facts">
          <header className="eco-section-head"><div><span>Publicly observable anchors</span><h2>Activity and sovereign position</h2></div><Status tone="stable">ATTRIBUTED</Status></header>
          {PUBLIC_FACTS.map(([label, value, note]) => <div key={label}><span>{label}</span><strong>{value}</strong><p>{note}</p></div>)}
          <p className="eco-public-note"><Activity size={15} /> PMI values should be refreshed from public S&P releases when a new monthly print is available.</p>
        </div>
        <div className="eco-sovereign">
          <header className="eco-section-head"><div><span>Sovereign assessment</span><h2>Improved anchor, unfinished repair</h2></div></header>
          <div className="eco-rating"><strong>BBB</strong><div><b>Stable public rating</b><span>India’s rating was upgraded from BBB− in August 2025.</span></div></div>
          <div className="eco-thesis-list"><p><b>Supports:</b> policy continuity, infrastructure investment and economic resilience.</p><p><b>Constrains:</b> fiscal burden, external sensitivity and implementation risk.</p><p><b>Watch:</b> whether consolidation continues without weakening productive investment.</p></div>
        </div>
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>Market transmission</span><h2>How the macro view reaches portfolios</h2></div></header>
        <div className="eco-transmission">{TRANSMISSION.map(([asset, view, explanation]) => <article key={asset}><span>{asset}</span><h3>{view}</h3><p>{explanation}</p></article>)}</div>
      </section>

      <section className="eco-band">
        <header className="eco-section-head"><div><span>Risk framework</span><h2>India macro risk map</h2></div><p>Qualitative AGI classifications derived from the source evidence; proprietary provider scores are not displayed.</p></header>
        <div className="eco-risk-table"><div className="head"><b>Risk</b><b>AGI level</b><b>Buffer</b><b>Escalation trigger</b></div>{RISK_MAP.map(([risk, level, buffer, trigger]) => <div key={risk}><b>{risk}</b><Status tone={level.includes('High') ? 'high' : ''}>{level}</Status><span>{buffer}</span><span>{trigger}</span></div>)}</div>
      </section>

      <section className="eco-band eco-two">
        <div className="eco-data-gaps"><header className="eco-section-head"><div><span>Evidence needed next</span><h2>Data expansion roadmap</h2></div></header>
          <ul><li><Activity size={15} /><div><b>Monthly historical macro series</b><span>GDP, CPI, WPI, employment and PMI vintages for trend and surprise analysis.</span></div></li><li><Landmark size={15} /><div><b>RBI policy and yield curve</b><span>Policy history, liquidity, term structure and real-rate diagnostics.</span></div></li><li><Globe2 size={15} /><div><b>External and flow intelligence</b><span>Trade, oil, reserves, FPI, FDI and INR histories with publication dates.</span></div></li></ul>
        </div>
        <div className="eco-methodology"><header className="eco-section-head"><div><span>Publication control</span><h2>Evidence-to-view methodology</h2></div></header>
          <ol><li><b>1</b><span>Read licensed macro, credit and risk evidence.</span></li><li><b>2</b><span>Separate public facts from provider-specific forecasts and scores.</span></li><li><b>3</b><span>Translate direction, interaction and portfolio relevance into AGI commentary.</span></li><li><b>4</b><span>Publish the interpretation with source date, confidence and limitations.</span></li></ol>
        </div>
      </section>

      <section className="eco-band"><DeskResearchFeed deskId="economics" title="Economics Research" /></section>

      <footer className="eco-disclosure"><Database size={15} /><p><b>Evidence:</b> AGI analysis informed by the S&P Global Market Intelligence India Country/Region Profile dated 13 August 2026 and publicly announced sovereign-rating information. This page presents AGI’s derived interpretation and does not reproduce the provider’s forecast, risk-score, currency or comparison tables. Research only; not investment advice.</p></footer>
    </div>
  </PageShell>;
}
