import type { Track } from "../../api/types";
import { formatDuration } from "../../lib/format";
import { strings } from "../../lib/strings";
import { usePlayback } from "../../playback/PlaybackProvider";
import { QueueIcon } from "../icons";

// Shared by the column header and the rows so they always line up
export const TRACK_GRID =
  "grid grid-cols-[2rem_minmax(0,1fr)_3.5rem_2.5rem] items-center gap-x-3 md:grid-cols-[2.5rem_minmax(0,3fr)_minmax(0,2fr)_4rem_2.5rem] md:gap-x-4";

interface Props {
  track: Track;
  /** Row number shown on the left (1-based). */
  number: number;
  isCurrent: boolean;
  isPlaying: boolean;
  onPlay: () => void;
  /** Hide the album column (e.g. in search results). */
  hideAlbum?: boolean;
}

/**
 * A song in a list. The whole row plays it; the queue button on the right is
 * a separate control layered above the row's play button.
 */
export function TrackRow({ track, number, isCurrent, isPlaying, onPlay, hideAlbum = false }: Props) {
  const { addToQueue, isBusy } = usePlayback();
  const playable = track.is_playable && Boolean(track.uri);

  return (
    <li
      className={`group relative rounded-md transition-colors ${playable ? "hover:bg-line" : "opacity-40"}`}
      title={playable ? undefined : strings.playlist.unavailable}
    >
      <button
        type="button"
        onClick={onPlay}
        disabled={!playable}
        aria-current={isCurrent ? "true" : undefined}
        aria-label={`${track.title}, ${track.artist}`}
        className="absolute inset-0 cursor-pointer rounded-md disabled:cursor-default"
      />

      <div className={`${TRACK_GRID} pointer-events-none relative px-3 py-2`}>
        <span className="text-right text-sm text-ink-faint tabular-nums">
          {isCurrent ? <NowPlayingBars animated={isPlaying} /> : number}
        </span>

        <span className="flex min-w-0 items-center gap-3">
          <span className="size-10 shrink-0 overflow-hidden rounded bg-line">
            {track.thumbnail_url && (
              <img src={track.thumbnail_url} alt="" loading="lazy" className="h-full w-full object-cover" />
            )}
          </span>
          <span className="min-w-0">
            <span className={`block truncate font-[550] ${isCurrent ? "text-accent" : "text-ink"}`}>
              {track.title}
            </span>
            <span className="block truncate text-sm text-ink-soft">{track.artist}</span>
          </span>
        </span>

        <span className={`truncate text-sm text-ink-soft max-md:hidden ${hideAlbum ? "invisible" : ""}`}>
          {track.album}
        </span>

        <span className="text-right text-sm text-ink-faint tabular-nums">
          {formatDuration(track.duration_ms)}
        </span>

        <span className="flex justify-end">
          {playable && track.uri && (
            <button
              type="button"
              onClick={() => addToQueue(track.uri!, track.title)}
              disabled={isBusy}
              aria-label={strings.playback.addToQueue(track.title)}
              title={strings.playback.addToQueue(track.title)}
              className="pointer-events-auto grid size-9 cursor-pointer place-items-center rounded-full text-ink-faint opacity-0 transition hover:bg-accent hover:text-bg-deep group-hover:opacity-100 focus-visible:opacity-100 max-lg:opacity-100"
            >
              <QueueIcon size={18} />
            </button>
          )}
        </span>
      </div>
    </li>
  );
}

/** Three bars marking the current track; they move only while it plays. */
function NowPlayingBars({ animated }: { animated: boolean }) {
  return (
    <span className="inline-flex h-3.5 items-end justify-end gap-[2px]" aria-label="Current song">
      {[0, 1, 2].map((bar) => (
        <span
          key={bar}
          className={`w-[3px] rounded-full bg-accent ${animated ? "now-playing-bar" : ""}`}
          style={{ height: `${[60, 100, 75][bar]}%`, animationDelay: `${bar * -0.35}s` }}
        />
      ))}
    </span>
  );
}
