import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { AppShell } from "./components/layout/AppShell";
import { ConnectScreen, ServerDownScreen } from "./components/Screens";
import { useStatus } from "./hooks/queries";
import { MediaSession } from "./playback/MediaSession";
import { PlaybackProvider } from "./playback/PlaybackProvider";
import { WebPlayerProvider } from "./playback/WebPlayerProvider";
import { LibraryView } from "./views/LibraryView";
import { LikedView } from "./views/LikedView";
import { NowPlayingView } from "./views/NowPlayingView";
import { PlaylistView } from "./views/PlaylistView";
import { QueueView } from "./views/QueueView";
import { SearchView } from "./views/SearchView";

export default function App() {
  const { data, error, isPending } = useStatus();

  if (isPending) return null;

  // No answer from /api/status means the Python server isn't running
  if (error) return <ServerDownScreen />;

  if (!data.authenticated) return <ConnectScreen />;

  return (
    <BrowserRouter>
      <WebPlayerProvider>
        <PlaybackProvider>
          <MediaSession />
          <Routes>
            <Route element={<AppShell />}>
              <Route
                index
                element={
                  <NowPlayingView
                    aiEnabled={data.ai_enabled}
                    recommendationsEnabled={data.recommendations_enabled}
                  />
                }
              />
              <Route path="search" element={<SearchView />} />
              <Route path="queue" element={<QueueView />} />
              <Route path="library" element={<LibraryView />} />
              <Route path="library/liked" element={<LikedView />} />
              <Route path="library/:playlistId" element={<PlaylistView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </PlaybackProvider>
      </WebPlayerProvider>
    </BrowserRouter>
  );
}
