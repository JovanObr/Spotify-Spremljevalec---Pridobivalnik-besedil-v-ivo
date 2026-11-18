// All user-facing text in one place, so wording changes (or a Slovenian
// translation) never require touching components.

export const strings = {
  appName: "Sound Companion",

  connect: {
    title: "Lyrics that keep time with your music",
    body: "Connect your Spotify account. Whatever you play shows up here with synced lyrics and a few facts about the song.",
    button: "Connect Spotify",
    authFailed: "Spotify login didn't finish. Try connecting again.",
  },

  serverDown: {
    title: "The companion server isn't running",
    body: "Start it from the project folder with  python -m api  and this page reconnects on its own.",
  },

  idle: {
    title: "Nothing playing on Spotify",
    body: "Start a song in any Spotify app and it appears here within a few seconds.",
    bodyWithBrowser:
      "Start a song in any Spotify app, or pick one here and it plays right in this browser.",
    searchLink: "Find something to play",
  },

  nav: {
    nowPlaying: "Now playing",
    search: "Search",
    library: "Library",
    insights: "Insights",
    main: "Main",
  },

  library: {
    title: "Library",
    yours: "Your playlists",
    following: "Following",
    empty: "No playlists yet. Playlists you create or follow in Spotify show up here.",
    error: "Your playlists couldn't be loaded.",
    retry: "Try again",
    playing: "Playing",
    songs: (count: number) => `${count} ${count === 1 ? "song" : "songs"}`,
    by: (owner: string) => `By ${owner}`,
    play: (name: string) => `Play ${name}`,
  },

  playlist: {
    back: "Library",
    play: "Play",
    pause: "Pause",
    notFound: "This playlist doesn't exist or isn't available anymore.",
    error: "This playlist couldn't be loaded.",
    notShared:
      "Spotify only shares track lists for playlists you own or collaborate on. You can still play it.",
    columns: { title: "Title", album: "Album", duration: "Length" },
    loadingMore: "Loading more songs…",
    unavailable: "Not available to play",
  },

  miniPlayer: {
    open: "Open now playing",
  },

  playback: {
    paused: "Paused",
    openInSpotify: "Open in Spotify",
    disconnect: "Disconnect",
    play: "Play",
    pause: "Pause",
    next: "Next song",
    previous: "Previous song",
    controlFailed: "Spotify didn't respond. Try again.",
    jumpToLine: "Click a line to jump to it",
    queued: (title: string) => `Added "${title}" to your queue`,
    addToQueue: (title: string) => `Add ${title} to queue`,
    shuffleOn: "Shuffle is on",
    shuffleOff: "Shuffle",
    repeatOff: "Repeat",
    repeatAll: "Repeating all",
    repeatOne: "Repeating this song",
    upNext: "Up next",
  },

  lyrics: {
    loading: "Finding lyrics…",
    notFound: "No lyrics found for this song.",
    searchWeb: "Search for the lyrics on Genius",
    instrumental: "Instrumental. Enjoy the music.",
    unsynced: "These lyrics aren't time-synced, so they won't follow along.",
    error: "Lyrics couldn't be loaded. Retrying shortly.",
    source: (source: string) => `Lyrics from ${source}`,
  },

  translation: {
    show: "Translate",
    hide: "Hide translation",
    language: "Translation language",
    loading: (language: string) => `Translating into ${language}…`,
    error: "The translation couldn't be made right now.",
    rateLimited: "The AI's free quota is used up for now. Try again later.",
    retry: "Try again",
    disclaimer: (language: string) => `${language} translation by AI. It can make mistakes.`,
  },

  meaning: {
    heading: "What's this song about",
    ask: "Explain this song",
    loading: "Reading between the lines…",
    error: "The explanation couldn't be written right now.",
    rateLimited: "The AI's free quota is used up for now. Try again later.",
    retry: "Try again",
    fromLyrics: "Based on the lyrics. Written by AI, so treat it as one reading.",
    withoutLyrics: "No lyrics were found, so this is from what the AI knows about the song.",
  },

  facts: {
    heading: "About this song",
    loading: "Asking Gemini…",
    disabled: "Add a GEMINI_API_KEY to .env to see facts about each song.",
    error: "Facts couldn't be generated right now.",
    rateLimited: "Gemini's free quota is used up for now. Try again later.",
    retry: "Try again",
    disclaimer: "Written by Gemini. It can make mistakes.",
  },

  recommendations: {
    heading: "If you like this",
    loading: "Finding songs you might like…",
    empty: "No recommendations found for this song.",
    error: "Recommendations couldn't be loaded right now.",
    rateLimited: "Gemini's free quota is used up for now. Try again later.",
    retry: "Try again",
    playNow: (title: string) => `Play ${title} now`,
    addToQueue: (title: string) => `Add ${title} to queue`,
    disclaimer: {
      musicatlas: "Picked by MusicAtlas audio analysis. Reasons written by AI.",
      musicatlasNoReasons: "Picked by MusicAtlas audio analysis.",
      ai: "Picked by AI and checked on Spotify.",
    },
  },

  like: {
    like: (title: string) => `Add ${title} to Liked Songs`,
    unlike: (title: string) => `Remove ${title} from Liked Songs`,
    liked: (title: string) => `Added "${title}" to Liked Songs`,
    unliked: (title: string) => `Removed "${title}" from Liked Songs`,
    failed: "Couldn't update Liked Songs. Try again.",
  },

  details: {
    heading: "Song details",
    loading: "Looking the song up on Wikipedia…",
    error: "Wikipedia couldn't be reached right now.",
    retry: "Try again",
    notFound: "Wikipedia has no article about this song.",
    fromAlbum: (album: string) => `From the album ${album}`,
    readMore: "Read on Wikipedia",
    artistHeading: "About the artist",
    country: "Country",
    capital: "Capital",
    language: "Language",
    currency: "Currency",
    flagAlt: (country: string) => `Flag of ${country}`,
    countryUnavailable: "Country details are unavailable right now.",
    attribution: "From Wikipedia. Country details from CountryInfoService.",
  },

  insights: {
    title: "Insights",
    tabs: { stats: "Music in Slovenia", sources: "Data sources" },
  },

  stats: {
    loading: "Loading the table from SiStat…",
    error: "SiStat couldn't be reached, and there's no saved copy yet.",
    notConfigured: "No SiStat table is configured yet.",
    retry: "Try again",
    stale: "SiStat couldn't be reached, so this is the last saved copy.",
    updated: (date: string) => `SiStat last updated this table on ${date}.`,
    fetched: (when: string) => `Fetched ${when}.`,
    compareBy: "Compare",
    from: "From",
    to: "To",
    show: "Show",
    table: "Table",
    chart: "Chart",
    noData: "No figures for this selection.",
    download: "Download CSV",
    sortBy: (column: string) => `Sort by ${column}`,
    source: "Source: Statistical Office of the Republic of Slovenia (SiStat), PC-Axis file",
    openOnSiStat: "Open the table on SiStat",
  },

  sources: {
    intro:
      "Everything this app shows comes from these sources. Each is reached with the technology shown and fetched again on the schedule below.",
    delivery: "How the data reaches you",
    technology: "Technology",
    provides: "Provides",
    refresh: "Refreshed",
    lastFetched: "Last fetched",
    never: "Not used yet",
    state: { ok: "Working", error: "Last request failed", unused: "Not used yet" },
    refreshNow: "Fetch again",
    refreshing: "Clearing…",
    refreshed: (name: string) => `${name}: saved data cleared. It's fetched again the next time it's needed.`,
    quota: "Uses a daily quota, so it isn't refetched by hand.",
    requests: (count: number) => `${count} ${count === 1 ? "request" : "requests"} since the server started`,
  },

  recent: {
    title: "Recently played",
    subtitle: "Your last 50 plays, newest first",
    tile: "Your last 50 plays",
    empty: "Nothing played recently. Songs show up here a minute or two after you play them.",
    error: "Your recently played songs couldn't be loaded.",
    playedAt: (when: string) => `Played ${when}`,
  },

  addToPlaylist: {
    button: (title: string) => `Add "${title}" to a playlist`,
    heading: "Add to playlist",
    filter: "Find a playlist",
    loading: "Loading your playlists…",
    error: "Your playlists couldn't be loaded.",
    none: "You don't have any playlists you can add to. Create one in Spotify first.",
    noMatch: "No playlist with that name.",
    added: (title: string, playlist: string) => `Added "${title}" to ${playlist}`,
    failed: "Couldn't add the song. Try again.",
    forbidden: "You can only add songs to playlists you own or collaborate on.",
  },

  liked: {
    title: "Liked Songs",
    empty: "Songs you like show up here. Tap the heart next to any song.",
    error: "Your liked songs couldn't be loaded.",
  },

  queue: {
    title: "Up next",
    nowPlaying: "Now playing",
    next: "Next in queue",
    empty: "Nothing queued. Use the add-to-queue button next to any song.",
    error: "The queue couldn't be loaded.",
    nothingPlaying: "Start playing something to see what comes next.",
  },

  devices: {
    button: "Devices",
    title: "Play on",
    current: "Playing here",
    loading: "Looking for devices…",
    none: "No devices found. Open Spotify on your phone, computer or speaker.",
    error: "Devices couldn't be loaded.",
    switched: (name: string) => `Playing on ${name}`,
    thisBrowser: "This browser",
    playHere: "Play here",
    webPlayer: {
      connecting: "Getting this browser ready to play…",
      unsupported: "This browser can't play Spotify. Use desktop Chrome, Edge or Firefox.",
      premium: "Playing in the browser needs Spotify Premium.",
      auth: "Log out and connect Spotify again to play in this browser.",
      unavailable: "This browser can't play Spotify right now.",
    },
    volume: "Volume",
  },

  search: {
    placeholder: "Songs, artists, albums or playlists",
    label: "Search Spotify",
    hint: "Find something to play.",
    noResults: (query: string) => `Nothing found for "${query}".`,
    error: "Search isn't working right now. Try again in a moment.",
    songs: "Songs",
    artists: "Artists",
    albums: "Albums",
    playlists: "Playlists",
    playArtist: (name: string) => `Play ${name}`,
    playAlbum: (name: string) => `Play ${name}`,
  },

  spotifyError: {
    rateLimited: "Spotify is limiting requests. Updates resume shortly.",
    forbidden:
      "Spotify denied access. Add your account under User Management in the Spotify developer dashboard.",
  },
};

/** Language the AI facts are written in. */
export const FACTS_LANGUAGE = "English";
