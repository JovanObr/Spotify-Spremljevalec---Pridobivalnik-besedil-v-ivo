# Spotify Sound Companion

A Python desktop application that monitors Spotify playback and displays information about the currently playing track.

The application uses the Spotify Web API to retrieve track information, detects playback changes, and provides a direct lyrics search link.

## Features

### Implemented

- Spotify authentication using OAuth 2.0.
- Retrieval of the currently playing track.
- Track metadata:
  - Track title
  - Artist
  - Album
  - Playback progress
  - Track duration
- Album artwork URL retrieval.
- Lyrics search link generation through Genius.
- Continuous playback monitoring.
- Automatic detection of track changes.
- Pause and resume detection.
- Handling of missing playback information.
- Spotify API error handling, including rate limits.
- Automated tests for playback monitoring, duration formatting, and error handling.

### Planned

- AI-generated facts about songs and artists.
- Improved terminal presentation.
- Additional music metadata and contextual information.

## Technologies

- Python
- Spotipy
- Spotify Web API
- Requests
- Python-dotenv
- Genius search

## Requirements

- Python 3.10 or newer.
- A Spotify account.
- A Spotify Developer application configured for Development Mode.
- An active Premium subscription on the Spotify application owner's account.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/JovanObr/Spotify-Spremljevalec---Pridobivalnik-besedil-v-ivo.git
cd Spotify-Spremljevalec---Pridobivalnik-besedil-v-ivo
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again.

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Spotify configuration

### 1. Create a Spotify Developer application

Visit:

https://developer.spotify.com/dashboard

Create an application and configure:

- API: Web API
- Redirect URI: `http://127.0.0.1:8888/callback`

### 2. Configure authorized users

In the application's settings, open User Management and add the Spotify account that will authenticate with the application.

Development Mode applications have restrictions on authorized users and require an eligible Premium subscription for the application owner.

### 3. Configure environment variables

Create a `.env` file in the repository root:

```env
SPOTIPY_CLIENT_ID="your_client_id"
SPOTIPY_CLIENT_SECRET="your_client_secret"
SPOTIPY_REDIRECT_URI="http://127.0.0.1:8888/callback"
```

Replace the placeholder values with your Spotify application's credentials.

**Never commit your `.env` file or share your Client Secret.**

## Running the application

Activate the virtual environment and execute:

```bash
python main.py
```

On the first run, Spotify OAuth authentication will open in your browser.

After authorization, the application will begin monitoring playback.

The default polling interval is five seconds.

Press `Ctrl+C` to stop the application.

## Running tests

Execute the automated test suite:

```bash
python -m unittest discover -s tests -v
```

The tests cover:

- Playback monitoring and track changes.
- Pause and resume transitions.
- Missing playback information.
- Duration formatting.
- Spotify API error handling and rate limits.

The lyrics service can also be tested separately:

```bash
python -m tests.test_lyrics_service
```

## Project structure

```text
Spotify-Sound-Companion/
│
├── main.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
│
├── core/
│   ├── __init__.py
│   └── config.py
│
├── services/
│   ├── __init__.py
│   ├── spotify_service.py
│   └── lyrics_service.py
│
├── utils/
│   ├── __init__.py
│   ├── display.py
│   └── spotify_errors.py
│
└── tests/
    ├── test_lyrics_service.py
    ├── test_playback_monitor.py
    ├── test_display.py
    └── test_spotify_errors.py
```

## Limitations

- The application requires an internet connection.
- Spotify API access depends on the application's Development Mode eligibility and account authorization.
- Lyrics are accessed through an external Genius search link; the application does not retrieve or display full lyrics.
- Album artwork is currently displayed as a URL rather than an inline image.
- AI-generated music facts are planned but are not yet implemented.
- Playback monitoring relies on periodic polling, so changes may take several seconds to appear.

## License

Add the project's chosen license here if you intend to distribute the application.
