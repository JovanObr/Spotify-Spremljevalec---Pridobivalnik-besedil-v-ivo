// Compact player shown on every view except Now Playing.

import { Link } from "react-router";

import { usePlayback } from "../../playback/PlaybackProvider";
import { strings } from "../../lib/strings";
import { DevicePicker } from "../DevicePicker";
import { QueueIcon } from "../icons";
import { LikeButton } from "../LikeButton";
import { PlayerControls } from "../PlayerControls";
import { SeekBar } from "../SeekBar";
import { VolumeControl } from "../VolumeControl";

export function MiniPlayer() {
  const { playback, progressMs, isBusy, run, seek } = usePlayback();
  if (!playback) return null;

  const { track } = playback;
  const ratio = track.duration_ms ? Math.min(1, progressMs / track.duration_ms) : 0;

  return (
    <section
      aria-label={strings.nav.nowPlaying}
      className="relative z-10 border-t border-line bg-bg-deep/80 backdrop-blur-lg max-lg:fixed max-lg:inset-x-0 max-lg:bottom-[calc(4rem+env(safe-area-inset-bottom))]"
    >
      {/* Mobile: thin progress line along the top edge */}
      <div className="absolute inset-x-0 top-0 h-0.5 bg-line lg:hidden" aria-hidden="true">
        <div className="h-full origin-left bg-accent" style={{ transform: `scaleX(${ratio})` }} />
      </div>

      <div className="mx-auto flex max-w-[90rem] items-center gap-4 px-4 py-2.5 lg:gap-8 lg:px-8 lg:py-3">
        <Link
          to="/"
          className="flex min-w-0 flex-1 items-center gap-3 rounded-md lg:max-w-xs"
          aria-label={`${strings.miniPlayer.open}: ${track.title}, ${track.artist}`}
        >
          <div className="size-11 shrink-0 overflow-hidden rounded bg-line">
            {track.artwork_url && (
              <img src={track.artwork_url} alt="" className="h-full w-full object-cover" />
            )}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-[600] text-ink">{track.title}</p>
            <p className="truncate text-xs text-ink-soft">{track.artist}</p>
          </div>
        </Link>

        <div className="max-lg:hidden">
          <LikeButton track={track} size={18} />
        </div>

        <PlayerControls
          isPlaying={playback.is_playing}
          disabled={isBusy}
          onAction={run}
          compact
        />

        <SeekBar
          progressMs={progressMs}
          durationMs={track.duration_ms}
          onSeek={seek}
          className="max-w-md flex-1 max-lg:hidden"
        />

        <div className="flex items-center gap-1 max-lg:hidden">
          <Link
            to="/queue"
            aria-label={strings.playback.upNext}
            title={strings.playback.upNext}
            className="grid size-10 place-items-center rounded-full text-ink-soft transition-colors hover:bg-line hover:text-ink"
          >
            <QueueIcon size={19} />
          </Link>
          <DevicePicker placement="above" showName={false} />
          <VolumeControl className="w-32" />
        </div>
      </div>
    </section>
  );
}
