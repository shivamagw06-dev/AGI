import { memo, useCallback, useEffect, useRef, useState } from 'react';

/**
 * One publisher's live broadcast, in that publisher's own player.
 *
 * Generic on purpose: Bloomberg and NDTV Profit differ only by the config
 * object passed in, so there is no publisher-specific branch here and adding a
 * third broadcast is a config change rather than a component change.
 *
 * Wrapped in memo, and this matters more than it looks. The desk refreshes its
 * market data every 45 seconds; if that re-render reached the iframe, both
 * streams would restart from the top three times a minute and the page would
 * be unusable. The broadcast objects are frozen module constants and the
 * callbacks are stable, so the props never change identity and the iframe is
 * never touched by a data refresh.
 *
 * The stream stays the publisher's: standard embed, their branding and
 * YouTube's controls untouched, no AGI overlay on the video, no proxying or
 * recording. Attribution sits directly beneath the frame.
 */
function LiveBroadcastPlayer({ broadcast, compact = false, onMinimize, canMinimize = false }) {
  const [started, setStarted] = useState(false);
  const [failed, setFailed] = useState(false);
  const loaded = useRef(false);

  const start = useCallback(() => setStarted(true), []);

  // A frame that never loads must not leave a dead black box on the page.
  useEffect(() => {
    if (!started) return undefined;
    loaded.current = false;
    const timer = setTimeout(() => {
      if (!loaded.current) setFailed(true);
    }, 12_000);
    return () => clearTimeout(timer);
  }, [started]);

  const onLoad = useCallback(() => { loaded.current = true; }, []);

  // Bound here rather than in the parent. An arrow created in the grid would be
  // a new prop identity on every render, which defeats memo and is exactly how
  // a data refresh ends up restarting the stream.
  const handleMinimize = useCallback(
    () => onMinimize?.(broadcast.id),
    [onMinimize, broadcast.id]
  );

  const { market, title, provider, embedUrl, externalUrl, attribution } = broadcast;

  if (failed) {
    return (
      <section className="ld-card ld-broadcast">
        <div className="ld-card-head">
          <span className="ld-label">{market}</span>
          <span className="ld-label">{title}</span>
        </div>
        <div className="ld-state ld-state-err">
          {title} is currently unavailable in the embedded player.
          <div style={{ marginTop: '0.5rem' }}>
            <a href={externalUrl} target="_blank" rel="noopener noreferrer">Watch on YouTube ↗</a>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="ld-card ld-broadcast">
      <div className="ld-card-head">
        <span className="ld-label">{market}</span>
        <span className="ld-broadcast-head-right">
          <span className="ld-live-dot">{provider}</span>
          {canMinimize && onMinimize ? (
            <button type="button" className="ld-minimize" onClick={handleMinimize}>
              Minimize
            </button>
          ) : null}
        </span>
      </div>

      <div className="ld-broadcast-title">{title}</div>

      <div className={compact ? 'ld-video-frame ld-video-compact' : 'ld-video-frame'}>
        {started ? (
          <iframe
            src={embedUrl}
            title={`${title} — live broadcast by ${provider}`}
            loading="lazy"
            onLoad={onLoad}
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
          />
        ) : (
          // Created on click, not on mount. Two YouTube embeds pull several
          // megabytes of player before anything is watched, and nothing here
          // autoplays - two broadcasts talking over each other on page load
          // would be the first thing a reader closed.
          <button type="button" className="ld-video-poster" onClick={start}>
            <span className="ld-play" aria-hidden="true">▶</span>
            <span className="ld-label">{title}</span>
            <span className="ld-poster-hint">Watch live · audio starts muted until you unmute</span>
          </button>
        )}
      </div>

      <div className="ld-attrib">
        <span className="ld-attrib-text">{attribution}</span>
        <a href={externalUrl} target="_blank" rel="noopener noreferrer">Watch on YouTube ↗</a>
      </div>
    </section>
  );
}

export default memo(LiveBroadcastPlayer);
