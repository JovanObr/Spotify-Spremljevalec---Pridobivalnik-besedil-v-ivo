import { Link } from "react-router";

import type { PlaylistSummary } from "../api/types";
import { PlaylistCard } from "../components/library/PlaylistCard";
import { useDisconnect } from "../hooks/useDisconnect";
import { useLikedTracks, usePlaylists } from "../hooks/queries";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";
import { LikedCover } from "./LikedView";

export function LibraryView() {
  const disconnect = useDisconnect();
  const { data: playlists, isPending, isError, refetch } = usePlaylists();

  const yours = playlists?.filter((playlist) => playlist.is_owned) ?? [];
  const following = playlists?.filter((playlist) => !playlist.is_owned) ?? [];

  return (
    <div className="mx-auto max-w-[90rem] px-6 py-10 lg:px-12 lg:py-14">
      <h1 className="text-[clamp(2.2rem,4vw,3.25rem)] leading-none font-[720] tracking-[-0.03em] [font-stretch:88%]">
        {strings.library.title}
      </h1>

      {isPending ? (
        <SkeletonGrid />
      ) : isError ? (
        <div className="mt-6 text-ink-soft">
          <p>{strings.library.error}</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-2 cursor-pointer text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent"
          >
            {strings.library.retry}
          </button>
        </div>
      ) : (
        <>
          <Section title={strings.library.yours} playlists={yours} leading={<LikedCard />} />
          <Section title={strings.library.following} playlists={following} />
          {playlists.length === 0 && (
            <p className="mt-6 max-w-lg text-ink-soft">{strings.library.empty}</p>
          )}
        </>
      )}

      <button
        type="button"
        onClick={disconnect}
        className="mt-16 cursor-pointer text-sm text-ink-faint underline-offset-4 hover:text-ink hover:underline lg:hidden"
      >
        {strings.playback.disconnect}
      </button>
    </div>
  );
}

const GRID = "grid grid-cols-[repeat(auto-fill,minmax(9.5rem,1fr))] gap-x-6 gap-y-9 sm:grid-cols-[repeat(auto-fill,minmax(11rem,1fr))]";

function Section({
  title,
  playlists,
  leading,
}: {
  title: string;
  playlists: PlaylistSummary[];
  /** An extra first tile (Liked Songs). */
  leading?: React.ReactNode;
}) {
  const { playback, playContext } = usePlayback();
  if (playlists.length === 0 && !leading) return null;

  return (
    <section className="mt-10 first-of-type:mt-8">
      <h2 className="mb-5 text-xl font-[650] text-ink-soft">{title}</h2>
      <ul className={GRID}>
        {leading}
        {playlists.map((playlist) => (
          <PlaylistCard
            key={playlist.id}
            playlist={playlist}
            isPlaying={playback?.context_uri === playlist.uri}
            onPlay={() => playContext(playlist.uri)}
          />
        ))}
      </ul>
    </section>
  );
}

function SkeletonGrid() {
  return (
    <ul className={`${GRID} mt-8`} aria-hidden="true">
      {Array.from({ length: 10 }, (_, index) => (
        <li key={index}>
          <div className="aspect-square rounded-md bg-line" />
          <div className="mt-3 h-4 w-3/4 rounded bg-line" />
          <div className="mt-2 h-3 w-1/2 rounded bg-line" />
        </li>
      ))}
    </ul>
  );
}

function LikedCard() {
  const liked = useLikedTracks();
  const total = liked.data?.pages[0]?.total;

  return (
    <li>
      <Link to="/library/liked" className="block rounded-md">
        <LikedCover className="w-full" />
        <span className="mt-3 block text-[0.95rem] leading-snug font-[600] text-ink">
          {strings.liked.title}
        </span>
        <span className="mt-0.5 block text-sm text-ink-faint">
          {total != null ? strings.library.songs(total) : "\u00a0"}
        </span>
      </Link>
    </li>
  );
}
