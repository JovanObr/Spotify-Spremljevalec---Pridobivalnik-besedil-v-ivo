import { useEffect, useRef } from "react";
import { Link } from "react-router";

import { HeartIcon } from "../components/icons";
import { TRACK_GRID, TrackRow } from "../components/library/TrackRow";
import { useLikedTracks } from "../hooks/queries";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";

// Spotify plays at most 100 songs from a list we send
const PLAY_WINDOW = 100;

export function LikedView() {
  const { playback, playTracks, isBusy } = usePlayback();
  const liked = useLikedTracks();
  const rows = liked.data?.pages.flatMap((page) => page.items) ?? [];
  const total = liked.data?.pages[0]?.total ?? 0;
  const currentUri = playback?.track.uri;

  // Play from a song: that song and the ones after it
  const playFrom = (index: number) => {
    const uris = rows
      .slice(index, index + PLAY_WINDOW)
      .map((row) => row.track.uri)
      .filter((uri): uri is string => Boolean(uri));
    if (uris.length) playTracks(uris);
  };

  // Load more when the end of the list scrolls into view
  const sentinel = useRef<HTMLDivElement>(null);
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = liked;
  useEffect(() => {
    const element = sentinel.current;
    if (!element || !hasNextPage) return;
    const observer = new IntersectionObserver(
      (entries) => entries[0].isIntersecting && !isFetchingNextPage && fetchNextPage(),
      { rootMargin: "600px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  return (
    <div className="mx-auto max-w-[90rem] px-6 py-8 lg:px-12 lg:py-10">
      <Link to="/library" className="inline-flex items-center gap-1.5 text-sm text-ink-faint hover:text-ink">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m15 6-6 6 6 6" />
        </svg>
        {strings.playlist.back}
      </Link>

      <header className="mt-6 flex flex-col gap-6 sm:flex-row sm:items-end sm:gap-8">
        <LikedCover className="w-44 lg:w-56" />
        <div>
          <h1 className="text-[clamp(2.2rem,5vw,4rem)] leading-[1] font-[720] tracking-[-0.03em] [font-stretch:88%]">
            {strings.liked.title}
          </h1>
          {liked.data && <p className="mt-3 text-sm text-ink-faint">{strings.library.songs(total)}</p>}
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

      {liked.isError ? (
        <p className="mt-10 text-ink-soft">{strings.liked.error}</p>
      ) : liked.data && rows.length === 0 ? (
        <p className="mt-10 max-w-lg text-lg text-ink-soft">{strings.liked.empty}</p>
      ) : (
        <section className="mt-10" aria-label={strings.liked.title}>
          <div className={`${TRACK_GRID} border-b border-line px-3 pb-2 text-sm text-ink-faint`} aria-hidden="true">
            <span className="text-right">#</span>
            <span>{strings.playlist.columns.title}</span>
            <span className="max-md:hidden">{strings.playlist.columns.album}</span>
            <span className="text-right">{strings.playlist.columns.duration}</span>
            <span />
          </div>
          <ol className="mt-2">
            {rows.map((row, index) => {
              const isCurrent = Boolean(currentUri) && row.track.uri === currentUri;
              return (
                <TrackRow
                  key={`${row.position}-${row.track.uri}`}
                  track={row.track}
                  number={index + 1}
                  isCurrent={isCurrent}
                  isPlaying={isCurrent && Boolean(playback?.is_playing)}
                  onPlay={() => playFrom(index)}
                />
              );
            })}
          </ol>
          <div ref={sentinel} />
          {isFetchingNextPage && (
            <p className="mt-4 px-3 text-sm text-ink-faint" aria-live="polite">
              {strings.playlist.loadingMore}
            </p>
          )}
        </section>
      )}
    </div>
  );
}

/** The Liked Songs artwork: the album accent with a heart. */
export function LikedCover({ className = "" }: { className?: string }) {
  return (
    <div
      className={`grid aspect-square shrink-0 place-items-center rounded-md bg-gradient-to-br from-accent to-accent/25 text-bg-deep shadow-[0_30px_70px_-25px_rgb(0_0_0/0.75)] ${className}`}
    >
      <HeartIcon size={64} filled />
    </div>
  );
}
