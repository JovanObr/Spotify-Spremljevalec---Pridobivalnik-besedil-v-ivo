import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/client";
import type { NowPlayingResponse, Playback, PlayerAction, RepeatMode } from "../api/types";

// Spotify needs a moment before "currently playing" reflects a change
const REFRESH_DELAY_MS = 600;

export type PlayerCommand =
  | {
      action: PlayerAction;
      /** Current (locally estimated) position, so a pause freezes at the right spot. */
      progressMs: number;
    }
  | { action: "seek"; positionMs: number }
  | { action: "playContext"; contextUri: string; offsetUri?: string | null; deviceId?: string | null }
  | { action: "playTrack"; uri: string; deviceId?: string | null }
  | { action: "queue"; uri: string; title: string }
  | { action: "playTracks"; uris: string[]; offsetUri?: string | null; deviceId?: string | null }
  | { action: "shuffle"; state: boolean }
  | { action: "repeat"; mode: RepeatMode }
  | { action: "volume"; percent: number }
  | { action: "transfer"; deviceId: string; deviceName: string };

interface Callbacks {
  onError: (error: unknown, command: PlayerCommand) => void;
  onSuccess?: (command: PlayerCommand) => void;
}

export function usePlayerControls({ onError, onSuccess }: Callbacks) {
  const queryClient = useQueryClient();
  const key = ["now-playing"];

  return useMutation({
    mutationFn: (command: PlayerCommand) => {
      switch (command.action) {
        case "seek":
          return api.seek(command.positionMs);
        case "playContext":
          return api.playContext(command.contextUri, command.offsetUri, command.deviceId);
        case "playTrack":
          return api.playTrack(command.uri, command.deviceId);
        case "queue":
          return api.addToQueue(command.uri);
        case "playTracks":
          return api.playTracks(command.uris, command.offsetUri, command.deviceId);
        case "shuffle":
          return api.shuffle(command.state);
        case "repeat":
          return api.repeat(command.mode);
        case "volume":
          return api.volume(command.percent);
        case "transfer":
          return api.transfer(command.deviceId);
        default:
          return api.player(command.action);
      }
    },

    // Play/pause/seek show instantly; Spotify confirms on the next poll
    onMutate: async (command) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<NowPlayingResponse>(key);
      const playback = previous?.playback;

      if (playback) {
        const patch = optimisticPatch(command, playback);
        if (patch) {
          queryClient.setQueryData<NowPlayingResponse>(key, {
            ...previous,
            playback: { ...playback, ...patch },
          });
        }
      }

      return { previous };
    },

    onSuccess: (_data, command) => onSuccess?.(command),

    onError: (error, command, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
      onError(error, command);
    },

    onSettled: () => {
      window.setTimeout(
        () => queryClient.invalidateQueries({ queryKey: key }),
        REFRESH_DELAY_MS,
      );
    },
  });
}

/** What the screen should show right away, before Spotify confirms. */
function optimisticPatch(command: PlayerCommand, _playback: Playback): Partial<Playback> | null {
  switch (command.action) {
    case "seek":
      return { progress_ms: Math.round(command.positionMs) };
    case "play":
    case "pause":
      return { is_playing: command.action === "play", progress_ms: Math.round(command.progressMs) };
    // Shuffle, repeat and volume aren't patched here: PlaybackProvider holds
    // them on screen until Spotify's own state confirms the change. Patching
    // this cache would make it look confirmed before Spotify applied it.
    default:
      return null;
  }
}
