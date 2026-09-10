/**
 * What a manager's book says about how it is run.
 *
 * The site already carries a `strategy` label on ten of fifty-one managers,
 * hand-written at seed time: "Concentrated activist", "Fundamental growth".
 * Those are assertions. Nothing in the database supports or contradicts them,
 * they were never checked against a filing, and forty-one managers have none.
 *
 * This derives the same kind of statement from the holdings themselves. A
 * brochure states a strategy; a book demonstrates one, and the demonstration
 * is what we already store: how many positions, how much sits in the largest
 * ten, whether there are options in it, how much of it is new since last
 * quarter, how long the typical position has been held, whether the manager
 * votes what it owns, and whether it files 13D.
 *
 * Two deliberate limits.
 *
 * The first is on "why". Saying why a manager runs a strategy is attribution,
 * and unless they have said so publicly it is a guess wearing the clothes of
 * research. Every archetype here carries a `characteristicOf` line instead,
 * which says what a book shaped like this is characteristic of. "A book that
 * turns over half its names each quarter is characteristic of tactical
 * management" is an observation about the book. "They do this because they
 * believe X" is not, and is the kind of sentence that eventually has to be
 * retracted. The distinction is the whole design.
 *
 * The second is on certainty. 13F shows US long equity and nothing else - no
 * shorts, no bonds, no foreign listings, no cash. A manager whose 13F looks
 * concentrated may be running a diversified book of which we see one corner.
 * Every profile therefore carries caveats, and a metric we cannot measure is
 * absent rather than defaulted: `turnoverPct` is null when there is no prior
 * quarter to compare against, not zero. Norges Bank measured 100% new
 * positions in the first sweep, which is not a strategy, it is a manager with
 * one stored quarter. A null says that; a zero would have lied.
 */

/** Archetypes, narrowest first. The first whose `when` holds is the answer. */
export const ARCHETYPES = [
  {
    key: 'market_making',
    label: 'Multi-strategy / market making',
    characteristicOf:
      'thousands of positions carried alongside heavy options exposure, which '
      + 'is characteristic of a book held to facilitate and hedge trading rather '
      + 'than to express a view on each name',
    when: (m) => m.positions >= 1000 && m.optionsPct >= 25,
  },
  {
    key: 'derivatives_overlay',
    label: 'Concentrated with a derivatives overlay',
    characteristicOf:
      'a small book in which a large share of the reported lines are options, '
      + 'which is characteristic of positions expressed through contracts rather '
      + 'than shares - including bearish ones, since a put is reported here the '
      + 'same way a long is',
    when: (m) => m.positions < 1000 && m.optionsPct >= 25,
  },
  {
    key: 'systematic_broad',
    label: 'Broad and evenly weighted',
    characteristicOf:
      'more names than a discretionary team could research, spread evenly '
      + 'enough that no position is a bet on its own, which is characteristic '
      + 'of systematic or quantitative management',
    // Options exposure is the discriminator, not concentration alone. A bank's
    // 13F is broad and evenly weighted too - Goldman reports 19% in its
    // largest ten, inside the band below - but it reports 14% of its lines as
    // options and a systematic equity book reports none.
    when: (m) => m.positions >= 1000 && m.top10Pct <= 20 && m.optionsPct < 5,
  },
  {
    key: 'broad_low_turnover',
    label: 'Broad book, low turnover',
    characteristicOf:
      'a wide book that barely changes between quarters, which is '
      + 'characteristic of index-tracking or of long-horizon mandates - 13F '
      + 'alone cannot separate the two',
    when: (m) => m.positions >= 1000 && known(m.turnoverPct) && m.turnoverPct <= 8,
  },
  {
    key: 'diversified_broad',
    label: 'Diversified across many names',
    characteristicOf:
      'a wide book that is actively changed, which is characteristic of a firm '
      + 'running many mandates at once rather than one strategy',
    when: (m) => m.positions >= 1000,
  },
  {
    key: 'concentrated_held',
    label: 'Concentrated and held',
    characteristicOf:
      'most of the book in ten names and almost nothing new this quarter, '
      + 'which is characteristic of buy-and-hold ownership rather than trading',
    when: (m) => m.top10Pct >= 50 && known(m.turnoverPct) && m.turnoverPct <= 10,
  },
  {
    key: 'concentrated_rotated',
    label: 'Concentrated and actively rotated',
    characteristicOf:
      'large positions that are replaced rather than held, which is '
      + 'characteristic of high-conviction management on a short horizon',
    when: (m) => m.top10Pct >= 50 && known(m.turnoverPct) && m.turnoverPct >= 30,
  },
  {
    key: 'concentrated',
    label: 'Concentrated',
    characteristicOf:
      'a book where ten names carry most of the value, which is characteristic '
      + 'of selection rather than diversification',
    when: (m) => m.top10Pct >= 50,
  },
  {
    key: 'focused_rotated',
    label: 'Focused and actively rotated',
    characteristicOf:
      'a short list of names, none dominant, replaced quickly - characteristic '
      + 'of trading a research view rather than owning it',
    when: (m) => m.positions < 1000 && known(m.turnoverPct) && m.turnoverPct >= 30,
  },
  {
    key: 'selective_diversified',
    // Not "focused": this is the bucket a 997-name book lands in, and calling
    // that focused because it sits three positions under the broad threshold
    // is the label arguing with its own evidence.
    label: 'Selective and diversified',
    characteristicOf:
      'a bounded list of names with no single dominant position, which is '
      + 'characteristic of research-led management that sizes for survivability '
      + 'rather than for conviction',
    when: (m) => m.positions < 1000,
  },
];

function known(value) {
  return Number.isFinite(value);
}

function pct(value) {
  return known(value) ? Math.round(value * 10) / 10 : null;
}

/**
 * Traits that hold independently of the archetype.
 *
 * These are the ones that carry across every shape of book: a concentrated
 * manager and a broad one can both file 13D, and both can decline to vote.
 * Kept separate from the archetype so that adding one does not renumber the
 * classification, and so that a manager reads as a set of facts rather than
 * as a single bucket.
 */
export function traitsFor(metrics) {
  const m = metrics || {};
  const traits = [];

  if (m.activistFilings > 0) {
    traits.push({
      key: 'activist',
      label: 'Files 13D',
      detail:
        `${m.activistFilings} Schedule 13D filing${m.activistFilings === 1 ? '' : 's'}. `
        + '13D is the schedule for a holder who intends to influence the company; '
        + '13G is for one who does not. The choice is the manager\'s own and is '
        + 'the plainest statement of intent in the public record.',
    });
  } else if (m.passiveFilings > 0) {
    traits.push({
      key: 'passive_stakes',
      label: 'Files 13G only',
      detail:
        `${m.passiveFilings} Schedule 13G filing${m.passiveFilings === 1 ? '' : 's'} `
        + 'and no 13D. Large stakes are declared as held without intent to '
        + 'influence control.',
    });
  }

  // Voting authority is reported on the filing itself. A manager reporting
  // sole voting authority on nearly everything is voting its own book; one
  // reporting almost none has the shares but not the vote, which is what a
  // custodian or an index platform whose funds vote separately looks like.
  if (known(m.votesPct)) {
    if (m.votesPct <= 25) {
      traits.push({
        key: 'votes_rarely',
        label: 'Holds without the vote',
        detail:
          `Sole voting authority reported on ${pct(m.votesPct)}% of positions. The `
          + 'shares are held here; the vote sits elsewhere.',
      });
    } else if (m.votesPct >= 95) {
      traits.push({
        key: 'votes_own_book',
        label: 'Votes its own book',
        detail: `Sole voting authority reported on ${pct(m.votesPct)}% of positions.`,
      });
    }
  }

  if (known(m.medianQuartersHeld) && m.medianQuartersHeld >= 4) {
    traits.push({
      key: 'long_held',
      label: 'Long-held positions',
      detail:
        `The median position has appeared in ${m.medianQuartersHeld} of the `
        + `${m.quartersObserved || m.medianQuartersHeld} stored quarterly filings. `
        + 'Appearances, not an unbroken run: a position sold and rebought counts twice.',
    });
  }

  if (known(m.topSectorPct) && m.topSectorPct >= 50 && m.topSector) {
    traits.push({
      key: 'sector_concentrated',
      label: `Concentrated in ${m.topSector}`,
      detail: `${pct(m.topSectorPct)}% of reported value sits in one sector.`,
    });
  }

  return traits;
}

/**
 * Why a profile might be wrong, stated on the profile.
 *
 * A caveat that lives in a code comment protects nobody. These are returned
 * with the profile so the page can show them next to the claim they qualify.
 */
export function caveatsFor(metrics) {
  const m = metrics || {};
  const caveats = [
    '13F reports US-listed long equity and options only. Short positions, '
    + 'bonds, cash, foreign listings and private holdings are not in it, so '
    + 'this describes the reported book and not necessarily the whole one.',
  ];

  if (!known(m.turnoverPct)) {
    caveats.push(
      'Only one quarter is stored for this manager, so turnover and holding '
      + 'period cannot be measured yet.',
    );
  } else if (m.priorPositions > 0 && m.quartersObserved < 4) {
    caveats.push(
      `Measured across ${m.quartersObserved} stored quarters, which is a short `
      + 'history to draw a pattern from.',
    );
  }

  if (m.positions < 10) {
    caveats.push(
      `Only ${m.positions} reported positions. Concentration measured on a book `
      + 'this small says more about what is reportable than about conviction.',
    );
  }

  return caveats;
}

/**
 * How much weight the archetype can bear.
 *
 * Low when a defining metric is missing or the book is too small to shape.
 * Medium when the manager sits within five points of the boundary that
 * decided it - the label would flip on a small revision, and saying so is
 * cheaper than defending it later.
 */
export function confidenceFor(metrics, archetype) {
  const m = metrics || {};
  if (!known(m.turnoverPct) || m.positions < 10) return 'low';

  const nearBoundary =
    Math.abs(m.top10Pct - 50) < 5
    || Math.abs(m.optionsPct - 25) < 5
    || (m.positions >= 900 && m.positions < 1100)
    || (archetype.key === 'broad_low_turnover' && Math.abs(m.turnoverPct - 8) < 3)
    || (archetype.key === 'concentrated_held' && Math.abs(m.turnoverPct - 10) < 3)
    || (archetype.key === 'concentrated_rotated' && Math.abs(m.turnoverPct - 30) < 5);

  if (nearBoundary) return 'medium';
  if (m.quartersObserved < 4) return 'medium';
  return 'high';
}

/**
 * The evidence, in the order a reader would want it.
 *
 * Every line is a measured number with its unit. Nothing here is inferred;
 * the inference is the archetype, and it is separate on purpose so a reader
 * who disagrees with the label can still use the numbers.
 */
export function evidenceFor(metrics) {
  const m = metrics || {};
  const rows = [
    { key: 'positions', label: 'Reported positions', value: m.positions, unit: 'count' },
    { key: 'top10', label: 'Value in the largest ten', value: pct(m.top10Pct), unit: 'percent' },
  ];
  if (known(m.turnoverPct)) {
    rows.push({ key: 'turnover', label: 'Positions new this quarter', value: pct(m.turnoverPct), unit: 'percent' });
  }
  if (known(m.medianQuartersHeld)) {
    rows.push({ key: 'held', label: 'Median quarters held', value: m.medianQuartersHeld, unit: 'quarters' });
  }
  if (known(m.optionsPct) && m.optionsPct > 0) {
    rows.push({ key: 'options', label: 'Lines that are options', value: pct(m.optionsPct), unit: 'percent' });
  }
  if (known(m.votesPct)) {
    rows.push({ key: 'votes', label: 'Sole voting authority', value: pct(m.votesPct), unit: 'percent' });
  }
  if (m.topSector && known(m.topSectorPct)) {
    rows.push({ key: 'sector', label: `Largest sector (${m.topSector})`, value: pct(m.topSectorPct), unit: 'percent' });
  }
  return rows;
}

/**
 * The whole profile for one manager.
 *
 * Returns null rather than guessing when there is nothing to classify: a
 * manager with no reported positions has no book to describe, and an
 * archetype invented for it would be the fabrication this whole file exists
 * to avoid.
 */
export function strategyProfile(metrics) {
  const m = metrics || {};
  if (!Number.isFinite(m.positions) || m.positions <= 0) return null;

  const archetype = ARCHETYPES.find((row) => row.when(m));
  // The last archetype has no lower bound on positions, so a book with any
  // position at all matches something. If that ever stops being true the
  // profile is absent rather than wrong.
  if (!archetype) return null;

  return {
    archetype: archetype.key,
    label: archetype.label,
    characteristicOf: archetype.characteristicOf,
    confidence: confidenceFor(m, archetype),
    evidence: evidenceFor(m),
    traits: traitsFor(m),
    caveats: caveatsFor(m),
  };
}
