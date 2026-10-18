# Spotify Sound Companion

A lightweight Python application that connects to your active Spotify session to fetch real-time playback stats, track info, and song lyrics. Designed as a modular service integration project with upcoming web dashboard and AI enhancement features.

---

## Features

* **Real-time Track Polling:** Automatically detects the track currently playing on your Spotify account.
* **Lyrics Synchronization:** Fetches matching song lyrics using the `Lyrics.ovh` REST API.
* **Track Metadata:** Displays album artwork URLs, artist names, album titles, and playback progress.
* **OAuth 2.0 Integration:** Secure authentication using Spotify's official OAuth flow with `user-read-currently-playing` scope.

---

## Tech Stack

* **Language:** Python 3.9+
* **APIs & Services:**
  * [Spotify Web API](https://developer.spotify.com/documentation/web-api) (via `spotipy`)
  * [Lyrics.ovh API](https://lyricsovh.docs.apiary.io/)
* **Dependencies:** `requests`, `spotipy`, `python-dotenv`

---

## Data Specifications

Data transferred over REST APIs using JSON over HTTPS.

### 1. Spotify Currently Playing Payload
* **Endpoint:** `GET /v1/me/player/currently-playing`
* **Data Types & Fields:**
  * `is_playing`: `boolean` (current status)
  * `item.name`: `string` (track title)
  * `item.artists[].name`: `string` (artist names)
  * `item.album.images[].url`: `string` (HTTPS URL to cover image)
  * `item.duration_ms`: `integer` (track duration)

### 2. Lyrics API Payload
* **Endpoint:** `GET /v1/{artist}/{title}`
* **Data Types & Fields:**
  * `lyrics`: `string` (raw lyrics with newline characters)

---

## Service Documentation

1. **Spotify Web API**
   * **Description:** Provides metadata for tracks, currently playing media, user library data, and playlist control.
   * **Auth:** OAuth 2.0 (Authorization Code Flow)
   * **Docs:** https://developer.spotify.com/documentation/web-api

2. **Lyrics.ovh API**
   * **Description:** Free public REST service for retrieving song text by artist and track title.
   * **Auth:** None (Public API)
   * **Docs:** https://lyricsovh.docs.apiary.io/

---

## Project Roadmap (Upcoming Features)

The project is designed to expand across three major development milestones:

- [ ] **🎛️ Live Web Dashboard**
  - Web UI built with **FastAPI / Flask** and **Tailwind CSS**.
  - Auto-refreshing player card with dynamic album artwork, progress bar, and synced scrolling lyrics.
- [ ] **🤖 AI Track Trivia**
  - Integration with an LLM API (Gemini / OpenAI) to generate real-time trivia, song origin stories, and fun facts about the current artist.
- [ ] **➕ Playlist Curation**
  - Quick action controls to instantly save the currently playing track to a designated "Favorites" or "Discovery" Spotify playlist.

---

## Setup & Installation

### 1. Prerequisites
* Python 3.9 or higher.
* A Spotify account (free or Premium).
* A registered application on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

### 2. Spotify API Keys Setup
1. Log into the Spotify Developer Dashboard and create a new app.
2. Note down your **Client ID** and **Client Secret**.
3. In your app settings, set the Redirect URI to `http://127.0.0.1:8888/callback`.

### 3. Repository Setup
Clone the repository and install the required dependencies:

```bash
git clone https://github.com/your-username/spotify-sound-companion.git
cd spotify-sound-companion
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root directory and add your credentials:

```env
SPOTIPY_CLIENT_ID="your_spotify_client_id"
SPOTIPY_CLIENT_SECRET="your_spotify_client_secret"
SPOTIPY_REDIRECT_URI="http://127.0.0.1:8888/callback"
```

---

## Usage

Run the main script to start listening for active Spotify playback:

```bash
python main.py
```

On first run, a browser window will open asking you to log into Spotify and authorize the app. Once authorized, the terminal will print details and lyrics for whatever track is currently playing.

