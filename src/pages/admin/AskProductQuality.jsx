import { useEffect, useState } from 'react';
import { getAqeDashboard, getAqeHealth, getIfacDashboard } from '@/lib/intelligenceApi';
import '@/pages/admin/valuationPolicy.css';

function Stat({ label, value }) {
  return (
    <div className="vp-stat">
      <div className="vp-stat-label">{label}</div>
      <div className="vp-stat-value">{value ?? '—'}</div>
    </div>
  );
}

function TargetRow({ label, target, actual }) {
  const ok =
    actual == null
      ? null
      : Number(target) === 0
        ? Number(actual) === 0
        : Number(actual) >= Number(target);
  return (
    <tr>
      <td>{label}</td>
      <td>{target}</td>
      <td>{actual ?? '—'}</td>
      <td>{ok == null ? '—' : ok ? 'ON TRACK' : 'BELOW'}</td>
    </tr>
  );
}

export default function AskProductQuality() {
  const [health, setHealth] = useState(null);
  const [board, setBoard] = useState(null);
  const [ifac, setIfac] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [h, d, i] = await Promise.all([
          getAqeHealth(),
          getAqeDashboard(),
          getIfacDashboard().catch(() => null),
        ]);
        if (!alive) return;
        setHealth(h);
        setBoard(d);
        setIfac(i);
        setErr('');
      } catch (e) {
        if (!alive) return;
        setErr(e?.message || 'AQE dashboard unavailable');
      }
    };
    load();
    const id = setInterval(load, 20000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const targets = board?.targets || {};
  const routing = board?.routing || {};
  const metrics = board?.metrics || {};
  const ifacStats = ifac?.stats || {};

  return (
    <div className="vp-page">
      <header className="vp-hero">
        <p className="vp-eyebrow">Phase 9.2</p>
        <h1>Ask Product Quality</h1>
        <p className="vp-lede">
          Institutional answer excellence over the existing warehouse → engines → IFAC stack.
          No new engines. Routing accuracy, evidence ranking, template coverage, and regression
          readiness.
        </p>
      </header>

      {err ? <div className="vp-banner warn">{err}</div> : null}

      <section className="vp-grid">
        <Stat label="Routing accuracy" value={metrics.routing_accuracy != null ? `${metrics.routing_accuracy}%` : '—'} />
        <Stat label="Metadata probes" value={metrics.metadata_probe_count} />
        <Stat label="Pedagogy probes" value={metrics.pedagogy_probe_count} />
        <Stat label="IFAC composes" value={ifacStats.composes} />
        <Stat label="Consensus demoted" value={ifacStats.consensus_demoted} />
        <Stat label="Version" value={health?.version || board?.version} />
      </section>

      <section className="vp-panel">
        <h2>Regression quality targets</h2>
        <div className="vp-table-wrap">
          <table className="vp-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Target</th>
                <th>Probe / live</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <TargetRow
                label="Routing Accuracy"
                target={targets.routing_accuracy}
                actual={metrics.routing_accuracy}
              />
              <TargetRow
                label="Metadata Accuracy"
                target={targets.metadata_accuracy}
                actual={null}
              />
              <TargetRow
                label="Institutional Template Coverage"
                target={targets.institutional_template_coverage}
                actual={null}
              />
              <TargetRow
                label="Answer Completeness"
                target={targets.answer_completeness}
                actual={null}
              />
              <TargetRow
                label="Evidence Coverage"
                target={targets.evidence_coverage}
                actual={null}
              />
              <TargetRow
                label="Consensus Headline Rate"
                target={targets.consensus_headline_rate}
                actual={ifacStats.consensus_demoted != null ? 0 : null}
              />
              <TargetRow
                label="Hallucination Rate"
                target={targets.hallucination_rate}
                actual={null}
              />
              <TargetRow
                label="Regression Pass Rate"
                target={targets.regression_pass_rate}
                actual={null}
              />
            </tbody>
          </table>
        </div>
      </section>

      <section className="vp-panel">
        <h2>Domain distribution (probes)</h2>
        <pre className="vp-pre">{JSON.stringify(routing.domains || {}, null, 2)}</pre>
      </section>

      <section className="vp-panel">
        <h2>Routing probes</h2>
        <div className="vp-table-wrap">
          <table className="vp-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Domain</th>
                <th>Entity</th>
                <th>Providers</th>
              </tr>
            </thead>
            <tbody>
              {(routing.probes || []).map((p) => (
                <tr key={p.question}>
                  <td>{p.question}</td>
                  <td>{p.domain}</td>
                  <td>
                    {(p.entity && (p.entity.canonical_name || p.entity.state)) || '—'}
                    {p.entity?.pedagogy_only ? ' (pedagogy)' : ''}
                  </td>
                  <td>{(p.provider_ids || []).slice(0, 6).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
