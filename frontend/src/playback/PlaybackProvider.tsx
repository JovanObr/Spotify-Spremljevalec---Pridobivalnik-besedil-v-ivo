// One place that knows what's playing. Every view, the mini player and the
// keyboard shortcut read playback state and send commands through here.

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import type { Playback, PlayerAction, RepeatMode, Track } from "../api/types";
import { useNowPlaying } from "../hooks/queries";
import { useArtworkPalette } from "../hooks/useArtworkPalette";
import { usePlaybackClock } from "../hooks/usePlaybackClock";
import { usePlayerControls } from "../hooks/usePlayerControls";
import { strings } from "../lib/strings";

const NOTICE_MS = 4500;

interface PlaybackContextValue {
  playback: Playback | null;
  /** Position in the current track, advanced locally between polls. */
  progressMs: number;
  /** True until the first now-playing response arrives. */
  isLoading: boolean;
  /** A message for the user (Spotify errors, failed commands), or null. */
  notice: string | null;
  isBusy: boolean;
  run: (action: PlayerAction) => void;
  togglePlay: () => void;
  seek: (positionMs: number) => void;
  /** Start a playlist/album, optionally from a given track URI. */
  playContext: (contextUri: string, offsetUri?: string | null) => void;
  /** Play one song now (on its own; prefer playSong). */
  playTrack: (uri: string) => void;
  /**
   * Play a song from a search result, the queue or a recommendation: it
   * starts inside its album, so Spotify continues with the rest of the
   * album (and its autoplay) and shuffle/repeat behave as expected.
   */
  playSong: (track: Track) => void;
  /** Add a song to the end of the Spotify queue. */
  addToQueue: (uri: string, title: string) => void;
  /** Play a list of songs (e.g. liked songs), optionally from one of them. */
  playTracks: (uris: string[], offsetUri?: string | null) => void;
  toggleShuffle: () => void;
  /** off -> context (repeat all) -> track (repeat one) -> off */
  cycleRepeat: () => void;
  setVolume: (percent: number) => void;
  transferTo: (deviceId: string, deviceName: string) => void;
  /** Show a short message (e.g. after liking a song). */
  notify: (message: string) => void;
}

// After changing shuffle/repeat/volume, keep showing the new value for this
// long even if Spotify still reports the old one (it applies changes with a
// delay). Otherwise the button flips back, and clicking again undoes it.
const HOLD_MS = 5000;

interface Held<T> {
  value: T;
  until: number;
}

interface HeldSettings {
  shuffle?: Held<boolean>;
  repeat?: Held<RepeatMode>;
  volume?: Held<number>;
}

/** Apply held values; forget each one once Spotify agrees or time runs out. */
function withHeldSettings(playback: Playback | null, held: HeldSettings): Playback | null {
  if (!playback) return playback;
  const now = Date.now();
  let result = playback;

  if (held.shuffle) {
    if (now > held.shuffle.until || playback.shuffle === held.shuffle.value) delete held.shuffle;
    else result = { ...result, shuffle: held.shuffle.value };
  }
  if (held.repeat) {
    if (now > held.repeat.until || playback.repeat === held.repeat.value) delete held.repeat;
    else result = { ...result, repeat: held.repeat.value };
  }
  if (held.volume && playback.device) {
    if (now > held.volume.until || playback.device.volume_percent === held.volume.value) {
      delete held.volume;
    } else {
      result = { ...result, device: { ...playback.device, volume_percent: held.volume.value } };
    }
  }
  return result;
}

const NEXT_REPEAT: Record<RepeatMode, RepeatMode> = {
  off: "context",
  context: "track",
  track: "off",
};

const PlaybackContext = createContext<PlaybackContextValue | null>(null);

function spotifyNotice(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  if (error.status === 429) return strings.spotifyError.rateLimited;
  if (error.status === 403) return strings.spotifyError.forbidden;
  if (error.status === 401) return null; // handled by sending the user to log in
  return error.message;
}

export function PlaybackProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data, error, dataUpdatedAt, isPending } = useNowPlaying(true);

  const held = useRef<HeldSettings>({});
  const hold = <K extends keyof HeldSettings>(key: K, value: NonNullable<HeldSettings[K]>["value"]) => {
    held.current[key] = { value, until: Date.now() + HOLD_MS } as HeldSettings[K];
  };

  const playback = withHeldSettings(data?.playback ?? null, held.current);
  const progressMs = usePlaybackClock(playback, dataUpdatedAt);
  useArtworkPalette(playback?.track.artwork_url);

  // Session expired: re-check status, which shows the connect screen
  const sessionExpired = error instanceof ApiError && error.status === 401;
  useEffect(() => {
    if (sessionExpired) queryClient.invalidateQueries({ queryKey: ["status"] });
  }, [sessionExpired, queryClient]);

  // Messages from failed commands disappear after a moment
  const [commandNotice, setCommandNotice] = useState<string | null>(null);
  useEffect(() => {
    if (!commandNotice) return;
    const timer = window.setTimeout(() => setCommandNotice(null), NOTICE_MS);
    return () => window.clearTimeout(timer);
  }, [commandNotice]);

  const controls = usePlayerControls({
    onError: (commandError, command) => {
      // Spotify refused: stop showing the value we were holding
      if (command.action === "shuffle" || command.action === "repeat" || command.action === "volume") {
        delete held.current[command.action];
      }
      setCommandNotice(
        commandError instanceof ApiError && commandError.status > 0
          ? commandError.message
          : strings.playback.controlFailed,
      );
    },
    onSuccess: (command) => {
      if (command.action === "queue") {
        setCommandNotice(strings.playback.queued(command.title));
        queryClient.invalidateQueries({ queryKey: ["queue"] });
      }
      if (command.action === "transfer") {
        setCommandNotice(strings.devices.switched(command.deviceName));
        queryClient.invalidateQueries({ queryKey: ["devices"] });
      }
    },
  });

  const value: PlaybackContextValue = {
    playback,
    progressMs,
    isLoading: isPending,
    notice: commandNotice ?? spotifyNotice(error),
    isBusy: controls.isPending,
    run: (action) => controls.mutate({ action, progressMs }),
    togglePlay: () =>
      controls.mutate({ action: playback?.is_playing ? "pause" : "play", progressMs }),
    seek: (positionMs) => controls.mutate({ action: "seek", positionMs }),
    playContext: (contextUri, offsetUri) =>
      controls.mutate({ action: "playContext", contextUri, offsetUri }),
    playTrack: (uri) => controls.mutate({ action: "playTrack", uri }),
    playSong: (track) => {
      if (!track.uri) return;
      if (track.album_uri) {
        controls.mutate({ action: "playContext", contextUri: track.album_uri, offsetUri: track.uri });
      } else {
        controls.mutate({ action: "playTrack", uri: track.uri });
      }
    },
    addToQueue: (uri, title) => controls.mutate({ action: "queue", uri, title }),
    playTracks: (uris, offsetUri) => controls.mutate({ action: "playTracks", uris, offsetUri }),
    toggleShuffle: () => {
      const next = !playback?.shuffle;
      hold("shuffle", next);
      controls.mutate({ action: "shuffle", state: next });
    },
    cycleRepeat: () => {
      const next = NEXT_REPEAT[playback?.repeat ?? "off"];
      hold("repeat", next);
      controls.mutate({ action: "repeat", mode: next });
    },
    setVolume: (percent) => {
      hold("volume", Math.round(percent));
      controls.mutate({ action: "volume", percent });
    },
    transferTo: (deviceId, deviceName) =>
      controls.mutate({ action: "transfer", deviceId, deviceName }),
    notify: setCommandNotice,
  };

  // Space toggles play/pause anywhere, unless focus is on something that uses Space
  const latest = useRef(value);
  latest.current = value;
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.code !== "Space" || event.repeat || !latest.current.playback) return;
      const target = event.target as HTMLElement;
      if (target.closest("button, a, input, textarea, select, [contenteditable]")) return;
      event.preventDefault();
      latest.current.togglePlay();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return <PlaybackContext.Provider value={value}>{children}</PlaybackContext.Provider>;
}

export function usePlayback(): PlaybackContextValue {
  const context = useContext(PlaybackContext);
  if (!context) throw new Error("usePlayback must be used inside <PlaybackProvider>");
  return context;
}
