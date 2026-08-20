/**
 * Geometry for the insider activity charts.
 *
 * Kept apart from the page because a chart that is wrong is not obviously
 * wrong - a bar drawn on the incorrect side of the axis, or a line clipped at
 * the top of its box, still looks like a chart. These functions return plain
 * numbers that can be asserted against.
 *
 * All of them take counts of filings rather than rupee values. A third of the
 * filings report no value, so a rupee axis silently understates the days where
 * the unreported ones happen to be the large trades.
 */

/** Round an axis bound up to something a reader can hold in their head. */
export function niceBound(value) {
  const magnitude = Math.abs(value);
  if (!Number.isFinite(magnitude) || magnitude === 0) return 1;
  const power = 10 ** Math.floor(Math.log10(magnitude));
  for (const step of [1, 2, 2.5, 5, 10]) {
    if (magnitude <= step * power) return step * power;
  }
  return 10 * power;
}

/**
 * Buys above the axis, sells below, and the running total as a line across it.
 *
 * The two are drawn on separate scales on purpose. A single day rarely carries
 * more than a few dozen filings while the running total climbs into the
 * hundreds, so sharing one axis would flatten the daily bars into the baseline.
 * The axis each series belongs to is labelled on the chart.
 */
export function flowChart(days, { width = 960, height = 260, gutter = 44, pad = 16 } = {}) {
  const points = (days || []).filter((day) => day && day.date);
  if (!points.length) return { empty: true, bars: [], line: '', width, height };

  const plotWidth = Math.max(width - gutter * 2, 1);
  const plotHeight = Math.max(height - pad * 2, 1);
  const zeroY = pad + plotHeight / 2;

  const barBound = niceBound(Math.max(...points.map((d) => Math.max(d.buys || 0, d.sells || 0)), 1));
  const netValues = points.map((d) => d.cumulativeNet || 0);
  const netBound = niceBound(Math.max(Math.abs(Math.min(...netValues, 0)), Math.abs(Math.max(...netValues, 0)), 1));

  const slot = plotWidth / points.length;
  // Leave a visible gap between days without letting a long window shrink the
  // bars to invisibility.
  const barWidth = Math.max(Math.min(slot * 0.52, 22), 3);

  const bars = [];
  points.forEach((day, index) => {
    const centre = gutter + slot * (index + 0.5);
    for (const [key, direction] of [['buys', -1], ['sells', 1]]) {
      const count = day[key] || 0;
      if (!count) continue;
      const length = (count / barBound) * (plotHeight / 2);
      bars.push({
        date: day.date,
        kind: key === 'buys' ? 'buy' : 'sell',
        count,
        x: centre - barWidth / 2,
        y: direction < 0 ? zeroY - length : zeroY,
        width: barWidth,
        height: Math.max(length, 1),
      });
    }
  });

  const line = points
    .map((day, index) => {
      const x = gutter + slot * (index + 0.5);
      const y = zeroY - ((day.cumulativeNet || 0) / netBound) * (plotHeight / 2);
      return `${index ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');

  return {
    empty: false,
    width,
    height,
    zeroY,
    barBound,
    netBound,
    bars,
    line,
    marks: points.map((day, index) => ({
      date: day.date,
      x: gutter + slot * (index + 0.5),
      cumulativeNet: day.cumulativeNet || 0,
      buys: day.buys || 0,
      sells: day.sells || 0,
    })),
  };
}

/**
 * Proportional widths for the mode breakdown.
 *
 * Anything below the floor still gets a sliver: a category with four filings
 * out of a thousand would otherwise render as nothing and read as absent
 * rather than small.
 */
export function shareBars(entries, { minPct = 0.6 } = {}) {
  const rows = (entries || []).filter((entry) => (entry?.count || 0) > 0);
  const total = rows.reduce((sum, entry) => sum + entry.count, 0);
  if (!total) return [];
  return rows.map((entry) => ({
    ...entry,
    pct: (entry.count / total) * 100,
    width: Math.max((entry.count / total) * 100, minPct),
  }));
}

/** A sparkline for one company's running position, scaled to its own range. */
export function sparkline(values, { width = 120, height = 28 } = {}) {
  const points = (values || []).filter((value) => Number.isFinite(value));
  if (points.length < 2) return '';
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  return points
    .map((value, index) => {
      const x = (index / (points.length - 1)) * width;
      const y = height - ((value - min) / span) * height;
      return `${index ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
}
