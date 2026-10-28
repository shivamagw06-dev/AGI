import { useEffect, useState } from 'react';
import { buildInstitutionalPortfolioReport } from '../../lib/institutionalPortfolioEngine';
import {
  loadInstitutionalPortfolioContext,
  persistInstitutionalPortfolioReport,
} from '../../lib/institutionalPortfolioStore';
import './institutionalPortfolio.css';

function formatPercent(value, digits = 1) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(digits)}%` : 'Not calculable';
}

function formatWeight(value, digits = 1) {
  return Number.isFinite(value) ? `${value.toFixed(digits)}%` : 'Unavailable';
}

function Metric({ label, value, note }) {
  return (
    <div className="ipi-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {note ? <small>{note}</small> : null}
    </div>
  );
}

function Status({ value }) {
  return <span className={`ipi-status ipi-status--${value || 'unknown'}`}>{String(value || 'unknown').replaceAll('_', ' ')}</span>;
}

export default function InstitutionalPortfolioPanel({ portfolioId = null }) {
  const [state, setState] = useState({ loading: true, report: null, error: null, persistence: null });

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const context = await loadInstitutionalPortfolioContext(portfolioId);
        const report = buildInstitutionalPortfolioReport(context);
        if (!active) return;
        setState({ loading: false, report, error: null, persistence: 'saving' });
        try {
          await persistInstitutionalPortfolioReport(context.portfolio.id, report);
          if (active) setState((current) => ({ ...current, persistence: 'stored' }));
        } catch (error) {
          if (active) setState((current) => ({ ...current, persistence: `not stored: ${error.message}` }));
        }
      } catch (error) {
        if (active) setState({ loading: false, report: null, error: error.message, persistence: null });
      }
    }
    load();
    return () => { active = false; };
  }, [portfolioId]);

  if (state.loading) {
    return <section className="ipi-shell ipi-loading" aria-busy="true">Building the evidence-aware portfolio view...</section>;
  }
  if (state.error) {
    return (
      <section className="ipi-shell ipi-error">
        <strong>Institutional analysis unavailable</strong>
        <p>{state.error}</p>
      </section>
    );
  }

  const report = state.report;
  const topScenario = [...report.scenarios].sort((a, b) => a.impactPct - b.impactPct)[0];
  const highAlerts = report.alerts.filter((alert) => alert.severity === 'high').length;

  return (
    <section className="ipi-shell" aria-labelledby="ipi-title">
      <header className="ipi-hero">
        <div>
          <p className="ipi-kicker">AGI INSTITUTIONAL DECISION LAYER</p>
          <h2 id="ipi-title">Portfolio resilience, evidence and policy</h2>
          <p>Transparent portfolio diagnostics modelled on institutional workflows. Missing evidence is never replaced with a synthetic answer.</p>
        </div>
        <div className="ipi-grade" aria-label={`Data quality grade ${report.coverage.grade}`}>
          <span>Evidence grade</span>
          <strong>{report.coverage.grade}</strong>
          <small>{report.coverage.score.toFixed(0)}/100</small>
        </div>
      </header>

      <div className="ipi-ribbon">
        <span>Engine {report.engineVersion}</span>
        <span>{new Date(report.generatedAt).toLocaleString()}</span>
        <span>{state.persistence}</span>
      </div>

      <div className="ipi-grid ipi-grid--metrics">
        <Metric label="Snapshot history" value={`${report.coverage.snapshotCount} days`} note={report.performance.status === 'calculated' ? 'Performance calculable' : 'Still accumulating'} />
        <Metric label="Fresh price coverage" value={formatWeight(report.coverage.freshPricePct)} note="Sourced, no older than four days" />
        <Metric label="Canonical identity" value={formatWeight(report.coverage.identityPct)} note="Weighted by investable value" />
        <Metric label="High-priority alerts" value={String(highAlerts)} note="Evidence and risk exceptions" />
      </div>

      <div className="ipi-grid ipi-grid--two">
        <article className="ipi-card">
          <div className="ipi-card__heading">
            <div><p>REALIZED RISK</p><h3>Performance discipline</h3></div>
            <Status value={report.performance.status} />
          </div>
          {report.performance.status === 'calculated' ? (
            <div className="ipi-stat-list">
              <Metric label="Time-weighted return" value={formatPercent(report.performance.twr)} />
              <Metric label="Annualized volatility" value={formatPercent(report.performance.annualizedVolatility)} />
              <Metric label="Maximum drawdown" value={formatPercent(report.performance.maxDrawdown)} />
              <Metric label="Sharpe ratio" value={report.performance.sharpe?.toFixed(2) || 'Not calculable'} />
              <Metric label="Benchmark alignment" value={report.performance.benchmark.status.replaceAll('_', ' ')} />
              <Metric label="Historical VaR" value={report.performance.tailRiskStatus === 'calculated' ? formatPercent(report.performance.historicalVar95) : 'Needs 60 days'} />
            </div>
          ) : <p className="ipi-empty">{report.performance.reason}</p>}
        </article>

        <article className="ipi-card ipi-card--scenario">
          <div className="ipi-card__heading">
            <div><p>WHAT-IF</p><h3>Scenario resilience</h3></div>
            <span className="ipi-impact">{formatPercent(topScenario?.impactPct)}</span>
          </div>
          <p className="ipi-caption">Most adverse built-in diagnostic: {topScenario?.name}. These are linear exposure shocks, not price forecasts.</p>
          <div className="ipi-scenarios">
            {report.scenarios.map((scenario) => (
              <div key={scenario.id}>
                <span>{scenario.name}<small>{scenario.confidence} mapping confidence</small></span>
                <strong className={scenario.impactPct < 0 ? 'negative' : 'positive'}>{formatPercent(scenario.impactPct)}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="ipi-card">
          <div className="ipi-card__heading">
            <div><p>POLICY</p><h3>Allocation drift</h3></div>
            <Status value={report.policy.status} />
          </div>
          {report.policy.status === 'calculated' ? (
            <div className="ipi-scenarios">
              {report.policy.drift.map((row) => (
                <div key={row.assetType}>
                  <span>{row.assetType.replaceAll('_', ' ')}<small>Target {formatWeight(row.targetPct)}</small></span>
                  <strong>{row.driftPct > 0 ? '+' : ''}{formatWeight(row.driftPct)}</strong>
                </div>
              ))}
            </div>
          ) : <p className="ipi-empty">{report.policy.reason} AGI will not invent a target portfolio.</p>}
        </article>

        <article className="ipi-card">
          <div className="ipi-card__heading">
            <div><p>X-RAY</p><h3>Fund look-through</h3></div>
            <Status value={report.lookThrough.status} />
          </div>
          <Metric label="Fund and ETF weight" value={formatWeight(report.lookThrough.fundWeightPct)} />
          <Metric label="Resolved look-through" value={formatWeight(report.lookThrough.resolvedFundWeightPct)} />
          {report.lookThrough.topUnderlyingHoldings.length ? (
            <div className="ipi-underlying">
              {report.lookThrough.topUnderlyingHoldings.slice(0, 6).map((row) => (
                <span key={row.instrumentId}>{row.symbol}<strong>{formatWeight(row.weightPct)}</strong></span>
              ))}
            </div>
          ) : <p className="ipi-empty">{report.lookThrough.reason || 'No fund look-through is required.'}</p>}
        </article>
      </div>

      <article className="ipi-card ipi-card--wide">
        <div className="ipi-card__heading">
          <div><p>EXCEPTION MONITOR</p><h3>What requires attention</h3></div>
          <span>{report.alerts.length} active</span>
        </div>
        {report.alerts.length ? (
          <div className="ipi-alerts">
            {report.alerts.map((alert) => (
              <div key={alert.alertKey} className={`ipi-alert ipi-alert--${alert.severity}`}>
                <Status value={alert.severity} />
                <span><strong>{alert.title}</strong><small>{alert.detail}</small></span>
              </div>
            ))}
          </div>
        ) : <p className="ipi-empty">No evidence or policy exceptions are active.</p>}
      </article>

      <footer className="ipi-methodology">
        <strong>Methodology boundary</strong>
        <span>Brinson attribution: {report.brinsonAttribution.status.replaceAll('_', ' ')}</span>
        <span>Calibrated factor risk: {report.factorRisk.status.replaceAll('_', ' ')}</span>
        <span>Corporate actions: {report.corporateActions.status.replaceAll('_', ' ')}</span>
        <p>AGI does not represent these diagnostics as licensed Bloomberg, Barra, Aladdin or Morningstar analytics, and does not present asset-level drift as personalized investment advice.</p>
      </footer>
    </section>
  );
}

