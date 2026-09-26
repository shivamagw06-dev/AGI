export default function Sparkline({ points = [], up = true, width = 72, height = 28 }) {
  const nums = (points || []).map(Number).filter(Number.isFinite);
  if (nums.length < 2) {
    return <div style={{ width, height }} className="opacity-30" />;
  }
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;
  const d = nums
    .map((v, i) => {
      const x = (i / (nums.length - 1)) * width;
      const y = height - ((v - min) / span) * (height - 4) - 2;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const stroke = up ? 'var(--io-green)' : 'var(--io-red)';
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      <path d={d} fill="none" stroke={stroke} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
