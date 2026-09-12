import { useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import {
  Activity,
  ArrowLeft,
  Calculator,
  Clock3,
  Database,
  FlaskConical,
  LockKeyhole,
  Radio,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import {
  getOptionsValidationDashboard,
  priceOptionsSnapshotAdmin,
} from '@/lib/optionsLabAdminApi';
import './optionsLab.css';

const INITIAL_INPUTS = {
  option_type: 'call',
  spot: '25000',
  strike: '25000',
  days_to_expiry: '7',
  risk_free_rate_pct: '5.5',
  dividend_yield_pct: '0',
  model_volatility_pct: '18',
  bid: '218',
  ask: '222',
  contract_multiplier: '75',
};

const numericFields = [
  'spot',
  'strike',
  'days_to_expiry',
  'risk_free_rate_pct',
  'dividend_yield_pct',
  'model_volatility_pct',
  'bid',
  'ask',
  'contract_multiplier',
];

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === '') return '--';
  const number = Number(value);
  if (!Number.isFinite(number)) return '--';
  return number.toLocaleString('en-IN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function InputField({ label, name, value, onChange, suffix, step = 'any' }) {
  return (
    <label className="ol-field">
      <span>{label}</span>
      <div className="ol-input-wrap">
        <input
          name={name}
          type="number"
          step={step}
          value={value}
          onChange={onChange}
          inputMode="decimal"
        />
        {suffix ? <em>{suffix}</em> : null}
      </div>
    </label>
  );
}

function Metric({ label, value, note, tone = '' }) {
  return (
    <article className={`ol-metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {note ? <small>{note}</small> : null}
    </article>
  );
}

function formatTimestamp(value) {
  if (!value) return 'Waiting for first collection';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export default function OptionsLab() {
  const [inputs, setInputs] = useState(INITIAL_INPUTS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [validation, setValidation] = useState(null);
  const [validationLoading, setValidationLoading] = useState(true);
  const [validationError, setValidationError] = useState('');

  const loadValidation = useCallback(async () => {
    setValidationLoading(true);
    setValidationError('');
    try {
      setValidation(await getOptionsValidationDashboard());
    } catch (err) {
      setValidationError(err?.message || 'Live validation evidence is unavailable.');
    } finally {
      setValidationLoading(false);
    }
  }, []);

  useEffect(() => {
    loadValidation();
  }, [loadValidation]);

  const update = (event) => {
    const { name, value } = event.target;
    setInputs((current) => ({ ...current, [name]: value }));
  };

  const calculate = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const payload = { ...inputs };
      numericFields.forEach((field) => {
        payload[field] = Number(inputs[field]);
      });
      setResult(await priceOptionsSnapshotAdmin(payload));
    } catch (err) {
      setError(err?.message || 'The local model could not calculate this option.');
    } finally {
      setLoading(false);
    }
  };

  const valuation = result?.valuation;
  const market = result?.market;
  const iv = result?.implied_volatility;
  const greeks = result?.greeks;
  const risk = result?.risk;
  const assessment = valuation?.assessment || 'model_only';
  const latestReport = validation?.latest_report?.report;
  const cumulative = latestReport?.cumulative || {};
  const daily = latestReport?.daily || {};
  const evidence = validation?.evidence || {};
  const worker = validation?.worker || {};

  return (
    <div className="ol-root">
      <Helmet>
        <title>Options Intelligence Lab | AGI</title>
        <meta
          name="description"
          content="Local European option pricing, implied volatility, Greeks and scenario analytics."
        />
      </Helmet>

      <header className="ol-hero">
        <div className="ol-shell">
          <Link className="ol-back" to="/admin">
            <ArrowLeft size={15} /> Admin control room
          </Link>
          <div className="ol-hero-grid">
            <div>
              <div className="ol-kicker"><LockKeyhole size={14} /> Administrator research instrument</div>
              <h1>Options Intelligence Lab</h1>
              <p>
                Frozen V1 conditional repricing, contract-level rolling IV and prospective
                validation from the live Upstox option chain. Execution remains disconnected.
              </p>
            </div>
            <div className="ol-model-stamp">
              <span>MODEL</span>
              <b>BSM / European</b>
              <small>agi-bsm-v1-local</small>
            </div>
          </div>
        </div>
      </header>

      <section className="ol-live-strip">
        <div className="ol-shell">
          <div className="ol-live-head">
            <div>
              <span className="ol-kicker"><Radio size={14} /> Prospective validation</span>
              <h2>Live evidence monitor</h2>
              <p>Every 15 minutes during NSE market hours. Daily report after 3:45 PM IST.</p>
            </div>
            <button onClick={loadValidation} disabled={validationLoading}>
              <RefreshCw size={15} className={validationLoading ? 'ol-spin' : ''} /> Refresh evidence
            </button>
          </div>
          {validationError ? <div className="ol-error">{validationError}</div> : null}
          <div className="ol-live-grid">
            <article>
              <span>Collector</span>
              <strong className={`ol-live-state ${worker.status || 'unknown'}`}>
                {(worker.status || 'starting').replaceAll('_', ' ')}
              </strong>
              <small><Clock3 size={12} /> {formatTimestamp(evidence.latest_captured_at)}</small>
            </article>
            <article>
              <span>Stored evidence</span>
              <strong>{formatNumber(evidence.snapshots, 0)} snapshots</strong>
              <small><Database size={12} /> {formatNumber(evidence.contracts, 0)} contracts · {formatNumber(evidence.observations, 0)} comparisons</small>
            </article>
            <article>
              <span>Observation-weighted MAPE</span>
              <strong>{cumulative.mape_pct == null ? '--' : `${formatNumber(cumulative.mape_pct)}%`}</strong>
              <small>Acceptance threshold &lt;3.00%</small>
            </article>
            <article>
              <span>Day-weighted MAPE</span>
              <strong>{cumulative.day_weighted_mape_pct == null ? '--' : `${formatNumber(cumulative.day_weighted_mape_pct)}%`}</strong>
              <small>{formatNumber(cumulative.trading_days || evidence.trading_days, 0)} / 60 minimum trading days</small>
            </article>
          </div>
          <div className="ol-validation-band">
            <div><span>Latest daily report</span><b>{validation?.latest_report?.report_date || 'Pending first market day'}</b></div>
            <div><span>Daily MAPE</span><b>{daily.mape_pct == null ? '--' : `${formatNumber(daily.mape_pct)}%`}</b></div>
            <div><span>MAE</span><b>{cumulative.mae_points == null ? '--' : `${formatNumber(cumulative.mae_points)} pts`}</b></div>
            <div><span>Within tolerance</span><b>{cumulative.within_tolerance_pct == null ? '--' : `${formatNumber(cumulative.within_tolerance_pct)}%`}</b></div>
            <div><span>Research status</span><b>{(validation?.model?.status || 'extended_validation_pending').replaceAll('_', ' ')}</b></div>
          </div>
        </div>
      </section>

      <main className="ol-shell ol-workbench">
        <form className="ol-panel ol-controls" onSubmit={calculate}>
          <div className="ol-panel-head">
            <div>
              <span className="ol-index">01</span>
              <h2>Contract snapshot</h2>
            </div>
            <span className="ol-source">Manual inputs</span>
          </div>

          <div className="ol-option-toggle" aria-label="Option type">
            {['call', 'put'].map((type) => (
              <button
                key={type}
                type="button"
                className={inputs.option_type === type ? 'active' : ''}
                onClick={() => setInputs((current) => ({ ...current, option_type: type }))}
              >
                {type}
              </button>
            ))}
          </div>

          <div className="ol-form-grid">
            <InputField label="Underlying spot" name="spot" value={inputs.spot} onChange={update} suffix="INR" />
            <InputField label="Strike" name="strike" value={inputs.strike} onChange={update} suffix="INR" />
            <InputField label="Days to expiry" name="days_to_expiry" value={inputs.days_to_expiry} onChange={update} suffix="days" />
            <InputField label="Model volatility" name="model_volatility_pct" value={inputs.model_volatility_pct} onChange={update} suffix="%" />
            <InputField label="Best bid" name="bid" value={inputs.bid} onChange={update} suffix="INR" />
            <InputField label="Best ask" name="ask" value={inputs.ask} onChange={update} suffix="INR" />
            <InputField label="Risk-free rate" name="risk_free_rate_pct" value={inputs.risk_free_rate_pct} onChange={update} suffix="%" />
            <InputField label="Dividend yield" name="dividend_yield_pct" value={inputs.dividend_yield_pct} onChange={update} suffix="%" />
            <InputField label="Contract multiplier" name="contract_multiplier" value={inputs.contract_multiplier} onChange={update} suffix="units" />
          </div>

          <button className="ol-calculate" type="submit" disabled={loading}>
            {loading ? <RefreshCw className="ol-spin" size={17} /> : <Calculator size={17} />}
            {loading ? 'Calculating' : 'Run local model'}
          </button>
          {error ? <div className="ol-error">{error}</div> : null}
        </form>

        <section className="ol-output" aria-live="polite">
          {!result ? (
            <div className="ol-empty-state">
              <Activity size={30} />
              <h2>Waiting for a contract</h2>
              <p>Run the sample snapshot to produce a complete, server-calculated risk sheet.</p>
            </div>
          ) : (
            <>
              <div className="ol-panel-head ol-results-head">
                <div>
                  <span className="ol-index">02</span>
                  <h2>Model readout</h2>
                </div>
                <span className={`ol-assessment ${assessment}`}>{assessment.replace('_', ' ')}</span>
              </div>

              <div className="ol-metrics">
                <Metric label="Model value" value={`₹${formatNumber(valuation.model_value)}`} note={`Market mid ₹${formatNumber(market.mid)}`} />
                <Metric label="Mid implied vol" value={`${formatNumber(iv.mid_pct)}%`} note={`Model input ${formatNumber(result.inputs.model_volatility_pct)}%`} tone="accent" />
                <Metric label="Delta" value={formatNumber(greeks.delta, 4)} note="Approximate price sensitivity" />
                <Metric label="Theta / day" value={`₹${formatNumber(greeks.theta_per_day)}`} note="Estimated daily time decay" tone={greeks.theta_per_day < 0 ? 'risk' : ''} />
              </div>

              <div className="ol-readout-grid">
                <article className="ol-card">
                  <div className="ol-card-title"><Activity size={16} /><h3>Volatility corridor</h3></div>
                  <div className="ol-iv-row"><span>Bid IV</span><b>{formatNumber(iv.bid_pct)}%</b></div>
                  <div className="ol-iv-row primary"><span>Mid IV</span><b>{formatNumber(iv.mid_pct)}%</b></div>
                  <div className="ol-iv-row"><span>Ask IV</span><b>{formatNumber(iv.ask_pct)}%</b></div>
                  <div className="ol-range-track"><i /><i /><i /></div>
                  <small>Calculated independently from each executable quote.</small>
                </article>

                <article className="ol-card">
                  <div className="ol-card-title"><ShieldCheck size={16} /><h3>Risk map</h3></div>
                  <div className="ol-risk-range">
                    <span>One-sigma range</span>
                    <strong>₹{formatNumber(risk.one_sigma_lower, 0)} - ₹{formatNumber(risk.one_sigma_upper, 0)}</strong>
                    <small>Expected move: approximately {formatNumber(risk.one_sigma_expected_move, 0)} points</small>
                  </div>
                  <div className="ol-greek-grid">
                    <div><span>Gamma</span><b>{formatNumber(greeks.gamma, 6)}</b></div>
                    <div><span>Vega</span><b>₹{formatNumber(greeks.vega_per_vol_point)}</b></div>
                    <div><span>Rho</span><b>₹{formatNumber(greeks.rho_per_rate_point)}</b></div>
                    <div><span>Spread</span><b>{formatNumber(market.spread_pct)}%</b></div>
                  </div>
                </article>
              </div>

              <article className="ol-card ol-scenarios">
                <div className="ol-card-title"><h3>Contract stress test</h3><span>P&amp;L versus current midpoint</span></div>
                <div className="ol-table-wrap">
                  <table>
                    <thead><tr><th>Scenario</th><th>Spot</th><th>Volatility</th><th>Option value</th><th>Contract P&amp;L</th></tr></thead>
                    <tbody>
                      {result.scenarios.map((scenario) => (
                        <tr key={scenario.label}>
                          <td>{scenario.label}</td>
                          <td>{scenario.spot_change_pct > 0 ? '+' : ''}{scenario.spot_change_pct}%</td>
                          <td>{scenario.volatility_change_points > 0 ? '+' : ''}{scenario.volatility_change_points} pts</td>
                          <td>₹{formatNumber(scenario.option_value)}</td>
                          <td className={scenario.pnl_per_contract >= 0 ? 'positive' : 'negative'}>
                            {scenario.pnl_per_contract >= 0 ? '+' : '-'}₹{formatNumber(Math.abs(scenario.pnl_per_contract), 0)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>

              {result.quality.warnings.length ? (
                <div className="ol-warnings">
                  {result.quality.warnings.map((warning) => <p key={warning}>{warning}</p>)}
                </div>
              ) : null}
            </>
          )}
        </section>
      </main>

      <section className="ol-method">
        <div className="ol-shell ol-method-grid">
          <div><span>Pricing</span><b>Black-Scholes-Merton</b><p>European exercise with continuous carry.</p></div>
          <div><span>Market basis</span><b>Bid / midpoint / ask</b><p>LTP is not used when an executable spread exists.</p></div>
          <div><span>Safety</span><b>No-arbitrage bounds</b><p>Invalid quotes do not receive a confident IV.</p></div>
          <div><span>Current scope</span><b>Live validation only</b><p>Upstox feed and durable evidence are connected. Signals and orders are not.</p></div>
        </div>
      </section>

      <footer className="ol-foot">
        <div className="ol-shell">Research analytics only. Model outputs are estimates, not forecasts, recommendations, or guarantees of executable prices.</div>
      </footer>
    </div>
  );
}
