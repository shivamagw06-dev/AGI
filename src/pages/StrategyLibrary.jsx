import { useState, useMemo, useRef } from 'react';
import { Helmet } from 'react-helmet-async';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, ShieldCheck, Layers, Database, Lock, ChevronRight } from 'lucide-react';
import Equation from '@/components/strategyLibrary/Equation';
import OuField from '@/components/strategyLibrary/OuField';
import { WIDGETS } from '@/components/strategyLibrary/widgets';
import {
  STRATEGIES, LADDER, ALPHA_CLAIM_STAGE, EXECUTION_STAGE,
  BLOCKER_COPY, FIRM_PLACEHOLDER, DISCLAIMER,
} from '@/lib/strategyLibraryData';
import './strategyLibrary.css';

/* ---------------------------------------------------------------- helpers */

function Reveal({ children, delay = 0 }) {
  const reduce = useReducedMotion();
  if (reduce) return <div>{children}</div>;
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.45, delay, ease: [0.22, 0.61, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

/** Seven-segment meter showing where a strategy sits on the validation ladder. */
function Ladder({ stage }) {
  return (
    <>
      <div className="sl-ladder" role="img"
           aria-label={`Validation stage ${stage} of ${LADDER.length}: ${LADDER[stage - 1]}`}>
        {LADDER.map((name, i) => (
          <span key={name} className={i < stage ? 'on' : ''} />
        ))}
      </div>
      <div className="sl-ladder-legend">
        <b className="sl-num">{LADDER[stage - 1]}</b>
        <span className="sl-num">{stage} / {LADDER.length}</span>
      </div>
    </>
  );
}

function AgiPosition({ agi }) {
  return (
    <div className="sl-agi">
      <div className="sl-agi-head">
        <ShieldCheck size={14} color="var(--sl-brass)" />
        <b>Where AGI actually stands</b>
      </div>
      <p>{agi.note}</p>

      {agi.strategies.length === 0 ? (
        <div className="sl-agi-empty">NOT REGISTERED — no capability in this area</div>
      ) : (
        agi.strategies.map((s) => (
          <div className="sl-strat-row" key={s.id}>
            <div className="sl-strat-top">
              <b>{s.name}</b>
              <code>{s.id}</code>
            </div>
            <Ladder stage={s.stage} />
            {s.blockedBy.length ? (
              <ul className="sl-blockers">
                {s.blockedBy.map((code) => (
                  <li key={code}>
                    <code>{code}</code>
                    <span>{BLOCKER_COPY[code] || 'Blocked.'}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ))
      )}
    </div>
  );
}

/* ------------------------------------------------------------------- page */

export default function StrategyLibrary() {
  const [active, setActive] = useState(STRATEGIES[0].id);
  const [sent, setSent] = useState(false);
  const panelRef = useRef(null);

  const strategy = useMemo(
    () => STRATEGIES.find((s) => s.id === active) || STRATEGIES[0],
    [active],
  );
  const Widget = WIDGETS[strategy.widget];

  const select = (id) => {
    setActive(id);
    if (window.innerWidth < 900) {
      window.requestAnimationFrame(() =>
        panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    }
  };

  return (
    <div className="sl-root">
      <Helmet>
        <title>Strategy Research Library | AGI</title>
        <meta
          name="description"
          content="Eight hedge fund strategy families explained with their mechanics, mathematics and failure modes — alongside an honest account of where AGI's research platform actually stands on each."
        />
      </Helmet>
      {/* ============================================== HERO */}
      <header className="sl-hero">
        <OuField />
        <div className="sl-shell sl-hero-inner">
          <div className="sl-eyebrow">Agarwal Global Investments — Research</div>
          <h1>The strategies institutional capital is built on, explained properly.</h1>
          <p className="sl-hero-lede">
            A working reference on eight hedge fund strategy families: the mechanics, the
            mathematics, and the conditions under which each one stops working. Alongside every
            family, an honest account of where our own research platform currently stands.
          </p>

          <div className="sl-hero-note">
            <b>This is a research library, not an offering.</b> AGI does not currently run any of
            the strategies described here. Each section shows our real position on the internal
            validation ladder, including the specific data that blocks progress. Nothing on this
            page is a recommendation, a track record, or a claim of demonstrated alpha.
          </div>

          <div className="sl-cta-row">
            <a className="sl-btn sl-btn-primary" href="#strategies">
              Read the strategies <ArrowRight size={14} />
            </a>
            <a className="sl-btn" href="#contact">Investor relations</a>
          </div>
        </div>
      </header>

      {/* ============================================== STAT BAND */}
      <section className="sl-band" aria-label="Research platform at a glance">
        <div className="sl-shell">
          <div className="sl-band-grid">
            {/* PLACEHOLDER FIGURES — descriptive of the research platform only.
                No AUM, returns or performance figures appear anywhere on this page. */}
            <div className="sl-band-cell">
              <b>{FIRM_PLACEHOLDER.researchUniverse}</b><span>Companies in factor universe</span>
            </div>
            <div className="sl-band-cell">
              <b>{FIRM_PLACEHOLDER.strategiesRegistered}</b><span>Strategies registered</span>
            </div>
            <div className="sl-band-cell">
              <b>{FIRM_PLACEHOLDER.strategiesOperational}</b><span>At stage 2 of 7</span>
            </div>
            <div className="sl-band-cell">
              <b>0</b><span>Validated for capital</span>
            </div>
            <div className="sl-band-cell">
              <b>{FIRM_PLACEHOLDER.founded}</b><span>Research began</span>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================== STRATEGIES */}
      <section className="sl-section" id="strategies">
        <div className="sl-shell">
          <div className="sl-section-head">
            <div className="sl-eyebrow"><Layers size={13} /> Section 01</div>
            <h2>Eight strategy families</h2>
            <p>
              Each family is presented as a practitioner would describe it: what the trade is,
              how it is constructed, the mathematics that governs it, and the ways it fails. The
              interactive models are live calculations on simulated data — move the inputs and the
              output recomputes.
            </p>
          </div>

          <div className="sl-strat-layout">
            <nav className="sl-rail" role="tablist" aria-label="Strategy families"
                 aria-orientation="vertical">
              <div className="sl-rail-title">Families</div>
              {STRATEGIES.map((s) => (
                <button
                  key={s.id}
                  role="tab"
                  type="button"
                  id={`tab-${s.id}`}
                  aria-selected={active === s.id}
                  aria-controls={`panel-${s.id}`}
                  data-short={s.family}
                  className="sl-rail-btn"
                  onClick={() => select(s.id)}
                >
                  <i>{s.number}</i>
                  <span>{s.title}</span>
                </button>
              ))}
            </nav>

            <div
              className="sl-panel"
              ref={panelRef}
              role="tabpanel"
              id={`panel-${strategy.id}`}
              aria-labelledby={`tab-${strategy.id}`}
              tabIndex={-1}
            >
              <div className="sl-panel-head">
                <div className="sl-eyebrow">{strategy.number} — {strategy.family}</div>
                <h3>{strategy.title}</h3>
                <p className="sl-panel-summary">{strategy.summary}</p>
              </div>

              <div className="sl-block">
                <h4>How the trade works</h4>
                <ol className="sl-steps">
                  {strategy.mechanics.map((m) => <li key={m}><span>{m}</span></li>)}
                </ol>
              </div>

              <div className="sl-block">
                <h4>The mathematics</h4>
                {strategy.math.map((eq) => (
                  <Equation key={eq.label} label={eq.label} tex={eq.tex} note={eq.note} />
                ))}
              </div>

              {Widget ? (
                <div className="sl-block">
                  <h4>Model</h4>
                  <Widget />
                </div>
              ) : null}

              <div className="sl-block">
                <h4>Where this breaks</h4>
                <div className="sl-risks">
                  {strategy.risks.map(([name, detail]) => (
                    <div className="sl-risk" key={name}>
                      <b>{name}</b><span>{detail}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="sl-block">
                <h4>Representative data sources</h4>
                <div className="sl-chips">
                  {strategy.sources.map((src) => <span className="sl-chip" key={src}>{src}</span>)}
                </div>
              </div>

              <div className="sl-block">
                <h4>Our position</h4>
                <AgiPosition agi={strategy.agi} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================== VALIDATION LADDER */}
      <section className="sl-section" id="validation">
        <div className="sl-shell">
          <div className="sl-section-head">
            <div className="sl-eyebrow"><Lock size={13} /> Section 02</div>
            <h2>How a strategy earns the right to capital</h2>
            <p>
              Strategies cannot promote themselves. A separate validation registry evaluates
              thirteen evidence gates and assigns a lifecycle stage; the strategy has no say in it.
              Historical alpha claims are mechanically prohibited below stage {ALPHA_CLAIM_STAGE},
              and execution below stage {EXECUTION_STAGE}.
            </p>
          </div>

          <Reveal>
            <div className="sl-stack">
              {LADDER.map((name, i) => {
                const n = i + 1;
                const notes = [
                  'Methodology exists on paper. No claim of any kind is permitted.',
                  'A deterministic calculator runs on certified, fresh, complete data.',
                  'Point-in-time integrity and corporate-action adjustment are independently verified.',
                  'Walk-forward backtest, out-of-sample test, transaction costs and capacity all pass.',
                  'Risk decomposition, parameter stability and paper-traded walk-forward all pass.',
                  'Operational controls, alerting and kill-switch drills are evidenced.',
                  'Cleared for capital under live monitoring.',
                ];
                return (
                  <div className="sl-stack-row" key={name}
                       style={n > 2 ? { borderLeftColor: 'var(--sl-line-strong)', opacity: 0.72 } : undefined}>
                    <i>{String(n).padStart(2, '0')}</i>
                    <div>
                      <b>
                        {name.replace(/_/g, ' ')}
                        {n === 2 ? ' — highest stage reached' : ''}
                        {n === ALPHA_CLAIM_STAGE ? ' — alpha claims unlock here' : ''}
                        {n === EXECUTION_STAGE ? ' — execution unlocks here' : ''}
                      </b>
                      <span>{notes[i]}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============================================== RISK MANAGEMENT */}
      <section className="sl-section" id="risk">
        <div className="sl-shell">
          <div className="sl-section-head">
            <div className="sl-eyebrow"><ShieldCheck size={13} /> Section 03</div>
            <h2>Risk management</h2>
            <p>
              Position sizing and loss control are the parts of the discipline that survive
              contact with reality. The formulas below are the standard toolkit, with the caveats
              that matter in practice.
            </p>
          </div>

          <div className="sl-grid-2" style={{ gap: '2rem', alignItems: 'start' }}>
            <Reveal>
              <div>
                <Equation
                  label="Sharpe ratio"
                  tex="S = \frac{\mathbb{E}[r_p] - r_f}{\sigma_p}"
                  note="Excess return per unit of volatility. Penalises upside and downside identically, which flatters strategies with negative skew — merger arbitrage and short volatility in particular."
                />
                <Equation
                  label="Kelly criterion (discrete)"
                  tex="f^{*} = \frac{pb - q}{b}"
                  note="Optimal fraction for a discrete bet with win probability p, loss probability q and odds b."
                />
                <Equation
                  label="Kelly (continuous)"
                  tex="f^{*} = \frac{\mu}{\sigma^{2}}"
                  note="Full Kelly maximises long-run growth and is far too aggressive in practice, because μ and σ are estimated with error. Most desks run a quarter to a half of it."
                />
              </div>
            </Reveal>

            <Reveal delay={0.08}>
              <div>
                <Equation
                  label="Parametric value at risk"
                  tex="\mathrm{VaR}_{c} = z_{c}\,\sigma_p\,V"
                  note="Assumes normality. Real return distributions have fatter tails, so parametric VaR understates exactly the scenarios it exists to measure."
                />
                <Equation
                  label="Expected shortfall"
                  tex="\mathrm{ES}_{c} = \mathbb{E}\!\left[\,L \mid L > \mathrm{VaR}_{c}\,\right]"
                  note="Average loss conditional on breaching VaR. Answers 'how bad is bad' rather than 'how often', which is the more useful question."
                />
                <div className="sl-widget" style={{ marginTop: '0.5rem' }}>
                  <div className="sl-widget-head"><b>Drawdown discipline</b><span>Illustrative policy</span></div>
                  <div className="sl-stack">
                    <div className="sl-stack-row"><i>−5%</i>
                      <div><b>Capital reduced</b><span>Allocation cut and positions reduced pro rata.</span></div></div>
                    <div className="sl-stack-row" style={{ borderLeftColor: 'var(--sl-oxide)' }}><i>−7.5%</i>
                      <div><b>Trading stopped</b><span>Book flattened pending review. Restart requires sign-off.</span></div></div>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>

          <Reveal delay={0.12}>
            <div style={{ marginTop: '2.5rem' }}>
              <div className="sl-eyebrow" style={{ marginBottom: '1rem' }}>The risk stack</div>
              <div className="sl-stack">
                {[
                  ['01', 'Position limits', 'Maximum weight per name, per sector, and against average daily volume.'],
                  ['02', 'Factor limits', 'Net exposure to market, size, value, momentum and rate sensitivity held inside bands.'],
                  ['03', 'Drawdown rules', 'Automatic de-risking at defined thresholds, applied without discretion.'],
                  ['04', 'Firm VaR and expected shortfall', 'Aggregate exposure netted across all books, measured on both.'],
                  ['05', 'Stress testing', 'Replays of 2008, 2020 and rate-shock scenarios against current positions.'],
                  ['06', 'Independent oversight', 'Risk reports outside the investment team and cannot be overridden by it.'],
                ].map(([n, title, detail]) => (
                  <div className="sl-stack-row" key={n}>
                    <i>{n}</i><div><b>{title}</b><span>{detail}</span></div>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============================================== DATA & TECHNOLOGY */}
      <section className="sl-section" id="data">
        <div className="sl-shell">
          <div className="sl-section-head">
            <div className="sl-eyebrow"><Database size={13} /> Section 04</div>
            <h2>Data and technology</h2>
            <p>
              Strategy research is mostly a data problem. The tiers below are the standard
              institutional stack; the house standards underneath them are the part that decides
              whether any of it produces a usable result.
            </p>
          </div>

          <div className="sl-tiers">
            <div className="sl-tier">
              <h4>Tier 1 — Core market data</h4>
              <ul>
                <li>Bloomberg / Refinitiv / FactSet</li>
                <li>CRSP and Compustat</li>
                <li>TAQ tick and quote history</li>
                <li>Exchange corporate action feeds</li>
                <li>Index constituent histories</li>
              </ul>
            </div>
            <div className="sl-tier">
              <h4>Tier 2 — Risk models</h4>
              <ul>
                <li>Barra factor models</li>
                <li>Axioma risk and optimisation</li>
                <li>Internal covariance estimation</li>
                <li>Liquidity and capacity modelling</li>
                <li>Prime broker exposure reporting</li>
              </ul>
            </div>
            <div className="sl-tier">
              <h4>Tier 3 — Alternative data</h4>
              <ul>
                <li>Transaction and card panels</li>
                <li>Satellite and geolocation</li>
                <li>NLP over filings and transcripts</li>
                <li>Web traffic and app telemetry</li>
                <li>Expert network transcripts</li>
              </ul>
            </div>
          </div>

          <Reveal>
            <div className="sl-stack" style={{ marginTop: '1.75rem' }}>
              <div className="sl-stack-row">
                <i>PIT</i>
                <div>
                  <b>Point-in-time correctness</b>
                  <span>
                    Research must see only what was knowable on the day. This requires storing
                    filing and revision timestamps, not just reporting periods. AGI does not yet
                    meet this standard — it is the single largest blocker across our registry.
                  </span>
                </div>
              </div>
              <div className="sl-stack-row" style={{ borderLeftColor: 'var(--sl-oxide)' }}>
                <i>SB</i>
                <div>
                  <b>Survivorship-bias-free research</b>
                  <span>
                    A universe built from companies that exist today has already excluded every
                    failure. Backtests over such a universe are systematically flattering. Correct
                    treatment requires historical constituents and delisted price history.
                  </span>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============================================== TEAM */}
      <section className="sl-section" id="team">
        <div className="sl-shell">
          <div className="sl-section-head">
            <div className="sl-eyebrow">Section 05</div>
            <h2>Research team</h2>
            <p>Placeholder profiles. Replace before this page is shown to anyone.</p>
          </div>
          <div className="sl-people">
            {/* PLACEHOLDER — clearly fictional names, no claimed credentials of real people. */}
            {[
              ['A. Placeholder', 'Head of Research', 'Placeholder biography. Replace with a real profile before publication.'],
              ['B. Placeholder', 'Quantitative Research', 'Placeholder biography. Replace with a real profile before publication.'],
              ['C. Placeholder', 'Data Engineering', 'Placeholder biography. Replace with a real profile before publication.'],
              ['D. Placeholder', 'Risk', 'Placeholder biography. Replace with a real profile before publication.'],
            ].map(([name, role, bio]) => (
              <div className="sl-person" key={name}>
                <b>{name}</b><em>{role}</em><span>{bio}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================== CONTACT */}
      <section className="sl-section" id="contact">
        <div className="sl-shell">
          <div className="sl-contact">
            <div>
              <div className="sl-eyebrow">Section 06</div>
              <h2 style={{ fontSize: 'clamp(1.6rem, 3.2vw, 2.2rem)', marginTop: '0.9rem' }}>
                Investor relations
              </h2>
              <p style={{ marginTop: '1rem', color: 'var(--sl-dim)', maxWidth: '46ch' }}>
                For research access or diligence questions. We will tell you exactly what is
                validated and what is not — the same answer this page gives.
              </p>
              <div className="sl-chips" style={{ marginTop: '1.5rem' }}>
                <span className="sl-chip">Research — India equities</span>
                <span className="sl-chip">No brokerage</span>
                <span className="sl-chip">No execution</span>
              </div>
            </div>

            <form
              className="sl-form"
              onSubmit={(e) => { e.preventDefault(); setSent(true); }}
            >
              <div className="sl-field">
                <label htmlFor="ir-name">Name</label>
                <input id="ir-name" name="name" type="text" required autoComplete="name" />
              </div>
              <div className="sl-field">
                <label htmlFor="ir-email">Email</label>
                <input id="ir-email" name="email" type="email" required autoComplete="email" />
              </div>
              <div className="sl-field">
                <label htmlFor="ir-msg">Message</label>
                <textarea id="ir-msg" name="message" required />
              </div>
              <button className="sl-btn sl-btn-primary" type="submit" style={{ justifyContent: 'center' }}>
                Send enquiry <ChevronRight size={14} />
              </button>
              {sent ? (
                <div className="sl-form-ok" role="status">
                  This form is a front-end demonstration and does not submit anywhere. Wire it to
                  a real endpoint before publication.
                </div>
              ) : null}
            </form>
          </div>
        </div>
      </section>

      {/* ============================================== FOOTER */}
      <footer className="sl-foot">
        <div className="sl-shell">
          <div className="sl-disclaimer">
            <b>Important. </b>{DISCLAIMER} Agarwal Global Investments operates a research platform
            and does not currently manage outside capital, execute trades, or act as a broker.
            References to well-known funds, events and vendors are educational and do not imply
            any affiliation or endorsement.
          </div>
          <p className="sl-illus" style={{ borderTop: 0, marginTop: '1.25rem' }}>
            Validation states shown on this page are transcribed from the internal strategy
            registry and are accurate as of the last review. They are not independently audited.
          </p>
        </div>
      </footer>
    </div>
  );
}
