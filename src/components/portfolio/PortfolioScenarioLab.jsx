import React, { useMemo, useState } from 'react';
import {
  PORTFOLIO_SCENARIO_PRESETS,
  buildPortfolioScenarioReport,
  runPortfolioScenario,
} from '../../lib/portfolioScenarioAnalysis';

const COLORS = {
  ink: '#152638',
  muted: '#687783',
  line: '#dbe3e6',
  paper: '#f8faf8',
  green: '#216957',
  red: '#a5483a',
  amber: '#936615',
  blue: '#245f75',
};

const percent = (value, digits = 1) => (
  value === null || value === undefined || !Number.isFinite(value)
    ? 'Unavailable'
    : `${value >= 0 ? '+' : ''}${(value * 100).toFixed(digits)}%`
);

const resolveSource = ({ holdings, foundation, institutionalFoundation, context, data, portfolio }) => {
  const source = foundation || institutionalFoundation || context || data || portfolio || {};
  const resolvedHoldings = holdings.length
    ? holdings
    : source.effectiveHoldings
      || source.effective_holdings
      || source.holdings
      || source.positions
      || source.assets
      || source.foundation?.holdings
      || [];
  return { source, holdings: Array.isArray(resolvedHoldings) ? resolvedHoldings : [] };
};

function Status({ status, reason }) {
  const color = status === 'available' ? COLORS.green : status === 'partial' ? COLORS.amber : COLORS.red;
  return (
    <div style={{ color, fontSize: 12, lineHeight: 1.5 }}>
      <strong style={{ textTransform: 'uppercase' }}>{status}</strong>
      {reason ? ` - ${reason}` : ''}
    </div>
  );
}

export default function PortfolioScenarioLab({
  holdings = [],
  foundation = null,
  institutionalFoundation = null,
  context = null,
  data = null,
  portfolio = null,
}) {
  const resolved = resolveSource({ holdings, foundation, institutionalFoundation, context, data, portfolio });
  const [scenarioId, setScenarioId] = useState(PORTFOLIO_SCENARIO_PRESETS[0].id);
  const scenario = PORTFOLIO_SCENARIO_PRESETS.find((item) => item.id === scenarioId)
    || PORTFOLIO_SCENARIO_PRESETS[0];
  const result = useMemo(
    () => runPortfolioScenario({ holdings: resolved.holdings, scenario }),
    [resolved.holdings, scenario],
  );
  const report = useMemo(() => buildPortfolioScenarioReport({
    holdings: resolved.holdings,
    portfolioName: resolved.source.name || resolved.source.portfolio_name || 'Client portfolio',
  }), [resolved.holdings, resolved.source.name, resolved.source.portfolio_name]);

  return (
    <section className="portfolio-scenario-report" style={{ background: COLORS.paper, border: `1px solid ${COLORS.line}`, color: COLORS.ink, marginTop: 24, padding: 'clamp(24px, 4vw, 54px)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div style={{ maxWidth: 760 }}>
          <div style={{ color: COLORS.green, fontSize: 11, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase' }}>Portfolio resilience</div>
          <h2 style={{ fontFamily: 'Georgia, serif', fontSize: 'clamp(32px, 5vw, 56px)', fontWeight: 400, lineHeight: 1, margin: '12px 0 16px' }}>
            Scenario testing
          </h2>
          <p style={{ color: COLORS.muted, lineHeight: 1.65, margin: 0 }}>
            Applies transparent shocks to known exposures and identifies the holdings driving the result. These are sensitivities, not predictions.
          </p>
        </div>
        <button
          type="button"
          onClick={() => window.print()}
          style={{ background: COLORS.ink, border: 0, color: '#fff', cursor: 'pointer', padding: '12px 18px' }}
        >
          Print client report
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 10, margin: '30px 0 24px' }}>
        {PORTFOLIO_SCENARIO_PRESETS.map((preset) => (
          <button
            type="button"
            key={preset.id}
            onClick={() => setScenarioId(preset.id)}
            style={{
              background: scenarioId === preset.id ? COLORS.ink : '#fff',
              border: `1px solid ${scenarioId === preset.id ? COLORS.ink : COLORS.line}`,
              color: scenarioId === preset.id ? '#fff' : COLORS.ink,
              cursor: 'pointer',
              padding: 16,
              textAlign: 'left',
            }}
          >
            <strong style={{ display: 'block', marginBottom: 6 }}>{preset.name}</strong>
            <span style={{ fontSize: 12, lineHeight: 1.4, opacity: 0.72 }}>{preset.description}</span>
          </button>
        ))}
      </div>

      <div style={{ background: '#fff', border: `1px solid ${COLORS.line}`, display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(230px, 0.65fr)', gap: 28, padding: 24 }}>
        <div>
          <Status status={result.status} reason={result.reason} />
          <h3 style={{ fontFamily: 'Georgia, serif', fontSize: 28, fontWeight: 400, margin: '12px 0 8px' }}>{result.scenario.name}</h3>
          <p style={{ color: COLORS.muted, lineHeight: 1.55, margin: 0 }}>{result.scenario.description}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 22, marginTop: 20 }}>
            <div>
              <div style={{ color: COLORS.muted, fontSize: 11, textTransform: 'uppercase' }}>Modeled impact</div>
              <strong style={{ color: result.modeledImpact !== null && result.modeledImpact < 0 ? COLORS.red : COLORS.green, fontFamily: 'Georgia, serif', fontSize: 36 }}>
                {percent(result.modeledImpact)}
              </strong>
            </div>
            <div>
              <div style={{ color: COLORS.muted, fontSize: 11, textTransform: 'uppercase' }}>Affected exposure</div>
              <strong style={{ fontFamily: 'Georgia, serif', fontSize: 30 }}>{percent(result.affectedWeight)}</strong>
            </div>
            <div>
              <div style={{ color: COLORS.muted, fontSize: 11, textTransform: 'uppercase' }}>Weight coverage</div>
              <strong style={{ fontFamily: 'Georgia, serif', fontSize: 30 }}>{result.coverage === null ? 'Unavailable' : `${(result.coverage * 100).toFixed(0)}%`}</strong>
            </div>
          </div>
        </div>
        <div style={{ borderLeft: `1px solid ${COLORS.line}`, paddingLeft: 22 }}>
          <div style={{ color: COLORS.muted, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Shock definition</div>
          {result.scenario.shocks.map((shock) => (
            <div key={`${shock.dimension}-${shock.target}`} style={{ borderBottom: `1px solid ${COLORS.line}`, display: 'flex', justifyContent: 'space-between', gap: 12, padding: '10px 0' }}>
              <span style={{ color: COLORS.muted }}>{shock.target.replace(/_/g, ' ')}</span>
              <strong style={{ color: shock.value < 0 ? COLORS.red : COLORS.green }}>{percent(shock.value, 0)}</strong>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 24 }}>
        <div style={{ color: COLORS.muted, fontSize: 11, letterSpacing: '0.12em', marginBottom: 10, textTransform: 'uppercase' }}>Largest modeled contributors</div>
        {!result.contributors.length ? (
          <div style={{ background: '#fff', border: `1px solid ${COLORS.line}`, color: COLORS.muted, padding: 20 }}>
            {result.status === 'unavailable' ? result.reason : 'No known holding is affected by this shock.'}
          </div>
        ) : result.contributors.slice(0, 8).map((holding) => (
          <div key={holding.id} style={{ background: '#fff', borderTop: `1px solid ${COLORS.line}`, display: 'grid', gridTemplateColumns: 'minmax(150px, 1fr) 120px 120px', gap: 16, padding: '13px 16px' }}>
            <span><strong>{holding.symbol || holding.name}</strong>{holding.symbol && holding.name !== holding.symbol ? <small style={{ color: COLORS.muted }}> - {holding.name}</small> : null}</span>
            <span style={{ color: COLORS.muted }}>Shock {percent(holding.holdingShock, 0)}</span>
            <strong style={{ color: holding.impact < 0 ? COLORS.red : COLORS.green, textAlign: 'right' }}>{percent(holding.impact, 2)}</strong>
          </div>
        ))}
      </div>

      <div style={{ borderTop: `1px solid ${COLORS.line}`, color: COLORS.muted, fontSize: 11, lineHeight: 1.55, marginTop: 26, paddingTop: 14 }}>
        {report.methodology} Data quality: {report.dataQuality.available} complete, {report.dataQuality.partial} partial, {report.dataQuality.unavailable} unavailable scenario results.
      </div>
    </section>
  );
}
