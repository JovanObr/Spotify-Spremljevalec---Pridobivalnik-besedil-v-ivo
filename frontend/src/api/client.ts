import type {
  FactsResponse,
  LyricsResponse,
  MeaningResponse,
  TranslationResponse,
  NowPlayingResponse,
  Device,
  PlayerAction,
  QueueResponse,
  RepeatMode,
  SearchResults,
  PlaylistDetail,
  PlaylistItemsPage,
  PlaylistSummary,
  RecommendationsResponse,
  StatusResponse,
  Track,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public retryAfterSeconds: number | null = null,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError("server_unreachable", 0);
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      // Not JSON (e.g. proxy error page)
    }
    const retryAfter = Number(response.headers.get("Retry-After"));
    throw new ApiError(
      String(detail),
      response.status,
      Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
    );
  }

  return response.json() as Promise<T>;
}

function trackQuery(track: Track, extra: Record<string, string> = {}) {
  const params = new URLSearchParams({
    artist: track.artists[0] ?? track.artist,
    title: track.title,
    ...extra,
  });
  if (track.album) params.set("album", track.album);
  return params;
}

function post<T>(path: string, body: unknown, method = "POST") {
  return request<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  status: () => request<StatusResponse>("/api/status"),

  nowPlaying: () => request<NowPlayingResponse>("/api/now-playing"),

  lyrics: (track: Track) => {
    const params = trackQuery(track);
    if (track.duration_ms) params.set("duration_ms", String(track.duration_ms));
    return request<LyricsResponse>(`/api/lyrics?${params}`);
  },

  translation: (track: Track, language: string) => {
    const params = trackQuery(track, { language });
    if (track.duration_ms) params.set("duration_ms", String(track.duration_ms));
    return request<TranslationResponse>(`/api/lyrics/translation?${params}`);
  },

  meaning: (track: Track, language: string) => {
    const params = trackQuery(track, { language });
    if (track.duration_ms) params.set("duration_ms", String(track.duration_ms));
    return request<MeaningResponse>(`/api/meaning?${params}`);
  },

  facts: (track: Track, language: string) =>
    request<FactsResponse>(`/api/facts?${trackQuery(track, { language })}`),

  player: (action: PlayerAction) =>
    request<{ ok: boolean }>(`/api/player/${action}`, { method: "POST" }),

  /** Start a playlist or album, optionally from a specific track. */
  /** deviceId: where to play when nothing is active (e.g. this browser). */
  playContext: (contextUri: string, offsetUri?: string | null, deviceId?: string | null) =>
    post<{ ok: boolean }>("/api/player/play", {
      context_uri: contextUri,
      offset_uri: offsetUri ?? null,
      device_id: deviceId ?? null,
    }),

  /** Play one song now. */
  playTrack: (trackUri: string, deviceId?: string | null) =>
    post<{ ok: boolean }>("/api/player/play", { track_uri: trackUri, device_id: deviceId ?? null }),

  /** Short-lived token for the Web Playback SDK (playing in this browser). */
  token: () => request<{ access_token: string; expires_at: number | null }>("/api/token"),

  addToQueue: (trackUri: string) =>
    request<{ ok: boolean }>("/api/player/queue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uri: trackUri }),
    }),

  recommendations: (track: Track) => {
    const params = trackQuery(track);
    if (track.uri) params.set("track_uri", track.uri);
    return request<RecommendationsResponse>(`/api/recommendations?${params}`);
  },

  /** Play a list of songs (max 100), optionally starting at one. */
  playTracks: (trackUris: string[], offsetUri?: string | null, deviceId?: string | null) =>
    post<{ ok: boolean }>("/api/player/play", {
      track_uris: trackUris.slice(0, 100),
      offset_uri: offsetUri ?? null,
      device_id: deviceId ?? null,
    }),

  queue: () => request<QueueResponse>("/api/queue"),

  devices: () => request<{ items: Device[] }>("/api/devices"),

  transfer: (deviceId: string) =>
    post<{ ok: boolean }>("/api/player/transfer", { device_id: deviceId, play: true }),

  shuffle: (state: boolean) => post<{ ok: boolean }>("/api/player/shuffle", { state }),

  repeat: (mode: RepeatMode) => post<{ ok: boolean }>("/api/player/repeat", { mode }),

  volume: (percent: number) =>
    post<{ ok: boolean }>("/api/player/volume", { percent: Math.round(percent) }),

  likedTracks: (offset: number) =>
    request<PlaylistItemsPage>(`/api/library/tracks?offset=${offset}`),

  likedContains: (uris: string[]) =>
    request<Record<string, boolean>>(
      `/api/library/contains?uris=${encodeURIComponent(uris.join(","))}`,
    ),

  setLiked: (uris: string[], liked: boolean) =>
    post<{ liked: boolean }>("/api/library/tracks", { uris }, liked ? "PUT" : "DELETE"),

  search: (query: string) =>
    request<SearchResults>(`/api/search?q=${encodeURIComponent(query)}`),

  playlists: () => request<{ items: PlaylistSummary[] }>("/api/playlists"),

  playlist: (id: string) =>
    request<PlaylistDetail>(`/api/playlists/${encodeURIComponent(id)}`),

  playlistItems: (id: string, offset: number) =>
    request<PlaylistItemsPage>(
      `/api/playlists/${encodeURIComponent(id)}/items?offset=${offset}`,
    ),

  seek: (positionMs: number) =>
    request<{ ok: boolean }>("/api/player/seek", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position_ms: Math.max(0, Math.round(positionMs)) }),
    }),

  logout: () =>
    request<{ authenticated: boolean }>("/api/logout", { method: "POST" }),

  /** Full-page navigation to Spotify's login; returns here afterwards. */
  loginUrl: () =>
    `/login?next=${encodeURIComponent(window.location.origin + "/")}`,
};
