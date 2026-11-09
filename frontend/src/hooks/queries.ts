import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { ApiError, api } from "../api/client";
import type { Track } from "../api/types";
import { FACTS_LANGUAGE } from "../lib/strings";

const POLL_PLAYING_MS = 3000;
const POLL_IDLE_MS = 8000;
const POLL_SERVER_DOWN_MS = 4000;

function retryAfterMs(error: unknown, fallback: number) {
  return error instanceof ApiError && error.retryAfterSeconds
    ? error.retryAfterSeconds * 1000
    : fallback;
}

/** Errors that retrying will not fix. */
function isPermanent(error: unknown) {
  return error instanceof ApiError && [401, 403, 422, 503].includes(error.status);
}

export function useStatus() {
  return useQuery({
    queryKey: ["status"],
    queryFn: api.status,
    retry: false,
    // Keep checking while the server is down, so the page recovers itself
    refetchInterval: (query) => (query.state.error ? POLL_SERVER_DOWN_MS : false),
  });
}

export function useNowPlaying(enabled: boolean) {
  return useQuery({
    queryKey: ["now-playing"],
    queryFn: api.nowPlaying,
    enabled,
    retry: false,
    refetchIntervalInBackground: true,
    refetchInterval: (query) => {
      const { error, data } = query.state;
      if (error) {
        if (isPermanent(error)) return false;
        return retryAfterMs(error, POLL_IDLE_MS);
      }
      return data?.playback ? POLL_PLAYING_MS : POLL_IDLE_MS;
    },
  });
}

export function useLyrics(track: Track | undefined) {
  return useQuery({
    queryKey: ["lyrics", track?.id, track?.title, track?.artist],
    queryFn: () => api.lyrics(track!),
    enabled: Boolean(track),
    staleTime: Infinity, // lyrics for a track never change
    retry: (count, error) => !isPermanent(error) && count < 2,
    retryDelay: (_, error) => retryAfterMs(error, 5000),
  });
}

export function useFacts(track: Track | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["facts", track?.id, track?.title, FACTS_LANGUAGE],
    queryFn: () => api.facts(track!, FACTS_LANGUAGE),
    enabled: enabled && Boolean(track),
    staleTime: Infinity,
    retry: false, // each retry costs AI quota; the user can retry manually
  });
}

export function usePlaylists() {
  return useQuery({
    queryKey: ["playlists"],
    queryFn: api.playlists,
    select: (data) => data.items,
    staleTime: 60_000,
    retry: (count, error) => !isPermanent(error) && count < 2,
  });
}

export function usePlaylist(id: string) {
  return useQuery({
    queryKey: ["playlist", id],
    queryFn: () => api.playlist(id),
    staleTime: 60_000,
    retry: (count, error) =>
      !isPermanent(error) && !(error instanceof ApiError && error.status === 404) && count < 2,
  });
}

/** A playlist's tracks, 50 at a time. Keyed by snapshot so edits refresh it. */
export function usePlaylistItems(id: string, snapshotId: string | null | undefined, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: ["playlist-items", id, snapshotId],
    queryFn: ({ pageParam }) => api.playlistItems(id, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.next_offset ?? undefined,
    enabled,
    staleTime: 5 * 60_000,
    retry: (count, error) => !isPermanent(error) && count < 2,
  });
}

export function useRecommendations(track: Track | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["recommendations", track?.uri ?? `${track?.artist}|${track?.title}`],
    queryFn: () => api.recommendations(track!),
    select: (data) => data.items,
    enabled: enabled && Boolean(track),
    staleTime: Infinity,
    retry: false, // each retry costs AI quota; the user can retry manually
  });
}

// Phase 4

/** The queue; refreshed whenever the current song changes. */
export function useQueue(currentUri: string | null | undefined) {
  return useQuery({
    queryKey: ["queue", currentUri],
    queryFn: api.queue,
    staleTime: 10_000,
    retry: (count, error) => !isPermanent(error) && count < 1,
  });
}

export function useDevices(enabled: boolean) {
  return useQuery({
    queryKey: ["devices"],
    queryFn: api.devices,
    select: (data) => data.items,
    enabled,
    staleTime: 0,
    retry: false,
  });
}

export function useLikedTracks() {
  return useInfiniteQuery({
    queryKey: ["liked-tracks"],
    queryFn: ({ pageParam }) => api.likedTracks(pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.next_offset ?? undefined,
    staleTime: 30_000,
    retry: (count, error) => !isPermanent(error) && count < 2,
  });
}

/** Whether one song is liked. */
export function useIsLiked(uri: string | null | undefined) {
  return useQuery({
    queryKey: ["liked", uri],
    queryFn: async () => (await api.likedContains([uri!]))[uri!] ?? false,
    enabled: Boolean(uri),
    staleTime: 60_000,
    retry: false,
  });
}

export function useSearch(query: string) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: ["search", trimmed.toLowerCase()],
    queryFn: () => api.search(trimmed),
    enabled: trimmed.length > 0,
    staleTime: 60_000,
    placeholderData: (previous) => previous, // keep old results while typing
    retry: (count, error) => !isPermanent(error) && count < 1,
  });
}
