import { Link } from "react-router";

import { DevicePicker } from "../components/DevicePicker";
import { FactsPanel } from "../components/FactsPanel";
import { QueueIcon } from "../components/icons";
import { LyricsView } from "../components/LyricsView";
import { MeaningPanel } from "../components/MeaningPanel";
import { NowPlaying } from "../components/NowPlaying";
import { PlayerControls } from "../components/PlayerControls";
import { RecommendationsPanel } from "../components/RecommendationsPanel";
import { IdleScreen } from "../components/Screens";
import { VolumeControl } from "../components/VolumeControl";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";

export function NowPlayingView({
  aiEnabled,
  recommendationsEnabled,
}: {
  aiEnabled: boolean;
  recommendationsEnabled: boolean;
}) {
  const { playback, progressMs, isLoading, isBusy, run, seek, toggleShuffle, cycleRepeat } =
    usePlayback();

  if (isLoading) return null;
  if (!playback) return <IdleScreen />;

  const { track } = playback;

  return (
    <div className="mx-auto grid max-w-[90rem] px-6 lg:h-full lg:grid-cols-[minmax(18rem,22rem)_1fr] lg:gap-x-20 lg:px-12 xl:gap-x-28 2xl:gap-x-36">
      <aside className="flex flex-col gap-8 pt-6 pb-2 lg:-mr-6 lg:overflow-y-auto lg:py-12 lg:pr-6">
        <NowPlaying
          playback={playback}
          progressMs={progressMs}
          onSeek={seek}
          controls={
            <PlayerControls
              isPlaying={playback.is_playing}
              disabled={isBusy}
              onAction={run}
              shuffle={playback.shuffle}
              repeat={playback.repeat}
              onShuffle={toggleShuffle}
              onRepeat={cycleRepeat}
            />
          }
          extras={
            <div className="-ml-2.5 flex flex-wrap items-center gap-x-1 gap-y-2">
              <Link
                to="/queue"
                className="flex h-10 items-center gap-2 rounded-full px-2.5 text-sm text-ink-soft transition-colors hover:bg-line hover:text-ink"
              >
                <QueueIcon size={19} />
                {strings.playback.upNext}
              </Link>
              <DevicePicker />
              <VolumeControl className="w-28 pl-1 max-lg:hidden" />
            </div>
          }
        />

        <div className="flex flex-col gap-8 max-lg:hidden">
          <FactsPanel track={track} aiEnabled={aiEnabled} />
          <MeaningPanel key={track.uri ?? track.title} track={track} aiEnabled={aiEnabled} />
          <RecommendationsPanel track={track} enabled={recommendationsEnabled} />
        </div>

        {track.spotify_url && (
          <a
            href={track.spotify_url}
            target="_blank"
            rel="noreferrer"
            className="mt-auto text-sm text-ink-faint hover:text-ink max-lg:hidden"
          >
            {strings.playback.openInSpotify}
          </a>
        )}
      </aside>

      <section className="relative h-[62dvh] min-h-0 lg:h-auto lg:py-6" aria-label="Lyrics">
        <LyricsView track={track} progressMs={progressMs} onSeek={seek} aiEnabled={aiEnabled} />
      </section>

      <div className="flex flex-col gap-8 pb-10 lg:hidden">
        <FactsPanel track={track} aiEnabled={aiEnabled} />
        <MeaningPanel key={track.uri ?? track.title} track={track} aiEnabled={aiEnabled} />
        <RecommendationsPanel track={track} enabled={recommendationsEnabled} />
      </div>
    </div>
  );
}
