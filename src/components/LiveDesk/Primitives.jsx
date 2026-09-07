/** Shared shells so every panel has the same loading, empty and error shape. */

export function Card({ title, right, children, tight = false }) {
  return (
    <section className="ld-card">
      <div className="ld-card-head">
        <span className="ld-label">{title}</span>
        {right ?? null}
      </div>
      <div className={tight ? 'ld-card-body ld-tight' : 'ld-card-body'}>{children}</div>
    </section>
  );
}

/** One place for the three states, so no panel can quietly render blank. */
export function State({ loading, error, empty, children, labels = {} }) {
  if (loading) return <div className="ld-state">{labels.loading || 'Loading…'}</div>;
  if (error) return <div className="ld-state ld-state-err">{labels.error || 'Data temporarily unavailable.'}</div>;
  if (empty) return <div className="ld-state">{labels.empty || 'Nothing to show.'}</div>;
  return children;
}

export function pct(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}%`;
}

export function price(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

/** Direction class. Small moves read as flat rather than as a signal. */
export function dirClass(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || Math.abs(n) < 0.005) return 'ld-flat';
  return n > 0 ? 'ld-up' : 'ld-down';
}

export function istTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return `${d.toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata',
  })} IST`;
}
