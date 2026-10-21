import { useEffect, useState } from 'react';
import { getCoverageHealth } from '@/lib/intelligenceApi';
import {
  getUpstoxBootstrapStatus,
} from '@/lib/upstoxBootstrapApi';
import './coverageHealth.css';

function fmt(v, digits = 1) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') {
    return Number.isInteger(v) && digits === 0 ? String(v) : v.toFixed(digits);
  }
  return String(v);
}

function Bar({ pct }) {
  const width = Math.max(0, Math.min(100, Number(pct) || 0));
  return (
    <div className="ich-bar" aria-hidden>
      <span style={{ width: `${width}%` }} />
    </div>
  );
}

function LayerRow({ name, pct, covered, universe }) {
  return (
    <div className="ich-layer">
      <div className="ich-layer-head">
        <span className="ich-layer-name">{name}</span>
        <span className="ich-layer-pct">{pct != null ? `${fmt(pct, 0)}%` : '—'}</span>
      </div>
      <Bar pct={pct} />
      {covered != null && universe != null ? (
        <div className="ich-layer-meta">{fmt(covered, 0)} / {fmt(universe, 0)}</div>
      ) : null}
    </div>
  );
}

function MetricList({ title, items }) {
  if (!items?.length) return null;
  return (
    <div className="ich-block">
      <h4>{title}</h4>
      <ul className="ich-metric-list">
        {items.map(([label, pct]) => (
          <li key={label}>
            <span>{label}</span>
            <strong>{pct != null ? `${fmt(pct, 0)}%` : '—'}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function CoverageHealthPanel() {
  const [pack, setPack] = useState(null);
  const [bootstrap, setBootstrap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getCoverageHealth().catch((err) => {
        throw err;
      }),
      getUpstoxBootstrapStatus().catch(() => null),
    ])
      .then(([health, boot]) => {
        if (cancelled) return;
        setPack(health);
        setBootstrap(boot);
        setError(health?.ok ? null : health?.error || 'coverage unavailable');
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'coverage health failed');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <section className="ich-panel hint">Loading coverage health…</section>;
  }
  if (error && !pack?.ok) {
    return <section className="ich-panel hint">Coverage health unavailable — {error}</section>;
  }
  if (!pack?.ok) return null;

  const dash = pack.dashboard || [];
  const dataLayers = pack.data_coverage?.layers || {};
  const metricMap = pack.metric_coverage?.metrics || {};
  const intel = pack.intelligence_coverage?.layers || {};
  const research = pack.research_coverage || {};
  const residual = pack.residual_gap || {};
  const valuation = pack.valuation_coverage || {};
  const summary = bootstrap?.summary || {};
  const queue = bootstrap?.queue || {};

  const dataItems = Object.entries(dataLayers).map(([k, v]) => [
    k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    v,
  ]);
  const metricItems = Object.values(metricMap).map((m) => [m.label || 'Metric', m.pct]);
  const intelItems = Object.entries(intel).map(([k, v]) => [
    k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    v,
  ]);

  return (
    <section className="ich-panel">
      <div className="ich-head">
        <div>
          <div className="ich-eyebrow">Coverage Health</div>
          <h3>Institutional coverage</h3>
          <p>
            Primary KPI is valuation applicability (VPAE) — not PE presence.
            {valuation.covered != null ? (
              <> {fmt(valuation.covered, 0)} / {fmt(valuation.expected, 0)} ({fmt(valuation.pct, 1)}%).</>
            ) : null}
          </p>
        </div>
      </div>

      <div className="ich-dashboard">
        {dash.map((row) => (
          <LayerRow
            key={row.name}
            name={row.name}
            pct={row.pct}
            covered={row.covered}
            universe={row.universe}
          />
        ))}
      </div>

      {(pack.hvie_pipeline_dashboard || []).length ? (
        <div className="ich-block" style={{ marginTop: '1rem' }}>
          <h4>HVIE Pipeline</h4>
          <p className="hint" style={{ marginTop: 0 }}>
            Full-universe completion stages — not just seeded count.
          </p>
          <ul className="ich-metric-list">
            {pack.hvie_pipeline_dashboard.map((row) => (
              <li key={row.name}>
                <span>{row.name}</span>
                <strong>{fmt(row.count, 0)}</strong>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="ich-grid">
        <MetricList title="Raw data" items={dataItems} />
        <MetricList title="Metric coverage" items={metricItems} />
        <MetricList title="Intelligence" items={intelItems} />

        <div className="ich-block">
          <h4>Research ready</h4>
          <div className="ich-stat-xl">{fmt(research.pct, 0)}%</div>
          <div className="ich-layer-meta">{fmt(research.research_ready, 0)} companies</div>
          <ul className="ich-metric-list">
            <li><span>Needs statements</span><strong>{fmt(research.needs_statements, 0)}</strong></li>
            <li><span>Needs history</span><strong>{fmt(research.needs_history, 0)}</strong></li>
            <li><span>Needs ratios</span><strong>{fmt(research.needs_ratios, 0)}</strong></li>
            <li><span>Needs review</span><strong>{fmt(research.needs_review, 0)}</strong></li>
          </ul>
        </div>

        <div className="ich-block">
          <h4>AGI valuation bootstrap</h4>
          {bootstrap?.ok ? (
            <>
              <ul className="ich-metric-list">
                <li>
                  <span>Universe</span>
                  <strong>{fmt(summary.companies || pack.universe?.companies, 0)}</strong>
                </li>
                <li>
                  <span>ISIN available</span>
                  <strong>{fmt(summary.isinAvailable ?? residual.isin_available, 0)}</strong>
                </li>
                <li>
                  <span>Bootstrapped</span>
                  <strong>
                    {fmt(
                      summary.completed
                      ?? queue.SUCCESS
                      ?? residual.with_upstox_key_ratios
                      ?? pack.data_coverage?.counts?.key_ratios,
                      0,
                    )}
                  </strong>
                </li>
                <li><span>Bootstrap coverage</span><strong>{summary.coverage != null ? `${fmt(summary.coverage, 1)}%` : '—'}</strong></li>
                <li><span>Pending</span><strong>{fmt(queue.PENDING ?? summary.remaining, 0)}</strong></li>
                <li><span>Retry</span><strong>{fmt(queue.RETRY, 0)}</strong></li>
                <li><span>Failed</span><strong>{fmt(queue.FAILED, 0)}</strong></li>
                <li><span>Missing ISIN</span><strong>{fmt(summary.missingIsin ?? residual.missing_isin, 0)}</strong></li>
                <li><span>ETA</span><strong>{summary.etaMinutes != null ? `${fmt(summary.etaMinutes, 0)} min` : '—'}</strong></li>
              </ul>
              {(summary.companies == null || Number(summary.companies) === 0) ? (
                <p className="hint">
                  Node bootstrap queue looks empty (often after redeploy). Warehouse residual /
                  key-ratio counts above are authoritative — do not rerun bootstrap solely from zeros.
                </p>
              ) : null}
            </>
          ) : (
            <p className="hint">Bootstrap status unavailable — open AGI Valuation Bootstrap for the live queue.</p>
          )}
        </div>

        <div className="ich-block">
          <h4>Residual gap</h4>
          <div className="ich-stat-xl">{fmt(residual.residual_missing, 0)}</div>
          <ul className="ich-metric-list">
            <li><span>Missing ISIN</span><strong>{fmt(residual.missing_isin, 0)}</strong></li>
            <li><span>No AGI fundamentals</span><strong>{fmt(residual.no_upstox_fundamentals, 0)}</strong></li>
            <li><span>Provider failure</span><strong>{fmt(residual.provider_failure, 0)}</strong></li>
            <li><span>Delisted</span><strong>{fmt(residual.delisted, 0)}</strong></li>
          </ul>
        </div>
      </div>

      {pack.vpae_integration?.example ? (
        <div className="ich-vpae-note">
          <strong>VPAE</strong>
          {' — '}
          {pack.vpae_integration.example.metric} unavailable ({pack.vpae_integration.example.reason})
          does not mean missing coverage when primary model is{' '}
          {pack.vpae_integration.example.primary_model}.
        </div>
      ) : null}
    </section>
  );
}
