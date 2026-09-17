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
    this.now = now;
    this.feed = null;
    this.timer = null;
    this.snapshots = [];
    this.resolved = universeInstrumentKeys(universe);
  }

  /** The current basket, computed fresh. Safe to call at any cadence. */
  current() {
    const now = this.now();
    const book = quoteBook(this.universe, {
      store: this.store, lastGood: this.lastGood, now, staleMs: this.staleMs,
    });
    book.volumes = Object.fromEntries(
      this.resolved.keys.map((key) => [key, this.store.get(key)?.cumulative_volume ?? null]),
    );
    return snapshotFrom(this.universe, book, {
      now,
      coverageFloor: this.coverageFloor,
      staleMs: this.staleMs,
      volumeBaselines: this.volumeBaselines,
    });
  }

  /** Take one snapshot and retain it. Returns the snapshot. */
  tick() {
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
