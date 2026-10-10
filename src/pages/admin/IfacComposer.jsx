import { useEffect, useState } from 'react';
import { getIfacDashboard, getIfacHealth } from '@/lib/intelligenceApi';
import '@/pages/admin/valuationPolicy.css';

function Stat({ label, value }) {
  return (
    <div className="vp-stat">
      <div className="vp-stat-label">{label}</div>
      <div className="vp-stat-value">{value ?? '—'}</div>
    </div>
  );
}

export default function IfacComposer() {
  const [health, setHealth] = useState(null);
  const [board, setBoard] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [h, d] = await Promise.all([getIfacHealth(), getIfacDashboard()]);
        if (!alive) return;
        setHealth(h);
        setBoard(d);
        setErr('');
      } catch (e) {
        if (!alive) return;
        setErr(e?.message || 'IFAC dashboard unavailable');
      }
    };
    load();
    const id = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const stats = board?.stats || health?.stats || {};
  const recent = board?.recent || [];

  return (
    <div className="vp-page">
      <header className="vp-hero">
        <p className="vp-eyebrow">Phase 9.1</p>
        <h1>Intelligence Fusion & Answer Composer</h1>
        <p className="vp-lede">
          IFAC sits above UVE, HVIE, VARIE, RIE, FIE, MIE and Market Intelligence.
          It fuses engine outputs into institutional reports — it never generates new
          intelligence, keeps source infrastructure private, and always presents AGI consensus as the headline.
        </p>
      </header>

      {err ? <div className="vp-banner warn">{err}</div> : null}

      <section className="vp-grid">
        <Stat label="Composes" value={stats.composes} />
        <Stat label="Avg compose ms" value={stats.avg_compose_ms} />
        <Stat label="Consensus demoted" value={stats.consensus_demoted} />
        <Stat label="Conflict rate" value={stats.conflict_rate} />
        <Stat label="DQIV fail rate" value={stats.dqiv_fail_rate} />
        <Stat label="Version" value={health?.version || board?.version} />
      </section>

      <section className="vp-panel">
        <h2>Product quality</h2>
        <p className="vp-lede">
          Phase 9.2 adds routing accuracy, evidence ranking, and answer completeness tracking
          under <a href="/admin/aqe">Ask Product Quality</a> and <a href="/admin/kul">KUL Routing</a>.
        </p>
        <div className="vp-grid">
          <Stat label="Template coverage" value={Object.keys(stats.templates || {}).length || '—'} />
          <Stat label="Provider usage keys" value={Object.keys(stats.primary_engines || {}).length || '—'} />
          <Stat label="DQIV fail rate" value={stats.dqiv_fail_rate} />
        </div>
      </section>

      <section className="vp-panel">
        <h2>Template usage</h2>
        <pre className="vp-pre">{JSON.stringify(stats.templates || {}, null, 2)}</pre>
      </section>

      <section className="vp-panel">
        <h2>Primary engines</h2>
        <pre className="vp-pre">{JSON.stringify(stats.primary_engines || {}, null, 2)}</pre>
      </section>

      <section className="vp-panel">
        <h2>Recent compositions</h2>
        <div className="vp-table-wrap">
          <table className="vp-table">
            <thead>
              <tr>
                <th>Family</th>
                <th>Template</th>
                <th>Primary</th>
                <th>ms</th>
                <th>Consensus demoted</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={6}>No compositions recorded in this process yet.</td>
                </tr>
              ) : (
                recent.map((row, i) => (
                  <tr key={i}>
                    <td>{row.family}</td>
                    <td>{row.template}</td>
                    <td>{row.primary_engine}</td>
                    <td>{row.compose_ms}</td>
                    <td>{row.consensus_demoted ? 'yes' : 'no'}</td>
                    <td>{row.summary}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
