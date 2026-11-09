// Media keys, headset buttons and the lock screen / OS media panel
// (Media Session API). Browsers show these controls while this tab is
// playing sound, i.e. when music plays in this browser (Phase 5).

import { useEffect, useRef } from "react";

import { usePlayback } from "./PlaybackProvider";

const SEEK_STEP_MS = 10_000;

export function MediaSession() {
  const playback = usePlayback();
  const latest = useRef(playback);
  latest.current = playback;

  const supported = typeof navigator !== "undefined" && "mediaSession" in navigator;
  const track = playback.playback?.track;
  const isPlaying = playback.playback?.is_playing ?? false;
  const serverProgress = playback.playback?.progress_ms;

  // What's playing
  useEffect(() => {
    if (!supported) return;
    if (!track) {
      navigator.mediaSession.metadata = null;
      return;
    }
    const artwork = [
      track.thumbnail_url && { src: track.thumbnail_url, sizes: "64x64" },
      track.artwork_url && { src: track.artwork_url, sizes: "640x640" },
    ].filter(Boolean) as MediaImage[];

    navigator.mediaSession.metadata = new MediaMetadata({
      title: track.title,
      artist: track.artist,
      album: track.album ?? "",
      artwork,
    });
  }, [supported, track?.uri, track?.title, track?.artist, track?.album, track?.artwork_url, track?.thumbnail_url]);

  // Playing or paused, and where in the song
  useEffect(() => {
    if (!supported) return;
    navigator.mediaSession.playbackState = track ? (isPlaying ? "playing" : "paused") : "none";

    if (!track?.duration_ms || serverProgress == null) return;
    try {
      navigator.mediaSession.setPositionState({
        duration: track.duration_ms / 1000,
        position: Math.min(serverProgress, track.duration_ms) / 1000,
        playbackRate: 1,
      });
    } catch {
      // Inconsistent values for a moment (e.g. song just changed)
    }
  }, [supported, track?.uri, track?.duration_ms, isPlaying, serverProgress]);

  // Buttons: set once, they always use the latest playback state
  useEffect(() => {
    if (!supported) return;
    const session = navigator.mediaSession;
    const seekBy = (deltaMs: number) => {
      const { progressMs, seek } = latest.current;
      seek(Math.max(0, progressMs + deltaMs));
    };
    const handlers: [MediaSessionAction, MediaSessionActionHandler][] = [
      ["play", () => latest.current.playback && !latest.current.playback.is_playing && latest.current.togglePlay()],
      ["pause", () => latest.current.playback?.is_playing && latest.current.togglePlay()],
      ["nexttrack", () => latest.current.run("next")],
      ["previoustrack", () => latest.current.run("previous")],
      ["seekto", (details) => details.seekTime != null && latest.current.seek(details.seekTime * 1000)],
      ["seekforward", (details) => seekBy((details.seekOffset ?? SEEK_STEP_MS / 1000) * 1000)],
      ["seekbackward", (details) => seekBy(-(details.seekOffset ?? SEEK_STEP_MS / 1000) * 1000)],
    ];
    for (const [action, handler] of handlers) {
      try {
        session.setActionHandler(action, handler);
      } catch {
        // This browser doesn't support that action
      }
    }
    return () => {
      for (const [action] of handlers) {
        try {
          session.setActionHandler(action, null);
        } catch {
          // ignore
        }
      }
    };
  }, [supported]);

  return null;
}
