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
  /** MusicAtlas or the AI is configured. */
  recommendations_enabled: boolean;
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

// Phase 6 (api/routes/lyrics.py)

/** One entry per displayed lyric line, "" where there's nothing to show. */
export interface TranslationResponse {
  language: string;
  lines: string[];
}

export interface MeaningResponse {
  summary: string;
  themes: string[];
  based_on_lyrics: boolean;
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
  /** One sentence on why it fits (may be missing). */
  reason: string | null;
}

export interface RecommendationsResponse {
  items: Recommendation[];
  /** Who picked the songs. */
  source: "musicatlas" | "ai";
  /** MusicAtlas style tags for the current song, e.g. "dreampop". */
  tags: string[];
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

// Song details (Wikipedia, scraped) and the artist's country (SOAP)

export interface InfoField {
  label: string;
  values: string[];
}

export interface WikiSong {
  title: string;
  url: string;
  album: string | null;
  fields: InfoField[];
  artist_url: string | null;
}

export interface WikiArtist {
  name: string;
  url: string;
  summary: string | null;
  origin: string | null;
  fields: InfoField[];
}

export interface CountryInfo {
  iso_code: string;
  name: string;
  capital: string | null;
  phone_code: string | null;
  continent: string | null;
  currency: string | null;
  flag_url: string | null;
  languages: string[];
}

export interface DetailsResponse {
  song: WikiSong | null;
  artist: WikiArtist | null;
  country: CountryInfo | null;
  errors: Record<string, string>;
}

// Music in Slovenia (SiStat, PC-Axis)

export interface StatsResponse {
  title: string;
  contents: string | null;
  units: string | null;
  source: string | null;
  last_updated: string | null;
  notes: string[];
  table: string;
  table_url: string;
  time_dimension: string | null;
  dimensions: { name: string; values: string[] }[];
  /** Each cell: [index in dimension 1, index in dimension 2, ..., value]. */
  observations: (number | null)[][];
  fetched_at: number;
  stale: boolean;
  error?: string;
}

// Data sources page

export interface SourceStatus {
  id: string;
  name: string;
  technology: string;
  format: string;
  provides: string;
  refresh: string;
  url: string;
  refreshable: boolean;
  state: "ok" | "error" | "unused";
  last_success: number | null;
  last_failure: number | null;
  last_error: string | null;
  requests_this_run: number;
}

export interface SourcesResponse {
  sources: SourceStatus[];
  delivery: { id: string; name: string; technology: string; description: string }[];
}
