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
  },

  nav: {
    nowPlaying: "Now playing",
    search: "Search",
    library: "Library",
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
    disclaimer: "Picked by Gemini and checked on Spotify.",
  },

  like: {
    like: (title: string) => `Add ${title} to Liked Songs`,
    unlike: (title: string) => `Remove ${title} from Liked Songs`,
    liked: (title: string) => `Added "${title}" to Liked Songs`,
    unliked: (title: string) => `Removed "${title}" from Liked Songs`,
    failed: "Couldn't update Liked Songs. Try again.",
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
