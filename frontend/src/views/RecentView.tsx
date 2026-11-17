import { Link } from "react-router";

import { HistoryIcon } from "../components/icons";
import { TRACK_GRID, TrackRow } from "../components/library/TrackRow";
import { useRecentlyPlayed } from "../hooks/queries";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";

export function RecentView() {
  const { playback, playTracks, isBusy } = usePlayback();
  const { data: rows = [], isPending, isError } = useRecentlyPlayed();
  const currentUri = playback?.track.uri;

  // Play from a song: that song and the ones played before it
  const playFrom = (index: number) => {
    const uris = rows
      .slice(index)
      .filter((row) => row.track.is_playable)
      .map((row) => row.track.uri)
      .filter((uri): uri is string => Boolean(uri));
    if (uris.length) playTracks(uris);
  };

  return (
    <div className="mx-auto max-w-[90rem] px-6 py-8 lg:px-12 lg:py-10">
      <Link to="/library" className="inline-flex items-center gap-1.5 text-sm text-ink-faint hover:text-ink">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m15 6-6 6 6 6" />
        </svg>
        {strings.playlist.back}
      </Link>

      <header className="mt-6 flex flex-col gap-6 sm:flex-row sm:items-end sm:gap-8">
        <RecentCover className="w-44 lg:w-56" />
        <div>
          <h1 className="text-[clamp(2.2rem,5vw,4rem)] leading-[1] font-[720] tracking-[-0.03em] [font-stretch:88%]">
            {strings.recent.title}
          </h1>
          <p className="mt-3 text-sm text-ink-faint">{strings.recent.subtitle}</p>
          <button
            type="button"
            onClick={() => playFrom(0)}
            disabled={isBusy || rows.length === 0}
            className="mt-6 inline-flex cursor-pointer items-center gap-2 rounded-full bg-accent py-2.5 pr-6 pl-5 font-[650] text-bg-deep transition-transform hover:scale-[1.03] active:scale-[0.98] disabled:opacity-60"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
              <path d="M8 5.5v13L19 12z" />
            </svg>
            {strings.playlist.play}
          </button>
        </div>
      </header>

      {isError ? (
        <p className="mt-10 text-ink-soft">{strings.recent.error}</p>
      ) : !isPending && rows.length === 0 ? (
        <p className="mt-10 max-w-lg text-lg text-ink-soft">{strings.recent.empty}</p>
      ) : (
        <section className="mt-10" aria-label={strings.recent.title}>
          <div className={`${TRACK_GRID} border-b border-line px-3 pb-2 text-sm text-ink-faint`} aria-hidden="true">
            <span className="text-right">#</span>
            <span>{strings.playlist.columns.title}</span>
            <span className="max-md:hidden">{strings.playlist.columns.album}</span>
            <span className="text-right max-sm:hidden">{strings.playlist.columns.duration}</span>
            <span />
          </div>
          <ol className="mt-2">
            {rows.map((row, index) => {
              const isCurrent = Boolean(currentUri) && row.track.uri === currentUri;
              return (
                <TrackRow
                  key={row.track.uri ?? index}
                  track={row.track}
                  number={index + 1}
                  isCurrent={isCurrent}
                  isPlaying={isCurrent && Boolean(playback?.is_playing)}
                  onPlay={() => playFrom(index)}
                />
              );
            })}
          </ol>
        </section>
      )}
    </div>
  );
}

/** The Recently played artwork: a clock on a soft accent gradient. */
export function RecentCover({ className = "" }: { className?: string }) {
  return (
    <div
      className={`grid aspect-square shrink-0 place-items-center rounded-md bg-gradient-to-tr from-bg-deep to-accent/55 text-ink shadow-[0_30px_70px_-25px_rgb(0_0_0/0.75)] ring-1 ring-line ring-inset ${className}`}
    >
      <HistoryIcon size={64} />
    </div>
  );
}
