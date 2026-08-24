import { useCallback, useEffect, useMemo, useState } from 'react';
import PageShell from '@/components/Layout/PageShell';
import DeskResearchFeed from '@/components/Research/DeskResearchFeed';
import { getFxIntelligence } from '@/lib/fxApi';
import './economicsPage.css';

const HORIZONS = [
  { key: 'd1', label: '1D' },
  { key: 'w1', label: '1W' },
  { key: 'm1', label: '1M' },
];

const SCENARIO_STEPS = [1, 2, 5];

function signedPct(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return `${number > 0 ? '+' : ''}${number.toFixed(2)}%`;
}

function price(value, decimals = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(number);
}

function freshTime(value) {
  if (!value) return 'Awaiting update';
  return new Date(value).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function moveTone(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || Math.abs(number) < 0.03) return 'flat';
  return number > 0 ? 'up' : 'down';
}

function Sparkline({ values = [], tone = 'up' }) {
  if (values.length < 2) return <div className="fx-spark-empty">No chart yet</div>;
  const width = 420;
  const height = 124;
  const low = Math.min(...values);
  const high = Math.max(...values);
  const spread = high - low || 1;
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - low) / spread) * (height - 16) - 8;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const areaPoints = `0,${height} ${points} ${width},${height}`;

  return (
    <svg className={`fx-spark fx-spark--${tone}`} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="One month price path">
      <polygon points={areaPoints} className="fx-spark-area" />
      <line x1="0" y1={height / 2} x2={width} y2={height / 2} className="fx-spark-mid" />
      <polyline points={points} fill="none" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function HeatCell({ row, horizon, active, onSelect }) {
  const move = Number(row?.returns?.[horizon]);
  const intensity = Number.isFinite(move) ? Math.min(Math.abs(move) / 1.75, 1) : 0;
  const tone = moveTone(move);
  const background =
    tone === 'up'
      ? `rgba(32, 199, 164, ${0.1 + intensity * 0.42})`
      : tone === 'down'
        ? `rgba(255, 111, 97, ${0.1 + intensity * 0.42})`
        : 'rgba(255, 255, 255, 0.05)';

  return (
    <button
      type="button"
      className={`fx-heat-cell fx-tone-${tone} ${active ? 'is-active' : ''}`}
      style={{ background }}
      onClick={() => onSelect(row.pair)}
      aria-pressed={active}
    >
      <div className="fx-heat-topline">
        <span>{row.pair}</span>
        <small>{row.region}</small>
      </div>
      <strong>{signedPct(move)}</strong>
      <div className="fx-heat-price">
        {price(row.price, row.decimals)}
        <span>{row.base} per {row.quote}</span>
      </div>
      <small className="fx-heat-action">Open pair</small>
    </button>
  );
}

function DriverCard({ row, horizon }) {
  const move = Number(row?.returns?.[horizon]);
  const tone = moveTone(move);
  const interpretations = {
    'Dollar index': move >= 0 ? 'Broad dollar demand is firmer.' : 'Broad dollar pressure is easing.',
    'Brent crude': move >= 0 ? 'India import-cost pressure is rising.' : 'India import-cost pressure is easing.',
    'US 10Y yield': move >= 0 ? 'Dollar carry support is firming.' : 'Dollar carry support is softening.',
    Gold: move >= 0 ? 'Defensive asset demand is rising.' : 'Defensive asset demand is cooling.',
  };

  return (
    <article className="fx-driver-card">
      <div>
        <p>{row.name}</p>
        <strong>{price(row.price, row.decimals)}</strong>
        <span>{row.unit}</span>
      </div>
      <div className={`fx-driver-move fx-tone-${tone}`}>{signedPct(move)}</div>
      <small>{interpretations[row.name]}</small>
    </article>
  );
}

function ScenarioCard({ label, value, delta, note, tone }) {
  return (
    <article className={`fx-scenario fx-scenario--${tone}`}>
      <span>{label}</span>
      <strong>{price(value, 4)}</strong>
      <b>{delta}</b>
      <p>{note}</p>
    </article>
  );
}

export default function EconomicsPage() {
  const [horizon, setHorizon] = useState('d1');
  const [selectedPair, setSelectedPair] = useState('USD/INR');
  const [scenarioShift, setScenarioShift] = useState(2);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPayload(await getFxIntelligence());
    } catch (reason) {
      setError(reason?.message || 'FX reference feed is unavailable.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 5 * 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const pairs = payload?.pairs || [];
  const drivers = payload?.drivers || [];
  const strength = payload?.strength?.[horizon] || [];
  const usdInr = useMemo(() => pairs.find((row) => row.pair === 'USD/INR'), [pairs]);
  const selected = useMemo(
    () => pairs.find((row) => row.pair === selectedPair) || usdInr || pairs[0],
    [pairs, selectedPair, usdInr],
  );
  const leaders = useMemo(
    () => [...pairs]
      .filter((row) => Number.isFinite(Number(row?.returns?.[horizon])))
      .sort((left, right) => Number(right.returns[horizon]) - Number(left.returns[horizon])),
    [pairs, horizon],
  );
  const selectedMove = Number(selected?.returns?.[horizon]);
  const selectedTone = moveTone(selectedMove);
  const maxStrength = Math.max(0.01, ...strength.map((row) => Math.abs(Number(row.score) || 0)));
  const scenarioBase = Number(usdInr?.price);
  const scenarioFactor = scenarioShift / 100;
  const rangeLow = Number(selected?.low);
  const rangeHigh = Number(selected?.high);
  const selectedPrice = Number(selected?.price);
  const rangePosition = Number.isFinite(rangeLow) && Number.isFinite(rangeHigh) && rangeHigh > rangeLow
    ? Math.max(0, Math.min(100, ((selectedPrice - rangeLow) / (rangeHigh - rangeLow)) * 100))
    : null;
  const regime = Math.abs(selectedMove) < 0.08
    ? 'Range-bound'
    : Math.abs(selectedMove) >= 0.75
      ? 'Expansion'
      : 'Directional';

  useEffect(() => {
    if (pairs.length && !pairs.some((row) => row.pair === selectedPair)) {
      setSelectedPair(pairs[0].pair);
    }
  }, [pairs, selectedPair]);

  return (
    <PageShell
      title="FX Intelligence"
      metaTitle="FX Intelligence | Agarwal Global Investments"
      eyebrow="Markets / Currency desk"
      description="Live currency heatmaps, India FX transmission signals and scenario tools built for decisions, not decoration."
      className="fx-shell"
      theme="dark"
      wide
    >
      <main className="fx-page">
        <section className="fx-command">
          <div className="fx-command-copy">
            <p className="fx-kicker">GLOBAL CURRENCY NETWORK</p>
            <h2>The market, translated through currencies.</h2>
            <p>
              Track relative force across the dollar, rupee, G10 and Asian FX, then inspect
              the rates, energy and risk channels behind each move.
            </p>
            <div className="fx-hero-proof" aria-label="FX desk coverage">
              <span><b>{payload?.coverage?.available || 0}/{payload?.coverage?.expected || 15}</b> pairs reporting</span>
              <span><b>5 min</b> automatic refresh</span>
              <span><b>Reference</b> research pricing</span>
            </div>
          </div>
          <div className="fx-command-status">
            <span className={`fx-live-dot ${error ? 'fx-live-dot--error' : ''}`} />
            <div>
              <b>{error ? 'Reference feed interrupted' : loading && !payload ? 'Connecting to market reference' : 'Market reference online'}</b>
              <small>{payload ? `Updated ${freshTime(payload.asOf)}` : 'Read-only, delayed data'}</small>
            </div>
            <button type="button" onClick={load} disabled={loading}>
              {loading ? 'Refreshing' : 'Refresh'}
            </button>
          </div>
        </section>

        {error ? (
          <div className="fx-alert">
            <div>
              <strong>FX desk is temporarily unavailable.</strong>
              <span>{error}</span>
            </div>
            <button type="button" onClick={load}>Try again</button>
          </div>
        ) : null}

        <section className="fx-market-tape" aria-label="Currency market tape">
          <div className="fx-tape-label">
            <span>FX</span>
            <b>MARKET TAPE</b>
          </div>
          <div className="fx-tape-track">
            {pairs.map((row) => {
              const rowMove = Number(row?.returns?.[horizon]);
              return (
                <button
                  type="button"
                  key={row.pair}
                  className={selected?.pair === row.pair ? 'is-active' : ''}
                  onClick={() => setSelectedPair(row.pair)}
                >
                  <span>{row.pair}</span>
                  <b>{price(row.price, row.decimals)}</b>
                  <em className={`fx-tone-${moveTone(rowMove)}`}>{signedPct(rowMove)}</em>
                </button>
              );
            })}
          </div>
        </section>

        <nav className="fx-horizons" aria-label="Return horizon">
          <span>Market move</span>
          {HORIZONS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={horizon === item.key ? 'is-active' : ''}
              onClick={() => setHorizon(item.key)}
            >
              {item.label}
            </button>
          ))}
          <small>Positive means the first currency in the pair appreciated.</small>
        </nav>

        <section className="fx-primary-grid">
          <div className="fx-panel fx-heatmap-panel">
            <header className="fx-panel-head">
              <div>
                <span>01 / CROSS-ASSET VIEW</span>
                <h3>Currency heatmap</h3>
              </div>
              <p>{payload?.coverage?.available || 0}/{payload?.coverage?.expected || 15} pairs reporting</p>
            </header>
            {pairs.length ? (
              <div className="fx-heatmap">
                {pairs.map((row) => (
                  <HeatCell
                    key={row.pair}
                    row={row}
                    horizon={horizon}
                    active={selected?.pair === row.pair}
                    onSelect={setSelectedPair}
                  />
                ))}
              </div>
            ) : (
              <div className="fx-loading-grid" aria-label="Loading currency heatmap">
                {Array.from({ length: 9 }).map((_, index) => <span key={index} />)}
              </div>
            )}
          </div>

          <aside className="fx-panel fx-strength-panel">
            <header className="fx-panel-head">
              <div>
                <span>02 / RELATIVE FORCE</span>
                <h3>Currency strength</h3>
              </div>
            </header>
            <p className="fx-panel-note">
              Average signed return across the available pair network. This is a relative market measure, not a trading signal.
            </p>
            <div className="fx-strength-list">
              {strength.slice(0, 11).map((row, index) => {
                const score = Number(row.score) || 0;
                const width = Math.max(4, (Math.abs(score) / maxStrength) * 50);
                return (
                  <div className="fx-strength-row" key={row.currency}>
                    <b>{String(index + 1).padStart(2, '0')}</b>
                    <strong>{row.currency}</strong>
                    <div className="fx-strength-track">
                      <span
                        className={score >= 0 ? 'is-positive' : 'is-negative'}
                        style={score >= 0 ? { left: '50%', width: `${width}%` } : { right: '50%', width: `${width}%` }}
                      />
                    </div>
                    <em className={`fx-tone-${moveTone(score)}`}>{signedPct(score)}</em>
                  </div>
                );
              })}
            </div>
          </aside>
        </section>

        <section className="fx-inr-grid">
          <article className="fx-panel fx-inr-focus fx-pair-focus">
            <header className="fx-panel-head">
              <div>
                <span>03 / PAIR WORKSTATION</span>
                <h3>{selected?.pair || 'Currency pair'} monitor</h3>
              </div>
              <div className={`fx-inr-badge fx-tone-${selectedTone}`}>
                {regime}
              </div>
            </header>
            <div className="fx-pair-context">
              <span>{selected?.region || 'Global FX'}</span>
              <b>{selected?.base || 'Base'} strength versus {selected?.quote || 'quote'}</b>
            </div>
            <div className="fx-inr-number">
              <strong>{price(selected?.price, selected?.decimals ?? 4)}</strong>
              <span className={`fx-tone-${selectedTone}`}>{signedPct(selectedMove)} / {HORIZONS.find((item) => item.key === horizon)?.label}</span>
            </div>
            <Sparkline values={selected?.sparkline || []} tone={selectedTone} />
            <div className="fx-pair-stats">
              {HORIZONS.map((item) => (
                <div key={item.key}>
                  <span>{item.label} return</span>
                  <b className={`fx-tone-${moveTone(selected?.returns?.[item.key])}`}>{signedPct(selected?.returns?.[item.key])}</b>
                </div>
              ))}
              <div>
                <span>Range position</span>
                <b>{rangePosition == null ? '—' : `${rangePosition.toFixed(0)}%`}</b>
              </div>
            </div>
            <div className="fx-range-meter" aria-label="Position inside one month range">
              <span style={{ width: `${rangePosition ?? 0}%` }} />
            </div>
            <div className="fx-range">
              <span>1-month low <b>{price(selected?.low, selected?.decimals ?? 4)}</b></span>
              <span>1-month high <b>{price(selected?.high, selected?.decimals ?? 4)}</b></span>
            </div>
          </article>

          <article className="fx-panel fx-transmission">
            <header className="fx-panel-head">
              <div>
                <span>04 / TRANSMISSION</span>
                <h3>Macro driver lens</h3>
              </div>
              <p>Observed market channels for context, not a causal model.</p>
            </header>
            <div className="fx-driver-grid">
              {drivers.length
                ? drivers.map((row) => <DriverCard key={row.name} row={row} horizon={horizon} />)
                : Array.from({ length: 4 }).map((_, index) => <div className="fx-driver-skeleton" key={index} />)}
            </div>
          </article>
        </section>

        <section className="fx-panel fx-scenario-panel">
          <header className="fx-panel-head">
            <div>
              <span>05 / RANGE TEST</span>
              <h3>USD/INR scenario paths</h3>
            </div>
            <div className="fx-scenario-controls">
              <span>Stress distance</span>
              <div>
                {SCENARIO_STEPS.map((step) => (
                  <button
                    type="button"
                    key={step}
                    className={scenarioShift === step ? 'is-active' : ''}
                    onClick={() => setScenarioShift(step)}
                  >
                    {step}%
                  </button>
                ))}
              </div>
              <small>Mechanical, not a forecast</small>
            </div>
          </header>
          <div className="fx-scenario-grid">
            <ScenarioCard
              label="INR strengthens"
              value={Number.isFinite(scenarioBase) ? scenarioBase * (1 - scenarioFactor) : null}
              delta={`-${scenarioShift.toFixed(1)}%`}
              tone="stronger"
              note="Lower imported inflation pressure; exporters face a translation headwind."
            />
            <ScenarioCard
              label="Reference path"
              value={scenarioBase}
              delta="0.0%"
              tone="base"
              note="Current market reference held constant to isolate portfolio sensitivity."
            />
            <ScenarioCard
              label="INR weakens"
              value={Number.isFinite(scenarioBase) ? scenarioBase * (1 + scenarioFactor) : null}
              delta={`+${scenarioShift.toFixed(1)}%`}
              tone="weaker"
              note="Higher import-cost pressure; exporters gain a translation tailwind."
            />
          </div>
        </section>

        <section className="fx-method-grid">
          <article>
            <span>DATA</span>
            <h3>Source-aware reference</h3>
            <p>{payload?.source || 'Yahoo Finance market reference'}. Designed for research context, never execution pricing.</p>
          </article>
          <article>
            <span>CALCULATION</span>
            <h3>Transparent transformations</h3>
            <p>Pair returns, ranges and strength scores are computed by AGI from the returned close series.</p>
          </article>
          <article>
            <span>INTERPRETATION</span>
            <h3>Evidence before conviction</h3>
            <p>Driver cards describe observed transmission channels. They do not assert causality or predict direction.</p>
          </article>
        </section>

        <div className="fx-research-wrap">
          <DeskResearchFeed
            deskId="economics"
            title="Latest macro & FX research"
            emptyHint="Publish macro and currency research from the Economics desk in Admin."
          />
        </div>

        <footer className="fx-disclosure">
          <b>Research use only.</b>
          <span>Market-reference data may be delayed, incomplete or revised. Nothing on this page is an execution quote, recommendation or solicitation.</span>
        </footer>
      </main>
    </PageShell>
  );
}
