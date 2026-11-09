import { useEffect, useState } from "react";

import type { Playback } from "../api/types";

const TICK_MS = 100;

/**
 * Spotify is polled every few seconds, but lyrics need to move smoothly.
 * Between polls, this hook advances the playback position locally from the
 * moment the last response arrived.
 */
export function usePlaybackClock(
  playback: Playback | null | undefined,
  receivedAt: number,
): number {
  const [now, setNow] = useState(() => Date.now());
  const isPlaying = Boolean(playback?.is_playing);

  useEffect(() => {
    setNow(Date.now());
    if (!isPlaying) return;

    const timer = window.setInterval(() => setNow(Date.now()), TICK_MS);
    return () => window.clearInterval(timer);
  }, [isPlaying, receivedAt]);

  if (!playback || playback.progress_ms == null) return 0;

  const elapsed = isPlaying ? Math.max(0, now - receivedAt) : 0;
  const position = playback.progress_ms + elapsed;
  const duration = playback.track.duration_ms;

  return duration ? Math.min(position, duration) : position;
}
