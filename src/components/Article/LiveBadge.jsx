export default function LiveBadge({ className = '', size = 'sm' }) {
  const sizeClass =
    size === 'md' ? 'live-badge--md' : size === 'lg' ? 'live-badge--lg' : 'live-badge--sm';

  return (
    <span className={`live-badge ${sizeClass} ${className}`.trim()} aria-label="Live coverage">
      <span className="live-badge-dot" aria-hidden="true" />
      LIVE
    </span>
  );
}
