import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCommitteePending, getCommitteePortfolio } from '@/lib/intelligenceApi';

function formatPct(weight) {
  if (weight == null || Number.isNaN(Number(weight))) return '—';
  const n = Number(weight);
  if (n <= 1 && n >= 0) return `${(n * 100).toFixed(0)}%`;
  return `${n.toFixed(0)}%`;
}

export default function CommitteePage() {
  const [resolution, setResolution] = useState(null);
  const [pending, setPending] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [review, pendingResp] = await Promise.all([
          getCommitteePortfolio('agi-core-equity', { refresh: true }).catch(() => null),
          getCommitteePending().catch(() => null),
        ]);
        if (!active) return;
        setResolution(review?.ok !== false ? review?.resolution || null : null);
        setPending(pendingResp?.pending || []);
        if (review && review.ok === false) {
          setError((review.validation_errors || []).join('; ') || 'Committee review unavailable');
        }
      } catch (err) {
        if (active) setError(err?.message || 'Committee unavailable');
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const actions = resolution?.required_actions || [];
  const votes = resolution?.votes || [];
  const followUps = resolution?.follow_up_items || [];

  return (
    <div>
      <h1 className="agi-greeting">Investment Committee</h1>
      <p className="agi-lede">
        Governance of portfolio decisions — approve, condition, defer, reject, or escalate. The
        committee references CIO recommendations; it does not rewrite risk, policy, or company
        decisions.
      </p>

      {error && <div className="agi-error">{error}</div>}

      <div className="agi-stat-row">
        <div className="agi-stat">
          <div className="agi-stat-label">Status</div>
          <div className="agi-stat-value" style={{ fontSize: '1.05rem' }}>
            {resolution?.status || '—'}
          </div>
        </div>
        <div className="agi-stat">
          <div className="agi-stat-label">Pending</div>
          <div className="agi-stat-value">{pending.length}</div>
        </div>
        <div className="agi-stat">
          <div className="agi-stat-label">Actions</div>
          <div className="agi-stat-value">{actions.length || '—'}</div>
        </div>
        <div className="agi-stat">
          <div className="agi-stat-label">Review</div>
          <div className="agi-stat-value" style={{ fontSize: '0.95rem' }}>
            {resolution?.review_date || '—'}
          </div>
        </div>
      </div>

      <section className="agi-section" style={{ marginTop: '1.5rem' }}>
        <div className="agi-section-head">
          <h2>Latest resolution</h2>
          <span className="agi-list-meta">ICE-01 · AGI Core Equity</span>
        </div>
        {!resolution ? (
          <div className="agi-empty">No committee resolution available.</div>
        ) : (
          <>
            <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
              {(resolution.lineage || []).join(' → ')}
              {resolution.resolution_id ? ` · ${resolution.resolution_id}` : ''}
            </p>
            <p style={{ marginBottom: '0.75rem' }}>{resolution.outcome}</p>
            <p className="agi-list-meta" style={{ marginBottom: '1rem' }}>
              CIO: {resolution.decision_recommendation || '—'} · Risk:{' '}
              {resolution.overall_risk || '—'} · Policy: {resolution.policy_status || '—'}
            </p>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem' }}>Votes</h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {votes.map((v) => (
                <li key={v.desk}>
                  <div className="agi-list-title">
                    {v.desk}: {v.vote}
                  </div>
                  <div className="agi-list-meta">{v.rationale}</div>
                </li>
              ))}
            </ul>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Open action items
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {actions.length ? (
                actions.map((a) => (
                  <li key={a.action_id || a.title}>
                    <div className="agi-list-title">{a.title}</div>
                    <div className="agi-list-meta">
                      {a.detail}
                      {a.ticker
                        ? ` · ${a.ticker} ${formatPct(a.from_value)} → ${formatPct(a.to_value)}`
                        : ''}
                      {` · Owner ${a.owner} · Due ${a.due}`}
                    </div>
                  </li>
                ))
              ) : (
                <li>
                  <div className="agi-list-meta">No open action items.</div>
                </li>
              )}
            </ul>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Follow-up / upcoming reviews
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {followUps.map((f) => (
                <li key={f}>
                  <div className="agi-list-title">{f}</div>
                </li>
              ))}
              {!followUps.length ? (
                <li>
                  <div className="agi-list-meta">No follow-ups scheduled.</div>
                </li>
              ) : null}
            </ul>
          </>
        )}
      </section>

      <div className="agi-grid-2" style={{ marginTop: '1.5rem' }}>
        <section className="agi-section">
          <div className="agi-section-head">
            <h2>Pending decisions</h2>
          </div>
          <ul className="agi-list">
            {pending.length ? (
              pending.map((p) => (
                <li key={p.resolution_id}>
                  <div className="agi-list-title">{p.decision_recommendation || p.status}</div>
                  <div className="agi-list-meta">
                    {p.portfolio_id} · {p.status}
                  </div>
                </li>
              ))
            ) : (
              <li>
                <div className="agi-list-meta">No pending committee reviews in session.</div>
              </li>
            )}
          </ul>
        </section>

        <section className="agi-section">
          <div className="agi-section-head">
            <h2>Approved / deferred</h2>
            <Link to="/agi/portfolio">Investment Office</Link>
          </div>
          <ul className="agi-list">
            {resolution ? (
              <li>
                <div className="agi-list-title">{resolution.status}</div>
                <div className="agi-list-meta">
                  {resolution.decision_recommendation} · {resolution.portfolio_decision_id}
                </div>
              </li>
            ) : (
              <li>
                <div className="agi-list-meta">No resolved items yet.</div>
              </li>
            )}
            {(resolution?.conditions || []).map((c) => (
              <li key={c}>
                <div className="agi-list-meta">Condition: {c}</div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
