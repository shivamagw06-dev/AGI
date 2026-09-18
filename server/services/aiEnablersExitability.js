/**
 * Liquidity as a sizing attribute, not an eligibility filter.
 *
 * The earlier Stage 2 asked "is this company liquid enough to be in the
 * index?" and needed a turnover floor to answer it. Every floor it could have
 * used was fitted to the seven companies in front of it, which is how a
 * threshold becomes indefensible.
 *
 * The right question is a different one. A company does not stop being an AI
 * enabler because a fifty-crore position would be too large for it - it stops
 * being able to carry a fifty-crore position. So eligibility comes from
 * thematic evidence and sizing comes from liquidity, and what the screen
 * produces is not a pass or a fail but a maximum executable position:
 *
 *   minimum ADVT      = target position / (exit days x max participation)
 *   max executable    = ADVT x exit days x max participation
 *
 * A name is only excluded where its executable size rounds to nothing, which
 * is a statement about the security rather than about the threshold.
 */

const numeric = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

/** The policy the whole calculation hangs on, stated once and printed. */
export const DEFAULT_POLICY = Object.freeze({
  targetPosition: null,      // set by the portfolio, not by this module
  exitDays: 3,
  maxParticipation: 0.20,
});

/**
 * The turnover a target position requires.
 *
 * Inverse of the executable-size calculation, kept separate because it is the
 * form the policy is usually stated in: "a fifty-crore position must exit in
 * three days at no more than a fifth of normal volume".
 */
export function minimumAdvt({ targetPosition, exitDays = 3, maxParticipation = 0.2 }) {
  const position = numeric(targetPosition);
  const days = numeric(exitDays);
  const participation = numeric(maxParticipation);
  if (position === null || position <= 0) return { value: null, reason: 'NO_TARGET_POSITION' };
  if (days === null || days <= 0) return { value: null, reason: 'INVALID_EXIT_DAYS' };
  if (participation === null || participation <= 0 || participation > 1) {
    return { value: null, reason: 'INVALID_PARTICIPATION' };
  }
  return { value: position / (days * participation), reason: null };
}

/**
 * Normal daily traded value, made robust.
 *
 * The lower of the twenty-day and sixty-day medians. Medians rather than
 * means because a single block trade moves a mean enough to make a thin name
 * look executable; the lower of two windows because one abnormally busy week
 * inside the shorter window should not be able to do the same.
 */
export function normalAdvt({ turnoverSeries, shortWindow = 20, longWindow = 60, minSessions = 20 }) {
  const values = (turnoverSeries || []).map(numeric).filter((one) => one !== null && one >= 0);
  if (values.length < minSessions) {
    return { value: null, reason: 'INSUFFICIENT_HISTORY', sessions: values.length, need: minSessions };
  }
  const medianOf = (window) => {
    const slice = values.slice(0, window);
    if (slice.length < Math.min(window, minSessions)) return null;
    const sorted = [...slice].sort((a, b) => a - b);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
  };
  const short = medianOf(shortWindow);
  const long = medianOf(longWindow);
  const candidates = [short, long].filter((one) => one !== null);
  if (!candidates.length) return { value: null, reason: 'INSUFFICIENT_HISTORY', sessions: values.length };
  return {
    value: Math.min(...candidates),
    short, long,
    windowUsed: short !== null && (long === null || short <= long) ? shortWindow : longWindow,
    sessions: values.length,
    reason: null,
  };
}

/**
 * How large a position this security can carry under the policy.
 *
 * Returned for every member, including ones whose executable size is far
 * below any target. That is the point: the company stays in the intelligence
 * universe and carries a smaller number beside it.
 */
export function executableFor({ advt, exitDays = 3, maxParticipation = 0.2, targetPosition = null }) {
  const daily = numeric(advt);
  const days = numeric(exitDays);
  const participation = numeric(maxParticipation);
  if (daily === null || daily <= 0) {
    return { maxExecutablePosition: null, meetsTarget: null, reason: 'NO_TURNOVER' };
  }
  if (days === null || days <= 0 || participation === null || participation <= 0 || participation > 1) {
    return { maxExecutablePosition: null, meetsTarget: null, reason: 'INVALID_POLICY' };
  }
  const maxExecutablePosition = daily * days * participation;
  const target = numeric(targetPosition);
  return {
    maxExecutablePosition,
    // Null rather than false when no target is set: whether a size is
    // sufficient is a question nobody asked yet.
    meetsTarget: target === null || target <= 0 ? null : maxExecutablePosition >= target,
    shortfall: target !== null && target > 0 && maxExecutablePosition < target
      ? target - maxExecutablePosition : null,
    reason: null,
  };
}

/**
 * Stage 2, restated: size every member, exclude almost none.
 *
 * `excludeBelow` exists for the genuinely untradable - a security whose
 * executable position is below the smallest size worth holding - and defaults
 * to nothing being excluded, so the decision to drop a name is always one
 * somebody made explicitly.
 */
export function sizePositions(members, {
  targetPosition = null, exitDays = 3, maxParticipation = 0.2, excludeBelow = null,
} = {}) {
  const policy = { targetPosition, exitDays, maxParticipation, excludeBelow };
  const required = minimumAdvt({ targetPosition, exitDays, maxParticipation });

  const sized = [];
  const unscreened = [];
  const excluded = [];
  for (const member of members || []) {
    const advt = numeric(member.normalAdvt ?? member.medianDailyTurnover);
    if (advt === null) {
      unscreened.push({ symbol: member.symbol, reason: 'NO_TURNOVER_HISTORY' });
      continue;
    }
    const executable = executableFor({ advt, exitDays, maxParticipation, targetPosition });
    const row = {
      symbol: member.symbol,
      normalAdvt: advt,
      maxExecutablePosition: executable.maxExecutablePosition,
      meetsTarget: executable.meetsTarget,
      shortfall: executable.shortfall,
    };
    const floor = numeric(excludeBelow);
    if (floor !== null && executable.maxExecutablePosition < floor) {
      excluded.push({ ...row, reason: 'BELOW_MINIMUM_EXECUTABLE_POSITION' });
      continue;
    }
    sized.push(row);
  }

  return {
    stage: 2,
    policy,
    minimumAdvtForTarget: required.value,
    minimumAdvtReason: required.reason,
    sized: sized.sort((a, b) => b.maxExecutablePosition - a.maxExecutablePosition),
    unscreened,
    excluded,
    // Members that stay in the universe but cannot carry the target size.
    belowTarget: sized.filter((one) => one.meetsTarget === false).map((one) => one.symbol),
  };
}
