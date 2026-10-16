import { Link } from 'react-router-dom';

export default function SettingsPage() {
  return (
    <div>
      <h1 className="agi-greeting">Settings</h1>
      <p className="agi-lede">Workspace preferences and the institutional release gate.</p>

      <section className="agi-section">
        <div className="agi-section-head">
          <h2>Release</h2>
        </div>
        <div className="agi-panel">
          <div className="agi-list-title">AGI Release Health</div>
          <p className="agi-list-meta" style={{ margin: '0.45rem 0 1rem' }}>
            The one screen before every release — Build, Unit Tests, Integration, IST, IBS, E2E, hallucinations,
            provenance, regression, Ready for Release.
          </p>
          <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
            <Link className="agi-btn agi-btn-primary" to="/admin/release-health">
              Open Release Health
            </Link>
            <Link className="agi-btn" to="/agi">
              Dashboard
            </Link>
          </div>
        </div>
      </section>

      <section className="agi-section">
        <div className="agi-section-head">
          <h2>Access paths</h2>
        </div>
        <ul className="agi-list">
          <li>
            <div>
              <div className="agi-list-title">/admin/release-health</div>
              <div className="agi-list-meta">Primary operator UI (requires admin)</div>
            </div>
          </li>
          <li>
            <div>
              <div className="agi-list-title">CLI</div>
              <div className="agi-list-meta">
                cd intelligence-engine && PYTHONPATH=. python3 -m release_health --run
              </div>
            </div>
          </li>
          <li>
            <div>
              <div className="agi-list-title">API</div>
              <div className="agi-list-meta">POST /api/intelligence/release-health/run</div>
            </div>
          </li>
        </ul>
      </section>
    </div>
  );
}
