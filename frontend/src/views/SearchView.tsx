import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import type { AlbumResult, ArtistResult } from "../api/types";
import { SearchIcon } from "../components/icons";
import { PlaylistCard } from "../components/library/PlaylistCard";
import { TrackRow } from "../components/library/TrackRow";
import { useSearch } from "../hooks/queries";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";

const DEBOUNCE_MS = 300;

export function SearchView() {
  // The query lives in the URL (?q=…), so Back returns to the same results
  const [params, setParams] = useSearchParams();
  const [text, setText] = useState(params.get("q") ?? "");
  const [query, setQuery] = useState(text);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery(text);
      setParams(text.trim() ? { q: text } : {}, { replace: true });
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [text, setParams]);

  const { data, isPending, isError, isFetching } = useSearch(query);
  const trimmed = query.trim();

  const empty =
    data &&
    !data.tracks.length &&
    !data.artists.length &&
    !data.albums.length &&
    !data.playlists.length;

  return (
    <div className="mx-auto max-w-[90rem] px-6 py-10 lg:px-12 lg:py-14">
      <label className="flex items-center gap-4 border-b-2 border-line pb-3 focus-within:border-accent">
        <span className="text-ink-faint">
          <SearchIcon size={30} />
        </span>
        <span className="sr-only">{strings.search.label}</span>
        <input
          type="text"
          role="searchbox"
          enterKeyHint="search"
          autoComplete="off"
          spellCheck={false}
          autoFocus
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={strings.search.placeholder}
          className="w-full bg-transparent text-[clamp(1.6rem,3.5vw,2.75rem)] font-[650] tracking-[-0.02em] text-ink outline-none placeholder:text-ink-faint focus-visible:outline-none [font-stretch:92%]"
        />
      </label>

      <div className={`transition-opacity ${isFetching && data ? "opacity-60" : ""}`}>
        {!trimmed ? (
          <p className="mt-8 text-lg text-ink-soft">{strings.search.hint}</p>
        ) : isError ? (
          <p className="mt-8 text-lg text-ink-soft">{strings.search.error}</p>
        ) : isPending ? null : empty ? (
          <p className="mt-8 text-lg text-ink-soft">{strings.search.noResults(trimmed)}</p>
        ) : (
          <Results data={data!} />
        )}
      </div>
    </div>
  );
}

function Results({ data }: { data: NonNullable<ReturnType<typeof useSearch>["data"]> }) {
  const { playback, playSong, playContext } = usePlayback();
  const currentUri = playback?.track.uri;

  return (
    <>
      {data.tracks.length > 0 && (
        <Section title={strings.search.songs}>
          <ol className="-mx-3">
            {data.tracks.map((track, index) => (
              <TrackRow
                key={track.uri ?? index}
                track={track}
                number={index + 1}
                isCurrent={Boolean(currentUri) && track.uri === currentUri}
                isPlaying={Boolean(playback?.is_playing)}
                onPlay={() => playSong(track)}
              />
            ))}
          </ol>
        </Section>
      )}

      {data.artists.length > 0 && (
        <Section title={strings.search.artists}>
          <ul className="-mx-6 flex gap-6 overflow-x-auto px-6 pb-2 lg:-mx-12 lg:px-12">
            {data.artists.map((artist) => (
              <ArtistTile key={artist.uri} artist={artist} onPlay={() => playContext(artist.uri)} />
            ))}
          </ul>
        </Section>
      )}

      {data.albums.length > 0 && (
        <Section title={strings.search.albums}>
          <ul className={GRID}>
            {data.albums.map((album) => (
              <AlbumTile
                key={album.uri}
                album={album}
                isPlaying={playback?.context_uri === album.uri}
                onPlay={() => playContext(album.uri)}
              />
            ))}
          </ul>
        </Section>
      )}

      {data.playlists.length > 0 && (
        <Section title={strings.search.playlists}>
          <ul className={GRID}>
            {data.playlists.map((playlist) => (
              <PlaylistCard
                key={playlist.id}
                playlist={playlist}
                isPlaying={playback?.context_uri === playlist.uri}
                onPlay={() => playContext(playlist.uri)}
              />
            ))}
          </ul>
        </Section>
      )}
    </>
  );
}

const GRID =
  "grid grid-cols-[repeat(auto-fill,minmax(9.5rem,1fr))] gap-x-6 gap-y-9 sm:grid-cols-[repeat(auto-fill,minmax(11rem,1fr))]";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="mb-4 text-xl font-[650] text-ink-soft">{title}</h2>
      {children}
    </section>
  );
}

function ArtistTile({ artist, onPlay }: { artist: ArtistResult; onPlay: () => void }) {
  return (
    <li className="w-32 shrink-0">
      <button
        type="button"
        onClick={onPlay}
        aria-label={strings.search.playArtist(artist.name)}
        title={strings.search.playArtist(artist.name)}
        className="group block w-full cursor-pointer text-center"
      >
        <span className="block aspect-square overflow-hidden rounded-full bg-line shadow-[0_18px_40px_-18px_rgb(0_0_0/0.7)] transition-transform group-hover:scale-[1.03]">
          {artist.image_url && (
            <img src={artist.image_url} alt="" loading="lazy" className="h-full w-full object-cover" />
          )}
        </span>
        <span className="mt-3 block truncate font-[600] text-ink group-hover:text-accent">
          {artist.name}
        </span>
      </button>
    </li>
  );
}

function AlbumTile({
  album,
  isPlaying,
  onPlay,
}: {
  album: AlbumResult;
  isPlaying: boolean;
  onPlay: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onPlay}
        aria-label={strings.search.playAlbum(album.name)}
        title={strings.search.playAlbum(album.name)}
        className="group block w-full cursor-pointer text-left"
      >
        <span className="relative block aspect-square overflow-hidden rounded-md bg-line shadow-[0_18px_40px_-18px_rgb(0_0_0/0.7)]">
          {album.image_url && (
            <img src={album.image_url} alt="" loading="lazy" className="h-full w-full object-cover" />
          )}
          <span className="absolute right-2.5 bottom-2.5 grid size-11 translate-y-1 place-items-center rounded-full bg-accent text-bg-deep opacity-0 shadow-lg transition group-hover:translate-y-0 group-hover:opacity-100 group-focus-visible:opacity-100 max-lg:translate-y-0 max-lg:opacity-100">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
              <path d="M8 5.5v13L19 12z" />
            </svg>
          </span>
        </span>
        <span className={`mt-3 line-clamp-2 text-[0.95rem] leading-snug font-[600] ${isPlaying ? "text-accent" : "text-ink"}`}>
          {album.name}
        </span>
        <span className="mt-0.5 block truncate text-sm text-ink-faint">
          {[album.artist, album.year].filter(Boolean).join(", ")}
        </span>
      </button>
    </li>
  );
}
