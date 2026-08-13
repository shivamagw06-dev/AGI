import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Database, Layers, Scale, ShieldCheck, Target } from 'lucide-react';
import HedgeFundTerminal, { InlineAsk } from '@/pages/hedgeFundTerminal';
import './hedgeFundLab.css';

const COMPANY_STRATEGIES = [
  ['Quality Compounders', 'Operational', 'ready', 'ROIC · FCF conversion · stability · leverage', 'Persistent business quality across five to ten years.'],
  ['Relative Mispricing', 'Operational', 'ready', 'P/E · P/B · EV/EBITDA · historical percentiles', 'Industry-aware valuation with anomaly checks.'],
  ['Earnings Quality', 'Operational', 'ready', 'CFO · accruals · working capital · FCF', 'Tests whether reported profit converts into cash.'],
  ['Sustainable Growth', 'Operational', 'ready', 'Growth · ROIC · reinvestment · dilution', 'Separates durable growth from financed growth.'],
  ['Capital Allocation', 'Research candidate', 'candidate', 'ROIC · WACC · NOPAT · invested capital', 'WACC remains an explicit model assumption.'],
  ['Balance-Sheet Risk', 'Operational', 'ready', 'Debt · coverage · CFO/debt · liquidity', 'Risk classification, never an automatic short.'],
];

const ALLOCATION_STRATEGIES = [
  ['Macro Regime', 'Operational', 'ready', 'Rates · inflation · growth · INR · institutional flows', 'Changes risk budgets and sector context.'],
  ['Sector Relative Value', 'Operational', 'ready', 'Sector history · quality · valuation · macro', 'Compares sectors with their own history.'],
  ['Pair / Relative Value', 'Experimental', 'experimental', 'Prices · peers · spread · factor exposure', 'Cointegration, half-life and costed testing required.'],
  ['Event Intelligence', 'Data building', 'building', 'Events · exact timestamps · abnormal returns', 'Waiting for point-in-time event depth.'],
  ['Earnings Revisions', 'Data building', 'building', 'Consensus vintages · estimate revisions', 'Current consensus alone is insufficient.'],
  ['Forecast Mispricing', 'Experimental', 'experimental', 'Scenarios · uncertainty · outcome history', 'Promotion requires calibrated forecast outcomes.'],
];

function StrategyRow({ item }) {
  const [name, status, tone, data, note] = item;
  return (
    <article className="hfl-programme-item">
      <div className="hfl-programme-head">
        <h3>{name}</h3>
        <span className={`hfl-programme-status ${tone}`}>{status}</span>
      </div>
      <p>{data}</p>
      <div>{note}</div>
    </article>
  );
}

function ResearchArchitecture() {
  return (
    <section className="hfl-programme" aria-labelledby="investment-architecture-title">
      <div className="hfl-programme-title">
        <div><span>Weeks to years</span><h2 id="investment-architecture-title">Investment opportunity architecture</h2></div>
        <p>Warehouse evidence creates research candidates. Validation and risk remain hard gates before portfolio use.</p>
      </div>
      <div className="hfl-programme-grid">
        <div className="hfl-programme-column">
          <header><Database size={17} /><div><b>Company fundamentals</b><span>Quality · accounting · growth · solvency</span></div></header>
          {COMPANY_STRATEGIES.map((item) => <StrategyRow key={item[0]} item={item} />)}
        </div>
        <div className="hfl-programme-column">
          <header><Scale size={17} /><div><b>Relative value and allocation</b><span>Macro · sectors · events · forecasts</span></div></header>
          {ALLOCATION_STRATEGIES.map((item) => <StrategyRow key={item[0]} item={item} />)}
        </div>
      </div>
      <div className="hfl-process">
        {[
          [Target, 'Alpha estimation', 'Evidence-weighted research return'],
          [ShieldCheck, 'Validation and risk', 'PIT · costs · liquidity · exposure'],
          [Layers, 'Portfolio construction', 'Sizing · constraints · covariance'],
          [Activity, 'Performance learning', 'Attribution · outcomes · calibration'],
        ].map(([Icon, title, detail], index) => (
          <div key={title}><span>{index + 1}</span><Icon size={16} /><b>{title}</b><small>{detail}</small></div>
        ))}
      </div>
    </section>
  );
}

export default function HedgeFundResearchPage() {
  useEffect(() => { document.title = 'Hedge Fund | Agarwal Global Investments'; }, []);
  return (
    <div className="hfl-root">
      <header className="hfl-header hfl-research-header">
        <div className="hfl-mandate"><span>AGI Hedge Fund Research</span><b>Fundamental mispricing, risk and capital allocation</b></div>
        <h1>Investment Opportunity</h1>
        <p>Medium and long-horizon research built from company economics, valuation, accounting quality, macro context and portfolio risk.</p>
        <div className="hfl-focus-links">
          <Link to="/hedge-fund/alpha-opportunities"><Target size={16} /><span>Research queue</span><strong>Alpha Opportunities</strong><small>Fundamental confluence requiring analyst validation</small></Link>
        </div>
        <InlineAsk />
      </header>
      <main className="hfl-body">
        <ResearchArchitecture />
        <section className="hfl-terminal-band">
          <div className="hfl-programme-title"><div><span>Warehouse screens</span><h2>Research candidates</h2></div><p>Operational screens surface evidence to investigate. Scores are neither profit probabilities nor execution instructions.</p></div>
          <HedgeFundTerminal />
        </section>
        <p className="hfl-note">Research only. Operational means a module runs on available warehouse data; it does not mean investment validated, production approved or suitable for execution.</p>
      </main>
    </div>
  );
}
