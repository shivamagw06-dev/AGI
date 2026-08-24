import { BROADCASTS } from '@/lib/liveDeskConfig';
import LiveBroadcastPlayer from './LiveBroadcastPlayer';

/**
 * Global and India side by side, equal width and equal weight.
 *
 * Deliberately not tabs. The point of the desk is seeing both at once - a tab
 * makes one market a decision the reader has to keep making, and whichever tab
 * is not selected stops being situational awareness.
 *
 * The grid collapses to a stack below 1024px, where two 16:9 frames side by
 * side would each be too small to read.
 */
export default function DualBroadcastGrid({ minimizedId, onMinimize }) {
  return (
    <div className="ld-broadcasts">
      {BROADCASTS.map((broadcast) => (
        <LiveBroadcastPlayer
          key={broadcast.id}
          broadcast={broadcast}
          // Only one player may float at a time, so the other card keeps its
          // place rather than both leaving the layout.
          canMinimize={!minimizedId}
          onMinimize={onMinimize}
        />
      ))}
    </div>
  );
}
