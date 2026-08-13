import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Database, Layers, Scale, ShieldCheck, Target } from 'lucide-react';
import HedgeFundTerminal, { InlineAsk } from '@/pages/hedgeFundTerminal';
import { getResearchFactorAudit } from '@/lib/intelligenceApi';
import './hedgeFundLab.css';

const COMPANY_STRATEGIES = [
  ['Quality Compounders', 'In Development', 'development', 'ROIC · FCF conversion · stability · leverage', 'Current screen is basic; the 5–10Y factor model is not complete.'],
  ['Relative Mispricing', 'In Development', 'development', 'P/E · P/B · EV/EBITDA · historical percentiles', 'Historical valuation exists; the validated composite is not complete.'],
  ['Earnings Quality', 'In Development', 'development', 'CFO · accruals · working capital · FCF', 'Accounting Intelligence exists; the Hedge Fund adapter is not complete.'],
  ['Sustainable Growth', 'In Development', 'development', 'Growth · ROIC · reinvestment · dilution', 'Sustainable-growth and growth-gap mathematics are not complete.'],
  ['Capital Allocation', 'Data Building', 'building', 'ROIC · WACC · NOPAT · invested capital', 'Deployment history and evidence-backed WACC inputs remain incomplete.'],
  ['Balance-Sheet Risk', 'In Development', 'development', 'Debt · coverage · CFO/debt · liquidity', 'Current stress rules precede the unified risk model.'],
];

const ALLOCATION_STRATEGIES = [
  ['Macro Regime', 'In Development', 'development', 'Rates · inflation · growth · INR · institutional flows', 'Deterministic five-regime classifier is not yet portfolio-wired.'],
  ['Sector Relative Value', 'In Development', 'development', 'Sector history · quality · valuation · macro', 'Sector history exists; the four-factor composite is incomplete.'],
  ['Pair / Relative Value', 'Experimental', 'experimental', 'Prices · peers · spread · factor exposure', 'Cointegration, half-life and costed testing required.'],
  ['Event Intelligence', 'Data building', 'building', 'Events · exact timestamps · abnormal returns', 'Waiting for point-in-time event depth.'],
  ['Earnings Revisions', 'Data building', 'building', 'Consensus vintages · estimate revisions', 'Current consensus alone is insufficient.'],
  ['Forecast Mispricing', 'Experimental', 'experimental', 'Scenarios · uncertainty · outcome history', 'Promotion requires calibrated forecast outcomes.'],
  ['Portfolio Optimization', 'Experimental', 'experimental', 'Alpha vector · covariance · turnover · constraints', 'Current tools are illustrative, not an optimizer.'],
  ['Risk Decomposition', 'Experimental', 'experimental', 'Market · sector · factor · idiosyncratic risk', 'Current risk contribution is a proxy, not a factor covariance model.'],
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
        <p>These are permanent maturity states, not marketing labels. Only implemented mathematics with production data checks can become Operational.</p>
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
          [Target, 'Research factor layer', 'Versioned metrics · evidence · PIT cutoff'],
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

const isNumber = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const score = (value) => isNumber(value) ? Number(value).toFixed(1) : 'Unavailable';
const percent = (value) => isNumber(value) ? `${(Number(value) * 100).toFixed(1)}%` : 'Unavailable';

function FactorAudit() {
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    getResearchFactorAudit(20).then((data) => { if (active) setAudit(data); }).catch((err) => { if (active) setError(err?.message || 'Factor audit unavailable'); });
    return () => { active = false; };
  }, []);
  const rows = Array.isArray(audit?.rows) ? audit.rows : [];
  const lead = rows[0];
  return (
    <section className="hfl-factor-audit" aria-labelledby="factor-audit-title">
      <div className="hfl-programme-title">
        <div><span>Fundamental research summary</span><h2 id="factor-audit-title">Strongest fundamental research signals</h2></div>
        <p>Rankings reflect accounting-factor evidence only. They are not investment recommendations or demonstrated predictive alpha.</p>
      </div>
      {error ? <div className="hfl-factor-empty">Factor output is currently unavailable. {error}</div> : null}
      {!error && !audit ? <div className="hfl-factor-empty">Calculating warehouse factors...</div> : null}
      {!error && audit && rows.length === 0 ? <div className="hfl-factor-empty">No eligible factor outputs are available for this cutoff.</div> : null}
      {rows.length > 0 ? <>
        <div className="hfl-factor-meta"><b>{audit.status || 'IN_DEVELOPMENT'}</b><span>{audit.layer_version}</span><span>As of {audit.as_of}</span><span>{audit.universe} companies evaluated</span></div>
        <div className="hfl-factor-table-wrap"><table className="hfl-factor-table">
          <thead><tr><th>Company</th><th>Composite</th><th>Quality</th><th>Earnings</th><th>Growth</th><th>Capital</th><th>Balance</th><th>ROIC 5Y</th><th>FCF margin</th><th>Mispricing</th><th>Data quality</th><th>PIT status</th></tr></thead>
          <tbody>{rows.map((row) => <tr key={row.symbol}>
            <td><b>{row.symbol}</b><span>{row.company_name || 'Name unavailable'}</span></td>
            <td>{score(row.fundamental_composite)}</td><td>{score(row.quality_score)}</td><td>{score(row.earnings_quality_score)}</td><td>{score(row.sustainable_growth_score)}</td>
            <td>{score(row.capital_allocation_score)}</td><td>{score(row.balance_sheet_risk_score)}</td><td>{percent(row.roic_5y)}</td>
            <td>{percent(row.fcf_margin)}</td><td>{score(row.mispricing_score)}</td>
            <td>{score(row.data_quality)}</td><td><span className="hfl-pit-status">{String(row.validation_status || 'Unavailable').replaceAll('_', ' ')}</span></td>
          </tr>)}</tbody>
        </table></div>
        {lead ? <div className="hfl-research-summary">
          <header><span>Research summary</span><h3>{lead.company_name || lead.symbol} · {lead.primary_factor}</h3></header>
          <div><b>Supporting factors</b><p>{lead.supporting_factors?.join(' · ') || 'Unavailable'}</p></div>
          <div><b>Positive evidence</b><p>{lead.primary_evidence?.join(' · ') || 'Unavailable'}</p></div>
          <div><b>Contradictory evidence</b><p>{lead.contradictory_evidence?.join(' · ') || 'None identified from available fields'}</p></div>
          <div><b>Key limitation</b><p>{lead.key_risk}</p></div>
        </div> : null}
      </> : null}
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
        <FactorAudit />
        <section className="hfl-terminal-band">
          <div className="hfl-programme-title"><div><span>Current basic implementation</span><h2>Warehouse research screens</h2></div><p>These screens use available valuation, profitability, leverage and consensus fields. They are inputs to the factor build, not the completed mathematics described above.</p></div>
          <HedgeFundTerminal />
        </section>
        <p className="hfl-note">Research only. Operational means a module runs on available warehouse data; it does not mean investment validated, production approved or suitable for execution.</p>
      </main>
    </div>
  );
}
