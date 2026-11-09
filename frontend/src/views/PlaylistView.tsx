import { useEffect, useRef } from "react";
import { Link, useParams } from "react-router";

import { ApiError } from "../api/client";
import type { PlaylistDetail } from "../api/types";
import { PlaylistCover } from "../components/library/PlaylistCover";
import { TRACK_GRID, TrackRow } from "../components/library/TrackRow";
import { usePlaylist, usePlaylistItems } from "../hooks/queries";
import { formatTotalDuration } from "../lib/format";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";

export function PlaylistView() {
  const { playlistId = "" } = useParams();
  const { data: playlist, isPending, error } = usePlaylist(playlistId);

  return (
    <div className="mx-auto max-w-[90rem] px-6 py-8 lg:px-12 lg:py-10">
      <Link
        to="/library"
        className="inline-flex items-center gap-1.5 text-sm text-ink-faint hover:text-ink"
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m15 6-6 6 6 6" />
        </svg>
        {strings.playlist.back}
      </Link>

      {isPending ? (
        <HeaderSkeleton />
      ) : error ? (
        <p className="mt-10 max-w-lg text-lg text-ink-soft">
          {error instanceof ApiError && error.status === 404
            ? strings.playlist.notFound
            : strings.playlist.error}
        </p>
      ) : (
        <PlaylistContent playlist={playlist} />
      )}
    </div>
  );
}

function PlaylistContent({ playlist }: { playlist: PlaylistDetail }) {
  const { playback, playContext, togglePlay, isBusy } = usePlayback();
  const items = usePlaylistItems(playlist.id, playlist.snapshot_id, playlist.items_available);

  const rows = items.data?.pages.flatMap((page) => page.items) ?? [];
  const isThisPlaying = playback?.context_uri === playlist.uri;
  const currentUri = playback?.track.uri;

  const totalMs =
    items.data && !items.hasNextPage
      ? rows.reduce((sum, row) => sum + (row.track.duration_ms ?? 0), 0)
      : null;

  const count = playlist.track_count ?? (items.data ? rows.length : null);
  const details = [
    count != null ? strings.library.songs(count) : null,
    totalMs ? formatTotalDuration(totalMs) : null,
  ]
    .filter(Boolean)
    .join(", ");

  // Load the next page when the end of the list scrolls into view
  const sentinel = useRef<HTMLDivElement>(null);
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = items;
  useEffect(() => {
    const element = sentinel.current;
    if (!element || !hasNextPage) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetchingNextPage) fetchNextPage();
      },
      { rootMargin: "600px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const onMainButton = () => (isThisPlaying ? togglePlay() : playContext(playlist.uri));
  const mainLabel = isThisPlaying && playback?.is_playing ? strings.playlist.pause : strings.playlist.play;

  return (
    <>
      <header className="mt-6 flex flex-col gap-6 sm:flex-row sm:items-end sm:gap-8">
        <PlaylistCover
          name={playlist.name}
          imageUrl={playlist.image_url}
          className="aspect-square w-44 shrink-0 shadow-[0_30px_70px_-25px_rgb(0_0_0/0.75)] lg:w-56"
        />
        <div className="min-w-0">
          <h1 className="text-[clamp(2.2rem,5vw,4rem)] leading-[1] font-[720] tracking-[-0.03em] text-balance [font-stretch:88%]">
            {playlist.name}
          </h1>
          {playlist.description && (
            <p className="mt-3 line-clamp-2 max-w-2xl text-ink-soft">{playlist.description}</p>
          )}
          <p className="mt-3 text-sm text-ink-soft">{strings.library.by(playlist.owner_name)}</p>
          {details && <p className="mt-0.5 text-sm text-ink-faint">{details}</p>}
          <button
            type="button"
            onClick={onMainButton}
            disabled={isBusy}
            className="mt-6 inline-flex cursor-pointer items-center gap-2 rounded-full bg-accent py-2.5 pr-6 pl-5 font-[650] text-bg-deep transition-transform hover:scale-[1.03] active:scale-[0.98] disabled:opacity-60"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
              <path d={mainLabel === strings.playlist.pause ? "M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" : "M8 5.5v13L19 12z"} />
            </svg>
            {mainLabel}
          </button>
        </div>
      </header>

      {!playlist.items_available ? (
        <p className="mt-10 max-w-xl border-l-2 border-accent/50 pl-4 text-ink-soft">
          {strings.playlist.notShared}
        </p>
      ) : items.isError ? (
        <p className="mt-10 text-ink-soft">{strings.playlist.error}</p>
      ) : (
        <section className="mt-10" aria-label={playlist.name}>
          <div className={`${TRACK_GRID} border-b border-line px-3 pb-2 text-sm text-ink-faint`} aria-hidden="true">
            <span className="text-right">#</span>
            <span>{strings.playlist.columns.title}</span>
            <span className="max-md:hidden">{strings.playlist.columns.album}</span>
            <span className="text-right">{strings.playlist.columns.duration}</span>
            <span />
          </div>

          <ol className="mt-2">
            {rows.map((row) => {
              const isCurrent = Boolean(currentUri) && row.track.uri === currentUri;
              return (
                <TrackRow
                  key={`${row.position}-${row.track.uri}`}
                  track={row.track}
                  number={row.position + 1}
                  isCurrent={isCurrent}
                  isPlaying={isCurrent && Boolean(playback?.is_playing)}
                  onPlay={() => playContext(playlist.uri, row.track.uri)}
                />
              );
            })}
          </ol>

          {items.isPending && <RowsSkeleton />}
          <div ref={sentinel} />
          {isFetchingNextPage && (
            <p className="mt-4 px-3 text-sm text-ink-faint" aria-live="polite">
              {strings.playlist.loadingMore}
            </p>
          )}
        </section>
      )}
    </>
  );
}

function HeaderSkeleton() {
  return (
    <div className="mt-6 flex flex-col gap-6 sm:flex-row sm:items-end sm:gap-8" aria-hidden="true">
      <div className="aspect-square w-44 rounded-md bg-line lg:w-56" />
      <div className="flex-1">
        <div className="h-12 w-2/3 max-w-md rounded bg-line" />
        <div className="mt-4 h-4 w-1/3 max-w-xs rounded bg-line" />
      </div>
    </div>
  );
}

function RowsSkeleton() {
  return (
    <ul className="mt-2" aria-hidden="true">
      {Array.from({ length: 8 }, (_, index) => (
        <li key={index} className="flex items-center gap-3 px-3 py-2">
          <div className="ml-auto h-3 w-4 rounded bg-line md:w-5" />
          <div className="size-10 rounded bg-line" />
          <div className="flex-1">
            <div className="h-3.5 w-1/3 rounded bg-line" />
            <div className="mt-2 h-3 w-1/5 rounded bg-line" />
          </div>
        </li>
      ))}
    </ul>
  );
}
