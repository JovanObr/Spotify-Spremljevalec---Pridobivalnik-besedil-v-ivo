// Loads the Spotify Web Playback SDK (https://developer.spotify.com/documentation/web-playback-sdk)
// and describes the small part of it this app uses.

const SDK_URL = "https://sdk.scdn.co/spotify-player.js";
const LOAD_TIMEOUT_MS = 15_000;

export interface SdkError {
  message: string;
}

export interface SdkPlayerState {
  paused: boolean;
  position: number;
  track_window: { current_track: { uri: string } | null };
}

type ErrorEvent =
  | "initialization_error"
  | "authentication_error"
  | "account_error"
  | "playback_error";

export interface SdkPlayer {
  connect(): Promise<boolean>;
  disconnect(): void;
  addListener(event: "ready" | "not_ready", listener: (data: { device_id: string }) => void): boolean;
  addListener(event: ErrorEvent, listener: (error: SdkError) => void): boolean;
  addListener(event: "player_state_changed", listener: (state: SdkPlayerState | null) => void): boolean;
  addListener(event: "autoplay_failed", listener: () => void): boolean;
  /** Must run inside a click/tap so the browser lets the tab play sound. */
  activateElement(): Promise<void>;
}

export interface SdkPlayerOptions {
  name: string;
  getOAuthToken: (callback: (token: string) => void) => void;
  volume?: number;
}

declare global {
  interface Window {
    onSpotifyWebPlaybackSDKReady?: () => void;
    Spotify?: { Player: new (options: SdkPlayerOptions) => SdkPlayer };
  }
}

let loading: Promise<NonNullable<Window["Spotify"]>> | null = null;

/** The SDK's global, loading the script the first time. Rejects if it can't load. */
export function loadSpotifySdk(): Promise<NonNullable<Window["Spotify"]>> {
  if (window.Spotify) return Promise.resolve(window.Spotify);
  if (loading) return loading;

  loading = new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => fail(new Error("Spotify player timed out")), LOAD_TIMEOUT_MS);
    const fail = (error: Error) => {
      window.clearTimeout(timer);
      loading = null; // allow another try later
      reject(error);
    };

    // The script calls this once it's ready
    window.onSpotifyWebPlaybackSDKReady = () => {
      window.clearTimeout(timer);
      if (window.Spotify) resolve(window.Spotify);
      else fail(new Error("Spotify player missing"));
    };

    const script = document.createElement("script");
    script.src = SDK_URL;
    script.async = true;
    script.onerror = () => fail(new Error("Spotify player couldn't load"));
    document.head.appendChild(script);
  });

  return loading;
}
