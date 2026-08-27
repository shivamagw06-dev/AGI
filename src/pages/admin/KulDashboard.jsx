import { useEffect, useState } from 'react';
import { getAqeDashboard, postAqeInspect } from '@/lib/intelligenceApi';
import '@/pages/admin/valuationPolicy.css';

function Stat({ label, value }) {
  return (
    <div className="vp-stat">
      <div className="vp-stat-label">{label}</div>
      <div className="vp-stat-value">{value ?? '—'}</div>
    </div>
  );
}

export default function KulDashboard() {
  const [board, setBoard] = useState(null);
  const [question, setQuestion] = useState("What is HDFC Bank's business model?");
  const [inspect, setInspect] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    getAqeDashboard()
      .then((d) => {
        if (alive) setBoard(d);
      })
      .catch((e) => {
        if (alive) setErr(e?.message || 'KUL dashboard unavailable');
      });
    return () => {
      alive = false;
    };
  }, []);

  const runInspect = async () => {
    try {
      const r = await postAqeInspect({ question });
      setInspect(r);
      setErr('');
    } catch (e) {
      setErr(e?.message || 'inspect failed');
    }
  };

  const routing = board?.routing || {};

  return (
    <div className="vp-page">
      <header className="vp-hero">
        <p className="vp-eyebrow">Knowledge Unification</p>
        <h1>KUL Routing Quality</h1>
        <p className="vp-lede">
          Intent → entity → domain → required intelligence → provider ranking. Inspect plans
          without calling live vendors.
        </p>
      </header>

      {err ? <div className="vp-banner warn">{err}</div> : null}

      <section className="vp-grid">
        <Stat label="Probe accuracy" value={routing.accuracy_pct != null ? `${routing.accuracy_pct}%` : '—'} />
        <Stat label="Hits" value={routing.hits} />
        <Stat label="Total probes" value={routing.total} />
        <Stat label="Metadata routes" value={routing.metadata_routes} />
      </section>

      <section className="vp-panel">
        <h2>Inspect a question</h2>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          <input
            className="vp-input"
            style={{ flex: 1, minWidth: 240 }}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button type="button" className="vp-btn" onClick={runInspect}>
            Inspect routing
          </button>
        </div>
        {inspect ? <pre className="vp-pre">{JSON.stringify(inspect, null, 2)}</pre> : null}
      </section>
    </div>
  );
}
