import { Card, State, dirClass, pct, price } from './Primitives';

/**
 * Cross-asset read on one screen.
 *
 * Rows whose instrument the feed does not carry are shown as unavailable
 * rather than dropped, so the reader can see the shape of the coverage. US 10Y
 * and DXY are absent for that reason: AGI does not price them today, and
 * inventing a row is worse than admitting the gap.
 */
export default function CrossAssetMonitor({ rows, loading, error }) {
  return (
    <Card title="Cross-Asset Monitor" tight>
      <State
        loading={loading}
        error={error}
        empty={!rows?.length}
        labels={{ loading: 'Loading cross-asset data…', empty: 'Cross-asset data temporarily unavailable.' }}
      >
        <div className="ld-scroll">
          <table className="ld-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Class</th>
                <th className="ld-r">Last</th>
                <th className="ld-r">Move</th>
                <th>Signal</th>
              </tr>
            </thead>
            <tbody>
              {(rows || []).map((row) => (
                <tr key={row.label}>
                  <td>{row.label}</td>
                  <td style={{ color: 'var(--ld-muted)' }}>{row.klass}</td>
                  <td className="ld-r ld-num">{row.available ? price(row.last) : '—'}</td>
                  <td className={`ld-r ld-num ${row.available ? dirClass(row.changePct) : 'ld-flat'}`}>
                    {row.available ? pct(row.changePct) : '—'}
                  </td>
                  <td style={{ color: 'var(--ld-muted)' }}>
                    {row.available ? (row.signal || '—') : 'Not priced by AGI'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </State>
    </Card>
  );
}
