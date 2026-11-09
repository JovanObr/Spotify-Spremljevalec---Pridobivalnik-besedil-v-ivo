# Spotify Sound Companion

A companion app for Spotify that follows what you're playing and shows **live, time-synced lyrics** together with **AI-generated facts** about the song.

It integrates three external services:

| Service | Used for |
| --- | --- |
| Spotify Web API (OAuth 2.0) | The currently playing track, playback state and progress |
| LRCLIB | Synced (LRC) and plain lyrics |
| lyrics.ovh | Backup source for plain lyrics when LRCLIB has none |
| Google Gemini (AI Studio) | Short facts about the song and artist, and song recommendations |

There are two ways to use it:

- **Web app** (main interface): a React frontend served by a FastAPI backend.
- **Terminal app**: `python main.py`, a simple text monitor.

## Features

- Spotify login with OAuth 2.0 (shared token cache for the web and terminal apps).
- Current track: title, artists, album, artwork, progress and duration.
- Live synced lyrics that highlight and auto-scroll with the song, falling back to plain lyrics when no synced version exists.
- Play, pause, next and previous controls (Space toggles play/pause). Requires Spotify Premium.
- **Play in the browser:** the tab registers itself as a Spotify device called "Sound Companion" (Spotify Web Playback SDK), so no other Spotify app has to be open. When nothing is playing anywhere, whatever you start here plays in the browser. Needs Premium and a desktop browser with DRM support.
- **Media keys and lock screen:** keyboard media keys, headset buttons and the Windows / macOS / phone media panel show the current song and control it (Media Session API).
- Seek by dragging the progress bar, or click any lyric line to jump to it.
- Navigation between Now Playing, Search and Library, with a mini player on every other view.
- **Search** for songs, artists, albums and playlists. A song picked from search, Up next or recommendations plays inside its album, so the rest of the album (and Spotify's autoplay) follows.
- **Up next:** see your queue, and add any song to it from any list.
- **Liked Songs:** like or unlike the current song with the heart, and play from your Liked Songs.
- **Devices, shuffle, repeat and volume:** choose which Spotify app or speaker plays, and control playback modes.
- **Playlists:** your own and followed playlists in a library grid; open one to see its songs and start it from any song. Followed playlists can be played as a whole (Spotify doesn't share their track lists with apps like this).
- Lyrics from several sources: LRCLIB is searched in up to five ways, from an exact match to a free-text search that tolerates different artist spellings and titles like "Song - Remastered 2011". Synced lyrics are preferred; lyrics.ovh is the backup for plain lyrics. If nothing is found, a link searches Genius.
- Up to three AI-generated facts per song, using Gemini structured (JSON) output and Google's low-latency Flash-Lite model.
- **Smart recommendations:** three songs you'll probably like if you like the current one. With a MusicAtlas key they're picked by audio similarity (with the song's style tags), and Gemma writes a one-line reason for each. Without it, or when a song isn't in MusicAtlas, Gemma 4 suggests them and each is checked against Spotify search so made-up songs never appear. Play any of them now or add it to your queue.
- **Lyrics translation:** one click shows an AI translation under every lyric line, in the language you pick (remembered in this browser). Repeated lines are translated once.
- **What's this song about:** on request, a short AI explanation of the song's meaning based on its lyrics, with a few themes.
- Prefetching: when a song starts, the lyrics, facts and recommendations for the next song in your Spotify queue are prepared in the background, so they appear instantly when it plays.
- The page takes its colours from the current album cover.
- In-memory caching: lyrics and AI facts are fetched once per track, even when several requests for the same song arrive at once.
- Handling of rate limits (Spotify, LRCLIB, Gemini), expired logins, missing playback and podcasts.
- Automated tests for the services, the playback monitor and the web API.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer (for the frontend)
- A Spotify account and a Spotify Developer application in Development Mode
- Optional: a Google AI Studio API key for the AI facts

## Setup

### 1. Python environment

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

### 2. Spotify application

1. Go to https://developer.spotify.com/dashboard and create an app (API: Web API).
2. Set the redirect URI to `http://127.0.0.1:8888/callback`.
3. Under **User Management**, add the Spotify account you will log in with.

### 3. Gemini API key (optional)

Create a key at https://aistudio.google.com/apikey. Without a key the app still works; the "About this song" panel just explains how to enable it.

### 4. MusicAtlas API key (optional)

Create a free key at https://musicatlas.ai/developer (100 requests per day). Without it, recommendations come from Gemma alone.

### 5. Environment variables

Copy `.env.example` to `.env` and fill it in:

```env
SPOTIPY_CLIENT_ID="your_client_id"
SPOTIPY_CLIENT_SECRET="your_client_secret"
SPOTIPY_REDIRECT_URI="http://127.0.0.1:8888/callback"

GEMINI_API_KEY="your_gemini_key"
GEMINI_RECOMMENDATIONS_MODEL="gemma-4-31b-it"
GEMINI_FACTS_MODEL="gemini-3.5-flash-lite"

MUSICATLAS_API_KEY="your_musicatlas_key"
```

**Never commit `.env` or share your secrets.**

### 6. Frontend dependencies

```bash
cd frontend
npm install
```

## Running

### Web app (development)

Use two terminals:

```bash
# Terminal 1: Python API on http://127.0.0.1:8888
python -m api

# Terminal 2: frontend with hot reload on http://127.0.0.1:5173
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173** and click **Connect Spotify**. If you logged in with an older version, you'll be asked to connect once more: the app now requests every permission the planned features need (see `SPOTIFY_SCOPES` in `services/spotify_service.py`), so future updates won't need another login. Use `127.0.0.1`, not `localhost`, so it matches the Spotify redirect URI.

To restart the API automatically when Python files change: `$env:API_RELOAD="1"; python -m api` (PowerShell).

### Web app (production build)

```bash
cd frontend
npm run build
cd ..
python -m api
```

The API now also serves the built frontend, so everything runs on **http://127.0.0.1:8888**.

### Terminal app

```bash
python main.py
```

Press `Ctrl+C` to stop.

## API endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/status` | Whether Spotify is connected and AI / recommendations are configured |
| GET | `/api/token` | Short-lived access token for the Web Playback SDK (local only, not cached) |
| GET | `/login` | Redirects to Spotify login |
| GET | `/callback` | Spotify OAuth redirect target |
| POST | `/api/logout` | Removes the stored Spotify token |
| GET | `/api/now-playing` | Current track and playback state |
| POST | `/api/player/{play\|pause\|next\|previous}` | Controls playback on the active Spotify device. `play` also accepts `{"context_uri", "offset_uri"}` to start a playlist from a given song, `{"track_uri"}` to play one song or `{"track_uris"}` for a list, plus an optional `"device_id"` to choose where |
| POST | `/api/player/seek` | Jumps to `{"position_ms": ...}` in the current track |
| POST | `/api/player/queue` | Adds `{"uri": "spotify:track:…"}` to your queue |
| GET | `/api/queue` | The current song and the next 20 in your queue |
| GET | `/api/devices` | Spotify apps and speakers you can play on |
| POST | `/api/player/transfer` | Moves playback to `{"device_id"}` |
| POST | `/api/player/shuffle`, `/repeat`, `/volume` | `{"state": true}`, `{"mode": "off\|context\|track"}`, `{"percent": 0-100}` |
| GET | `/api/search?q=` | Songs, artists, albums and playlists (10 of each) |
| GET | `/api/library/tracks?offset=` | Your liked songs, 50 at a time |
| GET | `/api/library/contains?uris=` | Which songs are liked |
| PUT / DELETE | `/api/library/tracks` | Like / unlike `{"uris": [...]}` |
| GET | `/api/recommendations?artist=&title=&album=&track_uri=` | Three songs you might like: `{items, source: "musicatlas"\|"ai", tags}` |
| GET | `/api/playlists` | Every playlist in your library |
| GET | `/api/playlists/{id}` | One playlist's details (`items_available` says whether its songs can be listed) |
| GET | `/api/playlists/{id}/items?offset=` | 50 songs at a time |
| GET | `/api/lyrics?artist=&title=&album=&duration_ms=` | Lyrics with parsed synced lines |
| GET | `/api/facts?artist=&title=&album=&language=` | AI-generated facts |
| GET | `/api/lyrics/translation?artist=&title=&language=&album=&duration_ms=` | The lyrics translated line by line (one entry per displayed line) |
| GET | `/api/meaning?artist=&title=&album=&duration_ms=&language=` | What the song is about: `{summary, themes, based_on_lyrics}` |

Interactive documentation is available at http://127.0.0.1:8888/docs while the API runs.

## Running tests

```bash
python -m unittest discover -s tests -v
```

```bash
cd frontend
npm run typecheck
```

## Project structure

```text
├── main.py                  Terminal app
├── requirements.txt
├── .env.example
│
├── api/
│   ├── __main__.py          Starts the web server (python -m api)
│   ├── app.py               Creates the app, includes routers, serves the frontend
│   ├── state.py             Shared Spotify client and login state (a FastAPI dependency)
│   ├── errors.py            Spotify errors -> HTTP errors
│   └── routes/              One router per feature: auth, player, library, search, lyrics, ai
│
├── core/
│   └── config.py            Environment variables and paths
│
├── models/
│   ├── track.py             Track and Playback models (normalized Spotify data)
│   └── playlist.py          Playlist models (handle old and new Spotify field names)
│
├── services/
│   ├── spotify_service.py   Spotify client and authentication
│   ├── library_service.py   Playlists, their songs and liked songs, with short-lived caching
│   ├── search_service.py    Spotify search, normalized
│   ├── lyrics_service.py    Lyrics sources (LRCLIB, lyrics.ovh), LRC parsing, caching
│   ├── ai_service.py        Gemini/Gemma: facts, suggestions, reasons, translation, meaning
│   ├── musicatlas_service.py  MusicAtlas similar-tracks client (audio-based)
│   ├── recommendation_service.py  MusicAtlas picks, or AI suggestions verified with Spotify search
│   └── prefetch_service.py  Prepares lyrics, facts and recommendations for the current and next song
│
├── utils/
│   ├── display.py           Terminal output
│   ├── spotify_errors.py    Spotify error handling for the terminal app
│   ├── cache.py             Small in-memory cache with expiry
│   ├── single_flight.py     Makes simultaneous requests for the same song share one lookup
│   └── text.py              Loose title/artist matching (accents, "The", punctuation)
│
├── tests/
│
├── docs/
│   └── ROADMAP.md           Planned features and how they'll be built
│
└── frontend/                React + TypeScript + Vite + Tailwind CSS
    └── src/
        ├── App.tsx          Login gate and routes
        ├── views/           One file per page (Now Playing, Search, Up next, Library, Liked Songs, Playlist)
        ├── playback/        PlaybackProvider (shared state and commands), WebPlayerProvider
        │                    (this tab as a Spotify device), MediaSession (media keys)
        ├── components/      UI components; layout/ = app shell and mini player, library/ = playlist cards and track rows
        ├── api/             Typed API client and response types
        ├── hooks/           Data fetching (TanStack Query), playback clock, colours
        └── lib/             Text strings, formatting, album-colour extraction
```

### Extending the frontend

- **Text and translations:** all user-facing text is in `frontend/src/lib/strings.ts`. `FACTS_LANGUAGE` there sets the language of the AI facts (e.g. `"Slovenian"`).
- **New page:** create it in `src/views/`, add a `<Route>` in `App.tsx`, and add it to `NAV_ITEMS` in `components/layout/AppShell.tsx` to show it in the navigation.
- **Playback anywhere:** call `usePlayback()` for the current track, position and commands (`run`, `togglePlay`, `seek`).
- **New API area:** add a router in `api/routes/` and include it in `api/app.py`.
- **New data from the API:** add the response type to `src/api/types.ts`, a function to `src/api/client.ts` and a hook to `src/hooks/queries.ts`.
- **Colours and fonts:** design tokens are in `src/index.css` (`@theme`).

## Roadmap

The goal is a focused replacement for the Spotify app: the features you use every day, without the clutter, plus AI where Spotify offers nothing. The full plan, including the Spotify API restrictions that shape it, is in [docs/ROADMAP.md](docs/ROADMAP.md).

| Phase | Feature | Status |
| --- | --- | --- |
| 1 | App shell: navigation (Now Playing, Library), mini player, seek, click a lyric line to jump to it | Done |
| 2 | **Playlists**: browse your playlists, open them and play from any song | Done |
| 3 | **Smart recommendations**: 3 songs you'd like based on the current one (MusicAtlas audio similarity, Gemma as fallback), with Play now and Add to queue | Done |
| 4 | Search, Up next queue, liked songs, device picker, shuffle, repeat and volume | Done |
| 5 | Play directly in the browser (Spotify Web Playback SDK) and media-key support | Done |
| 6 | Lyrics translation and AI explanations of what a song is about | Done |

## Limitations

- Requires an internet connection.
- Spotify access depends on Development Mode restrictions and authorized users.
- Playback controls only work with Spotify Premium and need an active Spotify device (a Spotify app that is open and has played something recently, or this browser tab).
- Playing in the browser needs Premium and a desktop browser with Widevine DRM (Chrome, Edge, Firefox; not most mobile browsers). Closing the tab stops the music.
- Some devices (often phones) don't allow volume control through Spotify's API; the volume slider is hidden for them.
- Spotify applies shuffle, repeat and volume changes with a short delay; the app keeps showing your choice for up to 5 seconds until Spotify confirms it.
- Clicking an album or artist in search starts playing it; there are no separate album or artist pages.
- Playback is polled every 3 seconds; between polls the position is estimated locally, so seeking in Spotify shows up after the next poll.
- AI facts can contain mistakes; the interface says so.
- Lyrics coverage depends on LRCLIB's community database and lyrics.ovh; very niche songs may still have none. lyrics.ovh only has plain lyrics, so those won't scroll with the song.
- MusicAtlas's free tier allows 100 requests per day; after that (or for songs it doesn't know) recommendations come from Gemma. Songs are cached for a day.
- Translations and explanations are AI-written and can be wrong; the interface says so.
- Prefetching uses two extra AI requests (facts and recommendations) for each queued song you skip before it plays (set `PREFETCH_NEXT=0` to turn it off).
- Recommendations depend on Gemini's music knowledge. For very niche songs it may suggest fewer than three songs that exist on Spotify, or none.
