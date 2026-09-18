/**
 * The live basket: feed in, snapshots out.
 *
 * Owns nothing it does not have to. `UpstoxMarketFeedV3` owns the socket,
 * `SynchronizedSnapshotStore` owns tick validity, `aiEnablersQuotes` owns the
 * shape change and the fallback, and `aiEnablersIndex` owns the arithmetic.
 * This module is the loop that joins them and the memory that holds a minute
 * of history.
 *
 * It computes only what the first live version needs: price, day return,
 * basket return, layer and sub-layer return, breadth, contribution, relative
 * return against the benchmark, and volume ratio. No signals. A signal built
 * on a feed nobody has watched for a week is a guess with a timestamp.
 */

import { SynchronizedSnapshotStore, UpstoxMarketFeedV3 } from './upstoxMarketFeedV3.js';
import { LastGoodPrices, quoteBook, universeInstrumentKeys, volumeRatio } from './aiEnablersQuotes.js';
import { COVERAGE_FLOOR, computeIndex, STALE_MS } from './aiEnablersIndex.js';
import { actionsNear } from './aiEnablersStatements.js';

/** The IST calendar date of an instant, so a refresh follows the exchange day. */
const istDate = (ms) => new Date(ms + 330 * 60_000).toISOString().slice(0, 10);

/** One snapshot a minute, kept for a trading day. */
export const SNAPSHOT_INTERVAL_MS = 60_000;
export const SNAPSHOT_RETENTION = 400;

/**
 * A snapshot of the basket at one instant.
 *
 * Deliberately includes the refusals. A snapshot history that only contains
 * the minutes the index was computable is a history that cannot answer "was
 * the feed up?", which is the first question anyone asks of a level that
 * looks wrong.
 */
export function snapshotFrom(universe, book, { now = Date.now(), volumeBaselines = {}, ...options } = {}) {
  const index = computeIndex(universe, book.quotes, {
    ...options,
    now,
    benchmark: book.benchmark,
    staleMs: options.staleMs ?? STALE_MS,
  });

  const volumes = {};
  for (const [symbol, key] of universeInstrumentKeys(universe).bySymbol) {
    const quote = book.quotes[symbol];
    if (!quote) continue;
    volumes[symbol] = volumeRatio({
      cumulativeVolume: book.volumes?.[key] ?? null,
      averageDailyVolume: volumeBaselines[symbol] ?? null,
      now,
    });
  }

  return {
    at: new Date(now).toISOString(),
    status: index.status,
    index,
    quality: {
      live: book.sources.live.length,
      last_good: book.sources.last_good.length,
      missing: book.sources.missing.length,
      unresolved: book.unresolved,
      // A basket priced largely from last-good is not a live basket, and the
      // page must be able to say so without recomputing anything.
      live_share: book.sources.live.length + book.sources.last_good.length
        ? Number((book.sources.live.length
          / (book.sources.live.length + book.sources.last_good.length)).toFixed(4))
        : 0,
    },
    volumes,
  };
}

/**
 * Which members the corporate-action guard is and is not covering.
 *
 * Attached by the runtime, which is where that state lives. Kept out of
 * snapshotFrom's signature so a caller recomputing from a bare book does not
 * have to invent it.
 */
function withCorporateActions(snapshot, runtime) {
  const flagged = Object.entries(runtime.priceBreaks || {})
    .filter(([, one]) => one?.priceBreak)
    .map(([symbol, one]) => ({ symbol, reason: one.reason, actions: one.actions }));
  snapshot.corporateActions = {
    readFor: runtime.corporateActionsDate,
    excluded: flagged,
    unread: runtime.corporateActionsErrors || [],
  };
  return snapshot;
}

export class AiEnablersLiveRuntime {
  constructor({
    universe,
    store = new SynchronizedSnapshotStore(),
    lastGood = new LastGoodPrices(),
    coverageFloor = COVERAGE_FLOOR,
    staleMs = STALE_MS,
    snapshotIntervalMs = SNAPSHOT_INTERVAL_MS,
    retention = SNAPSHOT_RETENTION,
    volumeBaselines = {},
    feedFactory = (options) => new UpstoxMarketFeedV3(options),
    fetchCorporateActions = null,
    now = () => Date.now(),
  } = {}) {
    this.universe = universe;
    this.store = store;
    this.lastGood = lastGood;
    this.coverageFloor = coverageFloor;
    this.staleMs = staleMs;
    this.snapshotIntervalMs = snapshotIntervalMs;
    this.retention = retention;
    this.volumeBaselines = volumeBaselines;
    this.feedFactory = feedFactory;
    this.fetchCorporateActions = fetchCorporateActions;
    this.now = now;
    // Per-symbol corporate-action state, and the exchange day it was read for.
    this.priceBreaks = {};
    this.corporateActionsDate = null;
    this.corporateActionsErrors = [];
    this.feed = null;
    this.timer = null;
    this.snapshots = [];
    this.resolved = universeInstrumentKeys(universe);
  }

  /**
   * Read each member's corporate actions and flag any near its ex-date.
   *
   * The index has excluded a quote marked priceBreak since the guard was
   * written, and until now nothing marked one: a one-for-one bonus against an
   * unadjusted previous close would have printed a fifty per cent loss and
   * reconciled at every level. This is what sets the flag.
   *
   * A member whose actions cannot be read is recorded as such rather than
   * treated as clear. Silence about a corporate action is not evidence that
   * there is none, and the page should be able to say which members the
   * guard is not covering.
   */
  async refreshCorporateActions() {
    if (!this.fetchCorporateActions) return { refreshed: false, reason: 'no corporate-actions source' };
    const now = this.now();
    const members = (this.universe?.members || []).filter((one) => one.admitted !== false);
    const next = {};
    const errors = [];
    for (const member of members) {
      if (!member.isin) {
        errors.push({ symbol: member.symbol, error: 'NO_ISIN' });
        continue;
      }
      try {
        const payload = await this.fetchCorporateActions(member.isin);
        const near = actionsNear(payload, { now });
        next[member.symbol] = near;
      } catch (error) {
        errors.push({ symbol: member.symbol, error: String(error?.message || error) });
      }
    }
    this.priceBreaks = next;
    this.corporateActionsErrors = errors;
    this.corporateActionsDate = istDate(now);
    return { refreshed: true, date: this.corporateActionsDate, errors };
  }

  /** Re-read corporate actions once per exchange day, not once per process. */
  async #refreshIfNewDay() {
    if (!this.fetchCorporateActions) return;
    if (this.corporateActionsDate === istDate(this.now())) return;
    try {
      await this.refreshCorporateActions();
    } catch {
      // Recorded per member inside refreshCorporateActions; a whole-refresh
      // failure leaves the previous day's state rather than clearing it.
    }
  }

  /** The current basket, computed fresh. Safe to call at any cadence. */
  current() {
    const now = this.now();
    const book = quoteBook(this.universe, {
      store: this.store, lastGood: this.lastGood, now, staleMs: this.staleMs,
      priceBreaks: this.priceBreaks,
    });
    book.volumes = Object.fromEntries(
      this.resolved.keys.map((key) => [key, this.store.get(key)?.cumulative_volume ?? null]),
    );
    return withCorporateActions(snapshotFrom(this.universe, book, {
      now,
      coverageFloor: this.coverageFloor,
      staleMs: this.staleMs,
      volumeBaselines: this.volumeBaselines,
    }), this);
  }

  /** Take one snapshot and retain it. Returns the snapshot. */
  tick() {
    // Fire-and-forget: a slow corporate-actions read must not delay a tick.
    this.#refreshIfNewDay();
    const snapshot = this.current();
    this.snapshots.push(snapshot);
    if (this.snapshots.length > this.retention) {
      this.snapshots.splice(0, this.snapshots.length - this.retention);
    }
    return snapshot;
  }

  history() {
    return [...this.snapshots];
  }

  async start() {
    if (this.feed) return this.status();
    if (!this.resolved.keys.length) {
      throw new Error('No instrument keys resolved from the universe; nothing to subscribe to.');
    }
    this.feed = this.feedFactory({
      instrumentKeys: this.resolved.keys,
      mode: 'full',
      snapshotStore: this.store,
    });
    await this.feed.start();
    await this.#refreshIfNewDay();
    this.timer = setInterval(() => this.tick(), this.snapshotIntervalMs);
    if (this.timer.unref) this.timer.unref();
    return this.status();
  }

  async stop() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    if (this.feed?.stop) await this.feed.stop();
    this.feed = null;
  }

  status() {
    return {
      subscribed: this.resolved.keys.length,
      unresolved: this.resolved.unresolved,
      benchmarkKey: this.resolved.benchmarkKey,
      feed: this.feed?.status?.() || { status: 'idle' },
      snapshots: this.snapshots.length,
      store: this.store.stats?.() || null,
    };
  }
}
