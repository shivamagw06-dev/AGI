import React, { useMemo, useState } from 'react';
import { buildPortfolioDecisionQueue } from '../../lib/portfolioDecisionQueue';

const COLORS = {
  ink: '#142536',
  muted: '#677684',
  line: '#dce4e8',
  paper: '#fbfcfa',
  blue: '#1d5d73',
  red: '#a44335',
  amber: '#996515',
  green: '#28715b',
};

const priorityMeta = {
  review_now: { label: 'Review now', color: COLORS.red, background: '#fbefec' },
  monitor: { label: 'Monitor', color: COLORS.blue, background: '#edf5f7' },
  research_gap: { label: 'Research gap', color: COLORS.amber, background: '#faf4e7' },
};

const directionLabel = {
  positive: 'Positive',
  negative: 'Negative',
  mixed: 'Mixed',
  unavailable: 'Direction unavailable',
};

function Metric({ label, value, tone = COLORS.ink }) {
  return (
    <div style={{ borderTop: `1px solid ${COLORS.line}`, paddingTop: 12 }}>
      <div style={{ color: COLORS.muted, fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ color: tone, fontFamily: 'Georgia, serif', fontSize: 29, marginTop: 5 }}>{value}</div>
    </div>
  );
}

function Evidence({ evidence }) {
  if (!evidence.length) {
    return <span style={{ color: COLORS.amber }}>Source evidence is incomplete.</span>;
  }
  return evidence.slice(0, 2).map((source, index) => (
    <React.Fragment key={`${source.label}-${index}`}>
      {index > 0 ? ' | ' : ''}
      {source.url ? (
        <a href={source.url} target="_blank" rel="noreferrer" style={{ color: COLORS.blue }}>
          {source.label}
        </a>
      ) : source.label}
    </React.Fragment>
  ));
}

export default function PortfolioDecisionQueue({
  researchImpacts = [],
  holdings = [],
  foundation = null,
  institutionalFoundation = null,
  context = null,
  portfolio = null,
  data = null,
  heading = 'Portfolio decision queue',
}) {
  const [filter, setFilter] = useState('all');
  const source = foundation || institutionalFoundation || context || data || portfolio || {};
  const resolvedResearchImpacts = researchImpacts.length
    ? researchImpacts
    : source.researchImpacts
      || source.research_impacts
      || source.foundation?.researchImpacts
      || source.institutionalFoundation?.researchImpacts
      || [];
  const resolvedHoldings = holdings.length
    ? holdings
    : source.holdings
      || source.positions
      || source.assets
      || source.foundation?.holdings
      || [];
  const queue = useMemo(
    () => buildPortfolioDecisionQueue({
      researchImpacts: resolvedResearchImpacts,
      holdings: resolvedHoldings,
    }),
    [resolvedResearchImpacts, resolvedHoldings],
  );
  const items = filter === 'all'
    ? queue.items
    : queue.items.filter((item) => item.priority === filter);

  return (
    <section style={{ background: COLORS.paper, color: COLORS.ink, padding: 'clamp(24px, 4vw, 56px)', border: `1px solid ${COLORS.line}` }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(260px, 0.8fr)', gap: 32, alignItems: 'end' }}>
        <div>
          <div style={{ color: COLORS.green, fontSize: 11, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase' }}>
            Research to portfolio
          </div>
          <h2 style={{ fontFamily: 'Georgia, serif', fontSize: 'clamp(32px, 5vw, 58px)', fontWeight: 400, lineHeight: 0.98, margin: '12px 0 16px' }}>
            {heading}
          </h2>
          <p style={{ color: COLORS.muted, lineHeight: 1.65, margin: 0, maxWidth: 760 }}>
            Converts explicit research impacts into a review order. It does not place trades, rebalance the portfolio, or invent a view when evidence is missing.
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
          <Metric label="Review" value={queue.counts.review_now} tone={COLORS.red} />
          <Metric label="Monitor" value={queue.counts.monitor} tone={COLORS.blue} />
          <Metric label="Gaps" value={queue.counts.research_gap} tone={COLORS.amber} />
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, margin: '32px 0 20px' }}>
        {[
          ['all', 'All'],
          ['review_now', 'Review now'],
          ['monitor', 'Monitor'],
          ['research_gap', 'Research gaps'],
        ].map(([value, label]) => (
          <button
            type="button"
            key={value}
            onClick={() => setFilter(value)}
            style={{
              background: filter === value ? COLORS.ink : 'transparent',
              border: `1px solid ${filter === value ? COLORS.ink : COLORS.line}`,
              color: filter === value ? '#fff' : COLORS.ink,
              cursor: 'pointer',
              padding: '9px 14px',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {!items.length ? (
        <div style={{ borderTop: `1px solid ${COLORS.line}`, padding: '28px 0', color: COLORS.muted }}>
          {queue.message || 'No items match this view.'}
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 10 }}>
          {items.map((item) => {
            const meta = priorityMeta[item.priority];
            return (
              <article key={item.id} style={{ background: '#fff', border: `1px solid ${COLORS.line}`, padding: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                  <div style={{ minWidth: 0, flex: '1 1 520px' }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 9 }}>
                      <span style={{ background: meta.background, color: meta.color, fontSize: 11, fontWeight: 700, padding: '5px 8px', textTransform: 'uppercase' }}>
                        {meta.label}
                      </span>
                      {item.symbol && <strong style={{ color: COLORS.green }}>{item.symbol}</strong>}
                      <span style={{ color: COLORS.muted, fontSize: 12 }}>{item.category}</span>
                    </div>
                    <h3 style={{ fontFamily: 'Georgia, serif', fontSize: 24, fontWeight: 400, margin: '0 0 8px' }}>{item.title}</h3>
                    <p style={{ color: item.summary ? COLORS.muted : COLORS.amber, lineHeight: 1.55, margin: 0 }}>
                      {item.summary || 'Portfolio impact summary is unavailable.'}
                    </p>
                  </div>
                  <div style={{ minWidth: 190, borderLeft: `1px solid ${COLORS.line}`, paddingLeft: 18 }}>
                    <div style={{ color: COLORS.muted, fontSize: 11, textTransform: 'uppercase' }}>Stated impact</div>
                    <strong style={{ display: 'block', marginTop: 5 }}>{directionLabel[item.direction]}</strong>
                    <div style={{ color: COLORS.muted, fontSize: 12, marginTop: 8 }}>
                      Confidence: {item.confidence === null ? 'Unavailable' : `${Math.round(item.confidence * 100)}%`}
                    </div>
                  </div>
                </div>
                <div style={{ borderTop: `1px solid ${COLORS.line}`, color: COLORS.muted, display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', fontSize: 12, marginTop: 18, paddingTop: 13 }}>
                  <span><Evidence evidence={item.evidence} /></span>
                  <strong style={{ color: meta.color }}>{item.action}</strong>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <p style={{ borderTop: `1px solid ${COLORS.line}`, color: COLORS.muted, fontSize: 11, lineHeight: 1.5, margin: '24px 0 0', paddingTop: 14 }}>
        Methodology: {queue.methodology}
      </p>
    </section>
  );
}
