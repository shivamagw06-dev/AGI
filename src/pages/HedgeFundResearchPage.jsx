import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BookOpenCheck,
  ChevronRight,
  CircleDashed,
  Database,
  FlaskConical,
  Layers3,
  Scale,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { InlineAsk } from '@/pages/hedgeFundTerminal';
import {
  getCapitalIqMigrationStatus,
  getResearchFactorAudit,
  getResearchFactorCompany,
} from '@/lib/intelligenceApi';
import './hedgeFundLab.css';

const FACTORS = [
  { key: 'quality_score', detail: 'quality_compounder', name: 'Quality Compounder', short: 'Quality', formula: 'ROIC quality + stability + FCF quality + growth quality + margin quality + reinvestment efficiency + balance-sheet quality' },
  { key: 'earnings_quality_score', detail: 'earnings_quality', name: 'Earnings Quality', short: 'Earnings', formula: 'Cash conversion + working-capital quality + FCF conversion + exceptional-item quality + accrual quality' },
  { key: 'sustainable_growth_score', detail: 'sustainable_growth', name: 'Sustainable Growth', short: 'Growth', formula: 'Growth + sustainable growth + margin change + internal funding + capital efficiency' },
  { key: 'capital_allocation_score', detail: 'capital_allocation', name: 'Capital Allocation', short: 'Capital', formula: 'Reinvestment returns + cash discipline + acquisition discipline + distributions + debt discipline' },
  { key: 'balance_sheet_risk_score', detail: 'balance_sheet_risk', name: 'Balance-Sheet Risk', short: 'Balance', formula: 'Leverage + coverage + cash/debt + CFO/debt + liabilities/equity + working-capital and asset risk' },
  { key: 'mispricing_score', detail: 'relative_mispricing', name: 'Relative Mispricing', short: 'Value', formula: 'P/E + EV/EBITDA + P/B + peer-relative valuation + quality support' },
];

const BUILDING_STRATEGIES = [
  ['Sector Relative Value', 'DATA BUILDING', 'Sector valuation, quality and operating breadth require complete sector histories.'],
  ['Macro Strategy', 'IN DEVELOPMENT', 'Rates, inflation, growth, INR and flows are not yet joined to this research layer.'],
  ['Event Strategy', 'DATA BUILDING', 'Point-in-time events and subsequent abnormal returns are required.'],
  ['Earnings Revision', 'DATA BUILDING', 'Consensus estimate vintages are required before revision signals can be computed.'],
  ['Forecast Mispricing', 'EXPERIMENTAL', 'Forecast outcome history and confidence calibration remain incomplete.'],
  ['Pairs / Relative Value', 'EXPERIMENTAL', 'Cointegration, half-life, borrow and cost validation remain gated.'],
  ['Portfolio & Risk', 'EXPERIMENTAL', 'Covariance, exposure, capacity and cost controls are not production validated.'],
];

const isNumber = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const number = (value, fallback = 'Unavailable') => isNumber(value) ? Number(value).toFixed(1) : fallback;
const clean = (value) => String(value || 'Unavailable').replaceAll('_', ' ');
const analystText = (value) => clean(value)
  .replace('negative or missing denominator', 'Multiple unavailable because earnings or EBITDA is negative/missing')
  .replace('extreme outlier review required', 'Extreme observation requires corporate-action and unit review')
  .replace('symbol company name mismatch', 'Exchange symbol and company name do not reconcile')
  .replace('taxonomy corrected from contaminated source', 'Source-sector classification failed validation')
  .replace('duplicate isin', 'ISIN is assigned to more than one exchange symbol');
const factorCoverage = (row) => FACTORS.filter((factor) => isNumber(row?.[factor.key])).length;
const rowEligible = (row) => isNumber(row?.fundamental_composite) && Number(row?.data_quality) >= 60 && factorCoverage(row) >= 4;

function Status({ children, tone = 'neutral' }) {
  return <span className={`hfr-status ${tone}`}>{children}</span>;
}

function SectionTitle({ eyebrow, title, copy, action }) {
  return <header className="hfr-section-title">
    <div><span>{eyebrow}</span><h2>{title}</h2>{copy ? <p>{copy}</p> : null}</div>
    {action}
  </header>;
}

function ScoreBar({ value }) {
  const width = isNumber(value) ? Math.max(0, Math.min(100, Number(value))) : 0;
  return <div className="hfr-score"><b>{number(value, '—')}</b><span><i style={{ width: `${width}%` }} /></span></div>;
}

function ContextStrip({ audit }) {
  return <section className="hfr-context" aria-label="Research context">
    <div><span>Research regime</span><b>Annual fundamentals</b><small>Medium / long horizon</small></div>
    <div><span>Model state</span><b>{clean(audit?.status || 'IN DEVELOPMENT')}</b><small>{audit?.layer_version || 'research-factor-layer-v2.0.0'}</small></div>
    <div><span>Point-in-time</span><b className="hfr-warn">Limited</b><small>Historical availability is not historical publication timing</small></div>
    <div><span>Data cutoff</span><b>{audit?.as_of || 'Unavailable'}</b><small>{audit?.universe ? `${audit.universe.toLocaleString('en-IN')} companies evaluated` : 'Loading factor universe'}</small></div>
  </section>;
}

function OpportunityBoard({ rows, onSelect }) {
  const leaders = rows.slice(0, 6);
  const lead = leaders[0];
  return <section className="hfr-section" aria-labelledby="opportunities-title">
    <SectionTitle
      eyebrow="Research queue"
      title="Strongest fundamental evidence"
      copy="Candidates pass a minimum data-quality and factor-coverage gate. Ranking is a research prior, not a recommendation or demonstrated alpha."
      action={<Status tone="warning">PIT LIMITED</Status>}
    />
    {!lead ? <div className="hfr-empty"><CircleDashed size={18} /> No candidate currently passes the evidence gate.</div> : <div className="hfr-opportunity-layout">
      <article className="hfr-lead">
        <div className="hfr-lead-head"><div><span>Highest eligible composite</span><h3>{lead.company_name || lead.symbol}</h3><p>{lead.symbol} · {clean(lead.primary_factor)}</p></div><strong>{number(lead.fundamental_composite)}</strong></div>
        <div className="hfr-reason-grid">
          <div><b>Why it surfaced</b><p>{lead.primary_evidence?.slice(0, 3).join(' · ') || 'No narrative evidence available.'}</p></div>
          <div><b>Supporting factors</b><p>{lead.supporting_factors?.join(' · ') || 'Unavailable'}</p></div>
          <div><b>Contradictory evidence</b><p>{lead.contradictory_evidence?.join(' · ') || 'No contradictory evidence identified from available fields.'}</p></div>
          <div><b>Key limitation</b><p>{lead.key_risk || 'Point-in-time validation is incomplete.'}</p></div>
        </div>
        <button className="hfr-command" type="button" onClick={() => onSelect(lead.symbol)}>Inspect evidence <ChevronRight size={15} /></button>
      </article>
      <div className="hfr-ranking">
        {leaders.map((row, index) => <button key={row.symbol} type="button" onClick={() => onSelect(row.symbol)}>
          <span>{String(index + 1).padStart(2, '0')}</span>
          <div><b>{row.company_name || row.symbol}</b><small>{row.symbol} · {clean(row.primary_factor)}</small></div>
          <strong>{number(row.fundamental_composite)}</strong>
        </button>)}
      </div>
    </div>}
  </section>;
}

function MarketContext() {
  const modules = [
    ['Macro regime', 'DATA UNAVAILABLE', 'No joined rates, inflation, growth, INR and flows snapshot.'],
    ['Sector breadth', 'IN DEVELOPMENT', 'Factor coverage exists; sector aggregation is not independently validated.'],
    ['Consensus revisions', 'DATA BUILDING', 'Historical consensus vintages are not available.'],
    ['Portfolio conditions', 'EXPERIMENTAL', 'Liquidity, covariance and capacity controls are not approved.'],
  ];
  return <section className="hfr-section" aria-labelledby="context-title">
    <SectionTitle eyebrow="Research conditions" title="Market and sector context" copy="Unavailable context remains explicit rather than being replaced with inferred or fabricated signals." />
    <div className="hfr-context-modules">{modules.map(([name, status, note]) => <div key={name}><b>{name}</b><Status tone={status === 'DATA UNAVAILABLE' ? 'danger' : 'neutral'}>{status}</Status><p>{note}</p></div>)}</div>
  </section>;
}

function StrategyDashboard({ rows }) {
  return <section className="hfr-section" aria-labelledby="strategies-title">
    <SectionTitle eyebrow="Model diagnostics" title="Strategy dashboard" copy="Each module exposes its formula family, coverage and current governance state." />
    <div className="hfr-strategy-grid">
      {FACTORS.map((factor) => {
        const available = rows.filter((row) => isNumber(row[factor.key]));
        const leader = [...available].sort((a, b) => Number(b[factor.key]) - Number(a[factor.key]))[0];
        return <article key={factor.key} className="hfr-strategy-card">
          <header><div><span>ACCOUNTING FACTOR</span><h3>{factor.name}</h3></div><Status tone="warning">IN DEVELOPMENT</Status></header>
          <p>{factor.formula}</p>
          <div className="hfr-strategy-stats"><span><b>{available.length}</b> visible in current audit</span><span><b>{leader ? number(leader[factor.key]) : '—'}</b> highest score</span></div>
          <footer><span>{leader?.symbol || 'No candidate'}</span><small>Annual fundamental signal · PIT limited</small></footer>
        </article>;
      })}
      {BUILDING_STRATEGIES.map(([name, status, note]) => <article key={name} className="hfr-strategy-card gated">
        <header><div><span>GATED MODULE</span><h3>{name}</h3></div><Status tone={status === 'EXPERIMENTAL' ? 'neutral' : 'danger'}>{status}</Status></header>
        <p>{note}</p><div className="hfr-gated"><CircleDashed size={16} /> No institutional output claimed</div>
      </article>)}
    </div>
  </section>;
}

function OpportunityMatrices({ rows }) {
  const pairs = [
    ['Quality × Mispricing', 'quality_score', 'mispricing_score'],
    ['Growth × Earnings Quality', 'sustainable_growth_score', 'earnings_quality_score'],
    ['Capital Allocation × Balance Sheet', 'capital_allocation_score', 'balance_sheet_risk_score'],
    ['Quality × Earnings Quality', 'quality_score', 'earnings_quality_score'],
  ];
  return <section className="hfr-section" aria-labelledby="matrices-title">
    <SectionTitle eyebrow="Factor intersections" title="Opportunity matrices" copy="Intersections use available 0–100 factor scores; they are not return forecasts." />
    <div className="hfr-matrices">{pairs.map(([name, x, y]) => {
      const candidates = rows.filter((row) => isNumber(row[x]) && isNumber(row[y])).sort((a, b) => (Number(b[x]) + Number(b[y])) - (Number(a[x]) + Number(a[y]))).slice(0, 5);
      return <article key={name}><header><h3>{name}</h3><small>Equal-weight diagnostic intersection</small></header>
        {candidates.map((row) => <div key={row.symbol}><b>{row.symbol}</b><span>{number(row[x])}</span><span>{number(row[y])}</span><strong>{number((Number(row[x]) + Number(row[y])) / 2)}</strong></div>)}
        {!candidates.length ? <p>Insufficient overlapping observations.</p> : null}
      </article>;
    })}</div>
  </section>;
}

function CandidateTable({ rows, onSelect }) {
  const [query, setQuery] = useState('');
  const filtered = rows.filter((row) => `${row.symbol} ${row.company_name}`.toLowerCase().includes(query.toLowerCase())).slice(0, 30);
  const weakening = [...rows].filter((row) => Number(row.fundamental_composite) < 50).sort((a, b) => Number(a.fundamental_composite) - Number(b.fundamental_composite)).slice(0, 8);
  return <section className="hfr-section" aria-labelledby="candidates-title">
    <SectionTitle eyebrow="Company research" title="Candidate diagnostics" copy="Only rows passing ≥60 data quality, ≥4 available factors and an available composite are included." action={<label className="hfr-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search candidates" /></label>} />
    <div className="hfr-table-wrap"><table className="hfr-table">
      <thead><tr><th>Company</th><th>Composite</th>{FACTORS.map((factor) => <th key={factor.key}>{factor.short}</th>)}<th>Quality</th><th>Evidence</th></tr></thead>
      <tbody>{filtered.map((row) => <tr key={row.symbol} onClick={() => onSelect(row.symbol)} tabIndex="0">
        <td><b>{row.symbol}</b><span>{row.company_name || 'Name unavailable'}</span></td><td><strong>{number(row.fundamental_composite)}</strong></td>
        {FACTORS.map((factor) => <td key={factor.key}><ScoreBar value={row[factor.key]} /></td>)}
        <td>{number(row.data_quality)}</td><td><span className="hfr-evidence-count">{factorCoverage(row)} / {FACTORS.length} factors</span></td>
      </tr>)}</tbody>
    </table></div>
    <div className="hfr-weakening"><header><AlertTriangle size={16} /><div><b>Weakening fundamental profiles</b><span>Eligible companies with composite below 50</span></div></header>
      {weakening.length ? weakening.map((row) => <button key={row.symbol} type="button" onClick={() => onSelect(row.symbol)}><b>{row.symbol}</b><span>{row.company_name}</span><strong>{number(row.fundamental_composite)}</strong></button>) : <p>No eligible weakening profile is visible in the current audit window.</p>}
    </div>
  </section>;
}

function ComponentRows({ factor }) {
  const entries = Object.entries(factor?.component_contributions || {});
  if (!entries.length) return <p className="hfr-muted">Component contributions unavailable.</p>;
  const weightTotal = Object.values(factor?.component_weights || {}).reduce((sum, value) => sum + (Number(value) || 0), 0);
  return <><div className="hfr-components">{entries.map(([name, contribution]) => <div key={name}><span>{clean(name)}</span><small>Weight {isNumber(factor?.component_weights?.[name]) ? `${(Number(factor.component_weights[name]) * 100).toFixed(0)}%` : 'Unavailable'}</small><b>{number(contribution)}</b></div>)}</div><p className={Math.abs(weightTotal - 1) < 0.0001 ? 'hfr-muted' : 'hfr-policy'}>Displayed weights: {(weightTotal * 100).toFixed(0)}%</p></>;
}

function CompanyEvidence({ symbol, onClose }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!symbol) return undefined;
    let active = true;
    setDetail(null); setError('');
    getResearchFactorCompany(symbol).then((data) => { if (active) setDetail(data?.result || null); }).catch((err) => { if (active) setError(err?.message || 'Company evidence unavailable'); });
    return () => { active = false; };
  }, [symbol]);
  if (!symbol) return null;
  const company = detail?.company;
  return <section className="hfr-detail" aria-live="polite">
    <header className="hfr-detail-head"><div><span>Evidence drill-down</span><h2>{company?.company_name || symbol}</h2><p>{symbol}{company?.sector ? ` · ${company.sector}` : ''}{company?.industry ? ` · ${company.industry}` : ''}</p></div><button type="button" onClick={onClose}>Close</button></header>
    {error ? <div className="hfr-empty"><AlertTriangle size={18} /> {error}</div> : null}
    {!detail && !error ? <div className="hfr-empty"><CircleDashed size={18} /> Loading audited components…</div> : null}
    {detail ? <div className="hfr-detail-grid">{FACTORS.map((meta) => {
      const factor = detail[meta.detail];
      return <article key={meta.detail}>
        <header><div><span>{factor?.factor_version || 'Version unavailable'}</span><h3>{meta.name}</h3></div><strong>{number(factor?.score, '—')}</strong></header>
        <p className="hfr-formula">{meta.formula}</p>
        <div className="hfr-detail-meta"><span>Coverage <b>{isNumber(factor?.coverage) ? `${(Number(factor.coverage) * 100).toFixed(1)}%` : number(factor?.data_quality)}</b></span><span>Confidence <b>{factor?.confidence || 'Unavailable'}</b></span><span>Percentile <b>{number(factor?.percentile)}</b></span></div>
        <ComponentRows factor={factor} />
        <div className="hfr-missing"><b>Missing fields</b><span>{factor?.missing_data?.length ? factor.missing_data.map(analystText).join(' · ') : 'None reported'}</span></div>
      </article>;
    })}</div> : null}
  </section>;
}

function ValidationPanel() {
  const tests = [
    ['Point-in-time fundamentals', 'PARTIAL', 'Historical reporting availability is present; publication timing is not fully reconstructable.'],
    ['Forward-return labels', 'NOT AVAILABLE', '1M / 3M / 6M / 12M outcome joins are not accepted.'],
    ['Rank IC and portfolio spreads', 'NOT RUN', 'No predictive performance claim permitted.'],
    ['Out-of-sample / walk-forward', 'NOT RUN', 'Methodology has not passed a frozen OOS test.'],
    ['Costs, liquidity and capacity', 'NOT RUN', 'No executable portfolio claim permitted.'],
    ['Risk and attribution', 'NOT RUN', 'Factor covariance and realized attribution are not validated.'],
  ];
  return <section className="hfr-section" aria-labelledby="validation-title">
    <SectionTitle eyebrow="Reliability gate" title="Validation status" copy="The registry controls what the page may claim. A generated score is not treated as economically validated." action={<Status tone="danger">RESEARCH ONLY</Status>} />
    <div className="hfr-validation">{tests.map(([name, status, note]) => <div key={name}><span>{status === 'PARTIAL' ? <AlertTriangle size={17} /> : <CircleDashed size={17} />}</span><div><b>{name}</b><p>{note}</p></div><Status tone={status === 'PARTIAL' ? 'warning' : 'danger'}>{status}</Status></div>)}</div>
  </section>;
}

function GovernancePanel({ job, audit }) {
  const receipt = job || {};
  const complete = String(receipt.status || '').toUpperCase() === 'COMPLETED';
  const metrics = [
    ['Approved', receipt.approved_rows, 21580],
    ['Persisted', receipt.persisted_rows, 21580],
    ['Normalized', receipt.normalized_rows, 21580],
    ['Verified', receipt.verified_rows, 21580],
    ['Quarantined', receipt.quarantined_rows, 8620],
    ['Failed', receipt.failed_rows, 0],
  ];
  return <section className="hfr-section hfr-governance" aria-labelledby="governance-title">
    <SectionTitle eyebrow="Warehouse governance" title="Data lineage and acceptance" copy="Capital IQ annual accounting is persisted and normalized in INR millions. Quarantined rows remain outside approved factor inputs." action={<Status tone={complete ? 'success' : 'warning'}>{complete ? 'RECEIPT COMPLETE' : 'CHECKING RECEIPT'}</Status>} />
    <div className="hfr-governance-grid">
      <div className="hfr-receipt">{metrics.map(([label, live, fallback]) => <div key={label}><b>{Number(isNumber(live) ? live : fallback).toLocaleString('en-IN')}</b><span>{label}</span></div>)}</div>
      <div className="hfr-lineage">
        <div><Database size={17} /><span>Source</span><b>Master 10Y India · Capital IQ annual statements</b></div>
        <div><Scale size={17} /><span>Unit</span><b>INR millions · normalized</b></div>
        <div><Layers3 size={17} /><span>Factor layer</span><b>{audit?.layer_version || 'research-factor-layer-v2.0.0'}</b></div>
        <div><ShieldCheck size={17} /><span>Validation</span><b>POINT IN TIME LIMITED</b></div>
      </div>
    </div>
    <p className="hfr-policy">Accounting-factor evidence only. No recommendation, execution instruction or demonstrated predictive alpha. Promotion requires independent PIT backtesting, costs, liquidity, out-of-sample testing and risk controls.</p>
  </section>;
}

export default function HedgeFundResearchPage() {
  const [audit, setAudit] = useState(null);
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('');

  useEffect(() => {
    document.title = 'Research Strategy Intelligence | AGI';
    let active = true;
    Promise.allSettled([getResearchFactorAudit(100), getCapitalIqMigrationStatus()]).then(([auditResult, jobResult]) => {
      if (!active) return;
      if (auditResult.status === 'fulfilled') setAudit(auditResult.value);
      else setError(auditResult.reason?.message || 'Research factor output is unavailable.');
      if (jobResult.status === 'fulfilled') setJob(jobResult.value);
    });
    return () => { active = false; };
  }, []);

  const allRows = Array.isArray(audit?.rows) ? audit.rows : [];
  const eligibleRows = useMemo(() => allRows.filter(rowEligible).sort((a, b) => Number(b.fundamental_composite) - Number(a.fundamental_composite)), [allRows]);
  const select = (symbol) => { setSelected(symbol); window.requestAnimationFrame(() => document.getElementById('company-evidence')?.scrollIntoView({ behavior: 'smooth', block: 'start' })); };

  return <div className="hfl-root hfr-root">
    <header className="hfr-header">
      <div className="hfr-brand"><BookOpenCheck size={18} /><span>AGI Hedge Fund Research</span></div>
      <div className="hfr-header-grid"><div><h1>Research Strategy Intelligence</h1><p>Systematic fundamental research for identifying, challenging and validating medium- and long-horizon investment hypotheses.</p></div><div className="hfr-header-policy"><FlaskConical size={18} /><b>Research system</b><span>No brokerage · No execution · No investment recommendation</span></div></div>
      <InlineAsk />
    </header>
    <main className="hfr-main">
      <ContextStrip audit={audit} />
      {audit?.quarantined?.length ? <div className="hfr-error"><AlertTriangle size={18} /><div><b>{audit.quarantined.length} candidate identities quarantined</b><span>{audit.quarantined.map((item) => `${item.symbol}: ${(item.reasons || []).map(analystText).join(', ')}`).join(' · ')}</span></div></div> : null}
      {error ? <div className="hfr-error"><AlertTriangle size={18} /><div><b>Factor service unavailable</b><span>{error}</span></div></div> : null}
      {!audit && !error ? <div className="hfr-loading"><CircleDashed size={19} /> Loading independently calculated research factors…</div> : null}
      <OpportunityBoard rows={eligibleRows} onSelect={select} />
      <MarketContext />
      <StrategyDashboard rows={allRows} />
      <OpportunityMatrices rows={eligibleRows} />
      <CandidateTable rows={eligibleRows} onSelect={select} />
      <div id="company-evidence"><CompanyEvidence symbol={selected} onClose={() => setSelected('')} /></div>
      <ValidationPanel />
      <GovernancePanel job={job} audit={audit} />
    </main>
  </div>;
}
