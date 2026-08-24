import { useCallback, useEffect, useRef, useState } from 'react';
import {
  BLOOMBERG_ATTRIBUTION,
  BLOOMBERG_LIVE_EMBED_URL,
  BLOOMBERG_LIVE_WATCH_URL,
} from '@/lib/liveDeskConfig';

/**
 * Bloomberg's public livestream in YouTube's own player.
 *
 * The stream is Bloomberg's and stays Bloomberg's: standard embed, their
 * branding and YouTube's chrome untouched, no AGI overlay on the video, no
 * proxying or recording. Attribution sits directly beneath the frame.
 *
 * The iframe is created on click rather than on mount. YouTube's embed pulls
 * roughly a megabyte of player before anything is watched, and this page is
 * mostly read, not watched - the desk should be usable before the video is.
 */
export default function BloombergLivePlayer({ pip = false, onMinimize, onRestore, onClose }) {
  const [started, setStarted] = useState(false);
  const [failed, setFailed] = useState(false);
  const frameRef = useRef(null);
  const settled = useRef(false);

  const start = useCallback(() => setStarted(true), []);

  // An embed that never loads must not leave a dead black box. If nothing has
  // loaded after a reasonable wait, fall back to the link.
  useEffect(() => {
    if (!started) return undefined;
    settled.current = false;
    const timer = setTimeout(() => {
      if (!settled.current) setFailed(true);
    }, 12_000);
    return () => clearTimeout(timer);
  }, [started]);

  const onLoad = () => { settled.current = true; };

  if (failed) {
    return (
      <div className="ld-card">
        <div className="ld-state ld-state-err">
          Bloomberg Live is currently unavailable in the embedded player.
          <div style={{ marginTop: '0.5rem' }}>
            <a href={BLOOMBERG_LIVE_WATCH_URL} target="_blank" rel="noopener noreferrer">
              Watch on YouTube ↗
            </a>
          </div>
        </div>
      </div>
    );
  }

  const frame = (
    <div className="ld-video-frame" ref={frameRef}>
      {started ? (
        <iframe
          src={BLOOMBERG_LIVE_EMBED_URL}
          title="Bloomberg Live"
          loading="lazy"
          onLoad={onLoad}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin"
        />
      ) : (
        <button type="button" className="ld-video-poster" onClick={start}>
          <span className="ld-play" aria-hidden="true">▶</span>
          <span className="ld-label">Bloomberg Live</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--ld-muted)' }}>Watch live</span>
        </button>
      )}
    </div>
  );

  if (pip) {
    return (
      <div className="ld-pip">
        <div className="ld-pip-bar">
          <span className="ld-label">Bloomberg Live</span>
          <span style={{ display: 'flex', gap: '0.6rem' }}>
            <button type="button" onClick={onRestore}>Restore</button>
            <button type="button" onClick={onClose}>Close</button>
          </span>
        </div>
        {frame}
      </div>
    );
  }

  return (
    <div className="ld-card">
      <div className="ld-card-head">
        <span className="ld-label">Live Financial TV</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
          <span className="ld-live-dot">Bloomberg Live</span>
          {onMinimize ? (
            <button
              type="button"
              onClick={onMinimize}
              style={{
                background: 'none', border: 0, cursor: 'pointer', color: 'var(--ld-muted)',
                font: 'inherit', fontFamily: 'var(--ld-mono)', fontSize: '0.66rem',
                letterSpacing: '0.08em', textTransform: 'uppercase',
              }}
            >
              Minimize
            </button>
          ) : null}
        </span>
      </div>
      {frame}
      <div className="ld-attrib">
        <span className="ld-attrib-text">{BLOOMBERG_ATTRIBUTION}</span>
        <a href={BLOOMBERG_LIVE_WATCH_URL} target="_blank" rel="noopener noreferrer">
          Watch on YouTube ↗
        </a>
      </div>
    </div>
  );
}
