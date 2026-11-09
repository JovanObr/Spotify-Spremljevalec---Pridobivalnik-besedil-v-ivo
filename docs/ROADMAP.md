# Roadmap

**Goal:** a focused replacement for the Spotify app. It keeps the features people use every day (what's playing, lyrics, playlists, search, queue) and adds AI where Spotify no longer offers anything (facts, recommendations). Everything else is left out on purpose.

Each phase can be shipped and demoed on its own.

---

## Constraints that shape the plan

Spotify's Web API has changed a lot. These rules apply to this app because it runs in **Development Mode**:

| Constraint | Effect on us |
| --- | --- |
| `GET /recommendations`, related artists and audio features are unavailable to new apps (Nov 2024) | Spotify can't recommend songs for us. **Gemini fills this gap** (Phase 3). |
| `GET /playlists/{id}/items` only works for playlists the user **owns or collaborates on** (Feb 2026) | We can list every playlist, but can show track lists only for the user's own. Followed playlists can still be **played** as a whole. |
| Spotify-owned editorial and algorithmic playlists (e.g. Discover Weekly) aren't available to new apps | They won't appear with tracks; don't promise them. |
| `GET /artists/{id}/top-tracks` and batch fetches (`GET /tracks?ids=`) were removed (Feb 2026) | Fetch items one by one and cache them. Artist pages are limited. |
| `GET /search` returns at most **10** results per request | Paginate with `offset`; keep result lists short (fits "lose the fluff"). |
| Library endpoints moved to `PUT/DELETE /me/library` | Spotipy 2.26+ already uses them, so `requirements.txt` requires `spotipy>=2.26`. |
| App owner needs Premium; at most 5 users per app; playback control needs Premium | Fine for a course project; document it for testers. |

---

## Phase 1: App shell and navigation ✅ Done

Today the app is one screen. Playlists, search and recommendations need navigation, so this phase comes first.

**Frontend**
- Add routing (React Router) with these views: **Now Playing** (the current lyrics screen), **Library** (playlists) and later **Search**.
- Desktop layout: a narrow left sidebar for navigation and a **mini player bar** at the bottom on every view except Now Playing.
- Mobile layout: a bottom tab bar and the same mini player.
- Quick wins, since we already have the permission:
  - **Seek** by clicking the progress bar.
  - **Click a lyric line to jump to it.** Spotify doesn't offer this.

**Backend**
- Split `api/app.py` into FastAPI routers: `auth`, `player`, `library`, `ai`.
- Add `POST /api/player/seek` (`position_ms`).
- **Request every Spotify permission planned in phases 2–5 in this phase.** Each change to the permission list makes users log in again, so bundling them means only one more login.

```text
user-read-currently-playing   (have)
user-modify-playback-state    (have)
user-read-playback-state      devices, shuffle/repeat state, queue
playlist-read-private         own + followed playlists
playlist-read-collaborative
user-library-read             liked songs, heart state
user-library-modify           like / unlike
user-read-recently-played     home screen, better AI context
streaming, user-read-email, user-read-private   Web Playback SDK (Phase 5)
```

**Done when:** you can switch between views on desktop and mobile without the music UI flickering, and clicking a lyric line seeks to it.

---

## Phase 2: Playlists ✅ Done

**Backend**

| Endpoint | Spotify call | Notes |
| --- | --- | --- |
| `GET /api/playlists` | `GET /me/playlists` | Returns name, cover, owner, track count and an `is_owned` flag. Paginated. |
| `GET /api/playlists/{id}` | `GET /playlists/{id}` + `/items` | Returns items only when `is_owned`; otherwise `items: null`. |
| `POST /api/player/play` | `PUT /me/player/play` | Extend the existing endpoint to accept `{context_uri, offset}` so a whole playlist, or a playlist from a given song, can start. |

- Cache playlist lists for about 60 seconds and playlist contents per `snapshot_id`, which changes only when the playlist changes.

**Frontend**
- **Library view:** a grid of playlist covers, with your own playlists first.
- **Playlist view:** header (cover, name, owner, total duration) and a track list. Click a track to play the playlist from that track.
- For followed playlists, show a **Play** button and the line "Spotify only shares track lists for playlists you own."
- Highlight the currently playing track in the list.

**Done when:** you can open any of your playlists, start it from any track, and the Now Playing view follows along.

---

## Phase 3: Smart recommendations ✅ Done

**Update: MusicAtlas first, Gemma as fallback.** With `MUSICATLAS_API_KEY` set, `POST https://musicatlas.ai/api/similar_tracks` returns songs that *sound* similar (audio analysis), each with its Spotify ID, plus style hashtags for the current song. The app takes one song per artist, checks up to six on Spotify (playable in your market), keeps three, and asks Gemma for a one-line reason for each (MusicAtlas doesn't give one). If the song isn't in MusicAtlas's catalogue, the quota is used up or the key is wrong, the Gemma flow below runs instead. The response says which source was used, and the panel's note changes with it.

The original Gemma flow:

"If you like this song, you'll probably like these 3."

**Flow** (`services/recommendation_service.py`)
1. The recommendations model (`GEMINI_RECOMMENDATIONS_MODEL`, Gemma 4 31B by default) gets the current song and returns **5 candidates** as structured JSON: `{title, artist, reason}`, where `reason` is one short sentence.
2. Each candidate is looked up with Spotify search, all five in parallel: first `track:"…" artist:"…"`, then a plain-text search. A result counts only if its title and artist loosely match (accents, "The", "- Remastered" are ignored).
   - Candidates that aren't on Spotify are dropped. This is the guard against made-up songs.
   - The current song and duplicates are dropped too.
3. The first **3** found are returned with Spotify's track data and the AI's reason.

**Design decisions**
- **Separate from facts (changed from the original plan):** merging facts and recommendations into one call would have halved AI requests, but it would also have made the facts slow again. Facts use the fast Flash-Lite model and appear first; recommendations use Gemma 4 31B, chosen for its much larger free daily quota (it replaced Gemini 3.8 Flash). Gemma is called through `generate_content`; if it refuses JSON mode, the format is described in the prompt and the answer is parsed leniently.
- Both are prefetched for the next song in the queue, so they're usually ready when it starts.
- Results are cached per song, and simultaneous requests for the same song share one AI call.
- Taste context from recently played songs was left out for now: it would make results less cacheable and prefetchable. It can be added to the prompt later.

**Endpoints:** `GET /api/recommendations?artist=&title=&album=&track_uri=`, `POST /api/player/queue` (`{uri}`), and `POST /api/player/play` with `{track_uri}` to play one song.

**Frontend:** an "If you like this" section on Now Playing, below the facts. Each of the three rows shows the cover, title, artist and the one-line reason, with **Play now** and **Add to queue** buttons. Adding to the queue shows a confirmation.

---

## Phase 4: Everyday essentials ✅ Done

Each of these is small, but together they're what makes this usable instead of Spotify:

- **Search** (`/search`): songs, artists, albums and playlists for one query, at most 10 of each (Spotify's limit). Songs play on click, artists and albums start playing, playlists open. The query is kept in the URL, so Back returns to the results.
- **Up next** (`/queue`): what's playing and the next 20 songs from `GET /me/player/queue`. Every song list has an add-to-queue button.
- **Like button:** a heart on Now Playing and in the mini player (`PUT/DELETE /me/library`), and a **Liked Songs** page in the Library that plays from any song (up to 100 at a time, Spotify's limit for a song list).
- **Devices:** a "Play on" list of Spotify apps and speakers; picking one moves playback there.
- **Shuffle, repeat (off, all, one) and volume.** Now playing reads Spotify's full player state (`GET /me/player`), which includes the device, shuffle, repeat and volume.
- Sliders (seek and volume) send one command per drag or burst of arrow-key presses.
- Fixes after testing: songs started from search, Up next or recommendations play inside their album (playing a lone song gave Spotify nothing to continue with, and its queue endpoint then repeats that song); Up next lists each song once; shuffle/repeat/volume are sent to the active device and held on screen until Spotify reports the change.

---

## Phase 5: Play in the browser ✅ Done

This is the step that makes it a real replacement. Today the app is a **remote control**: Spotify has to be running somewhere else. With the **Spotify Web Playback SDK**, the browser tab itself becomes a Spotify device, so nothing else needs to be open.

- Add `GET /api/token`, which hands the browser a short-lived access token. This is acceptable because the app only runs on `127.0.0.1`.
- On startup, the frontend registers a device called "Sound Companion" and offers to move playback to it.
- Use the **Media Session API** so keyboard media keys, Windows media controls and the phone lock screen work.
- Requires Premium, and the browser must support DRM (Widevine): Chrome, Edge and Firefox do.
- Verify the SDK's current status against Spotify's docs before starting this phase.

**How it was built**
- `GET /api/token` returns the cached token (Spotipy refreshes it) with `Cache-Control: no-store`, and refuses tokens without the `streaming` scope.
- `playback/spotifySdk.ts` loads `sdk.scdn.co/spotify-player.js` once; `WebPlayerProvider` creates the player, tracks its device ID and turns SDK errors into plain messages (Premium needed, browser unsupported, log in again).
- The device picker lists "Sound Companion" as *This browser* even before Spotify's device list catches up. When nothing is playing anywhere, play commands send `device_id` so music starts in the tab. Every play/transfer into the tab calls `activateElement()` during the click, which browsers require before a tab may play sound.
- Changes in the tab refresh Now Playing immediately instead of waiting for the next poll.
- `MediaSession` sets the title, artist, album art, position and play/pause/next/previous/seek handlers.

---

## Phase 6: More AI ✅ Done

- **Translate lyrics:** a Translate button above the lyrics shows a line-by-line translation under each line (synced or plain). The language picker and on/off state are remembered in the browser. Only distinct lines are sent, numbered, to the fast facts model (`GEMINI_FACTS_MODEL`), and the answer is mapped back by number, so choruses cost nothing extra and lines can't shift. Cached per song and language. Lines the model repeats unchanged (e.g. "oh, oh") aren't shown twice.
- **What's this song about:** a button in the side panel, so it only uses quota when asked. The lyrics (up to 6,000 characters) are sent as context with an instruction to paraphrase, never quote; the recommendations model (Gemma) writes 3 to 5 sentences and up to four themes. If no lyrics are found, it says the explanation is from general knowledge.
- Endpoints: `GET /api/lyrics/translation` and `GET /api/meaning`.

---

## Out of scope (the "fluff")

Podcasts and audiobooks, AI-generated playlists, social and friend activity, Wrapped-style statistics, artist bios and concert listings, Canvas videos, and editorial home-feed carousels.
