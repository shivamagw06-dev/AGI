import { useEffect, useRef } from 'react';
import { rng, gaussian } from './simulation';

/**
 * Signature element: a generative background of Ornstein–Uhlenbeck paths.
 *
 * The ornament is the mathematics. Each ribbon is a mean-reverting process
 * following ds = θ(μ − s)dt + σ dW — the same SDE typeset in the statistical
 * arbitrage section — so the decoration illustrates the page rather than
 * competing with it.
 *
 * A live P&L ticker was the alternative the brief offered. It was rejected
 * deliberately: a scrolling profit strip on a firm-branded page reads as a
 * performance claim, and this firm cannot make one.
 */
export default function OuField() {
  const ref = useRef(null);
  const raf = useRef(0);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return undefined;

    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const ctx = canvas.getContext('2d');
    if (!ctx) return undefined;

    const LANES = 7;
    const THETA = 0.020;
    const SIGMA = 0.22;
    let dpr = 1;
    let w = 0;
    let h = 0;
    let lanes = [];

    const build = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      w = Math.max(1, Math.floor(rect.width));
      h = Math.max(1, Math.floor(rect.height));
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const step = Math.max(22, Math.floor(w / 46));
      const count = Math.ceil(w / step) + 2;
      lanes = Array.from({ length: LANES }, (_, i) => {
        const next = rng(9001 + i * 137);
        const series = [0];
        for (let k = 1; k < count; k += 1) {
          const prev = series[k - 1];
          series.push(prev + THETA * (0 - prev) + SIGMA * gaussian(next));
        }
        return { series, step, phase: i / LANES, drift: 0.12 + i * 0.035 };
      });
    };

    const draw = (t) => {
      ctx.clearRect(0, 0, w, h);
      lanes.forEach((lane, i) => {
        const amp = h * 0.10;
        const baseY = h * (0.16 + i * 0.115);
        const offset = ((t * 0.0075 * lane.drift) % lane.step) * -1;

        const xy = lane.series.map((v, k) => [k * lane.step + offset, baseY + v * amp]);
        ctx.beginPath();
        ctx.moveTo(xy[0][0], xy[0][1]);
        for (let k = 1; k < xy.length - 1; k += 1) {
          const [x0, y0] = xy[k];
          const [x1, y1] = xy[k + 1];
          ctx.quadraticCurveTo(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2);
        }
        const fade = 0.055 + (LANES - i) * 0.016;
        ctx.strokeStyle = i % 3 === 0
          ? `rgba(180, 136, 78, ${fade + 0.03})`
          : `rgba(110, 140, 160, ${fade})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      });
      raf.current = requestAnimationFrame(draw);
    };

    build();

    const still = () => { draw(0); cancelAnimationFrame(raf.current); raf.current = 0; };
    const start = () => {
      if (reduce?.matches) { still(); return; }
      if (!raf.current) raf.current = requestAnimationFrame(draw);
    };
    const stop = () => { cancelAnimationFrame(raf.current); raf.current = 0; };

    // The hero scrolls out of view quickly. Leaving a rAF loop running behind
    // eight screens of content burns CPU for nothing, so pause when off-screen.
    const io = new IntersectionObserver(
      ([entry]) => (entry.isIntersecting ? start() : stop()),
      { threshold: 0 },
    );
    io.observe(canvas);

    const onVisibility = () => (document.hidden ? stop() : start());
    document.addEventListener('visibilitychange', onVisibility);

    if (reduce?.matches) still(); else start();

    const onResize = () => { build(); };
    window.addEventListener('resize', onResize);
    return () => {
      io.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('resize', onResize);
      cancelAnimationFrame(raf.current);
    };
  }, []);

  return <canvas ref={ref} className="sl-hero-canvas" aria-hidden="true" />;
}
