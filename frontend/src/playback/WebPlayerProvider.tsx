// Phase 5: this browser tab as a Spotify device ("Sound Companion"), using
// the Web Playback SDK. It shows up in the device list like any Spotify app.
// Needs Spotify Premium and a desktop browser with DRM (Widevine) support;
// everything else in the app works without it.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { api } from "../api/client";
import { strings } from "../lib/strings";
import { loadSpotifySdk, type SdkPlayer } from "./spotifySdk";

export type WebPlayerProblem = "unsupported" | "premium" | "auth" | "unavailable";

interface WebPlayerValue {
  /** This tab's Spotify device ID once it's ready, else null. */
  deviceId: string | null;
  status: "connecting" | "ready" | "failed";
  problem: WebPlayerProblem | null;
  /** Call from a click before playing here, so the browser allows sound. */
  activate: () => void;
}

const WebPlayerContext = createContext<WebPlayerValue>({
  deviceId: null,
  status: "failed",
  problem: "unavailable",
  activate: () => {},
});

// Changes in this tab (play, pause, next) refresh the UI right away instead
// of waiting for the next poll, but at most this often.
const REFRESH_THROTTLE_MS = 800;

export function WebPlayerProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const player = useRef<SdkPlayer | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [status, setStatus] = useState<WebPlayerValue["status"]>("connecting");
  const [problem, setProblem] = useState<WebPlayerProblem | null>(null);

  useEffect(() => {
    let cancelled = false;
    let lastRefresh = 0;

    const fail = (reason: WebPlayerProblem) => {
      if (cancelled) return;
      setProblem(reason);
      setStatus("failed");
      setDeviceId(null);
    };

    loadSpotifySdk()
      .then((Spotify) => {
        if (cancelled) return;

        const instance = new Spotify.Player({
          name: strings.appName,
          volume: 0.8,
          getOAuthToken: (callback) => {
            api
              .token()
              .then((token) => callback(token.access_token))
              .catch(() => fail("auth"));
          },
        });
        player.current = instance;

        instance.addListener("ready", ({ device_id }) => {
          if (cancelled) return;
          setDeviceId(device_id);
          setStatus("ready");
          setProblem(null);
          queryClient.invalidateQueries({ queryKey: ["devices"] });
        });
        instance.addListener("not_ready", () => {
          if (cancelled) return;
          setDeviceId(null);
          setStatus("connecting"); // the SDK reconnects by itself
        });
        instance.addListener("initialization_error", () => fail("unsupported"));
        instance.addListener("authentication_error", () => fail("auth"));
        instance.addListener("account_error", () => fail("premium"));
        instance.addListener("playback_error", (error) => {
          console.warn("Spotify playback error", error.message);
        });
        instance.addListener("player_state_changed", () => {
          const now = Date.now();
          if (now - lastRefresh < REFRESH_THROTTLE_MS) return;
          lastRefresh = now;
          window.setTimeout(
            () => queryClient.invalidateQueries({ queryKey: ["now-playing"] }),
            300,
          );
        });

        instance.connect().then((connected) => {
          if (!connected) fail("unavailable");
        });
      })
      .catch(() => fail("unavailable"));

    return () => {
      cancelled = true;
      player.current?.disconnect();
      player.current = null;
    };
  }, [queryClient]);

  const activate = useCallback(() => {
    player.current?.activateElement().catch(() => {
      // Older SDK builds or already active: nothing to do
    });
  }, []);

  return (
    <WebPlayerContext.Provider value={{ deviceId, status, problem, activate }}>
      {children}
    </WebPlayerContext.Provider>
  );
}

export function useWebPlayer() {
  return useContext(WebPlayerContext);
}
