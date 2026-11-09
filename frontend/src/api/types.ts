// Shapes returned by the Python API (api/app.py). Keep in sync with
// models/track.py and services/lyrics_service.py.

export interface Track {
  id: string | null;
  title: string;
  artist: string;
  artists: string[];
  album: string;
  duration_ms: number | null;
  artwork_url: string | null;
  spotify_url: string | null;
  uri: string | null;
  thumbnail_url: string | null;
  is_local: boolean;
  is_playable: boolean;
  /** The song's album; single songs are played "in their album". */
  album_uri: string | null;
}

export type RepeatMode = "off" | "context" | "track";

export interface Device {
  id: string | null;
  name: string;
  /** "Computer", "Smartphone", "Speaker", … */
  type: string;
  is_active: boolean;
  volume_percent: number | null;
  supports_volume: boolean;
}

export interface Playback {
  track: Track;
  is_playing: boolean;
  progress_ms: number | null;
  /** What it's playing from, e.g. "spotify:playlist:…" */
  context_uri: string | null;
  shuffle: boolean;
  repeat: RepeatMode;
  device: Device | null;
}

export interface NowPlayingResponse {
  playback: Playback | null;
  server_time_ms: number;
}

export interface StatusResponse {
  authenticated: boolean;
  ai_enabled: boolean;
}

export interface LyricLine {
  time_ms: number;
  text: string;
}

export interface Lyrics {
  track_name: string;
  artist_name: string;
  album_name: string | null;
  instrumental: boolean;
  plain_lyrics: string | null;
  lines: LyricLine[];
  source: string;
}

export interface LyricsResponse {
  found: boolean;
  lyrics: Lyrics | null;
}

export interface FactsResponse {
  facts: string[];
}

export type PlayerAction = "play" | "pause" | "next" | "previous";

// Playlists (api/routes/library.py, models/playlist.py)

export interface PlaylistSummary {
  id: string;
  uri: string;
  name: string;
  description: string | null;
  image_url: string | null;
  owner_name: string;
  /** Owned or collaborative: Spotify shares the track list. */
  is_owned: boolean;
  track_count: number | null;
}

export interface PlaylistDetail extends PlaylistSummary {
  snapshot_id: string | null;
  items_available: boolean;
}

export interface PlaylistItem {
  position: number;
  added_at: string | null;
  track: Track;
}

export interface PlaylistItemsPage {
  items: PlaylistItem[];
  total: number;
  next_offset: number | null;
}

// Recommendations (api/routes/ai.py, services/recommendation_service.py)

export interface Recommendation {
  track: Track;
  /** One sentence from the AI on why it fits. */
  reason: string;
}

// Phase 4: queue, search

export interface QueueResponse {
  current: Track | null;
  next: Track[];
}

export interface AlbumResult {
  id: string;
  uri: string;
  name: string;
  artist: string;
  image_url: string | null;
  year: string | null;
}

export interface ArtistResult {
  id: string;
  uri: string;
  name: string;
  image_url: string | null;
}

export interface SearchResults {
  tracks: Track[];
  artists: ArtistResult[];
  albums: AlbumResult[];
  playlists: PlaylistSummary[];
}
