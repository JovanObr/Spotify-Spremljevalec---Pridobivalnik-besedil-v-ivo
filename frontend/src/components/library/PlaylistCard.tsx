import { Link } from "react-router";

import type { PlaylistSummary } from "../../api/types";
import { strings } from "../../lib/strings";
import { PlaylistCover } from "./PlaylistCover";

interface Props {
  playlist: PlaylistSummary;
  isPlaying: boolean;
  onPlay: () => void;
}

export function PlaylistCard({ playlist, isPlaying, onPlay }: Props) {
  const href = `/library/${playlist.id}`;
  const meta = playlist.is_owned
    ? playlist.track_count != null
      ? strings.library.songs(playlist.track_count)
      : null
    : strings.library.by(playlist.owner_name);

  return (
    <li className="group">
      <div className="relative">
        {/* Duplicate of the title link for mouse users; hidden from keyboard/AT */}
        <Link to={href} tabIndex={-1} aria-hidden="true" className="block">
          <PlaylistCover
            name={playlist.name}
            imageUrl={playlist.image_url}
            className="aspect-square w-full shadow-[0_18px_40px_-18px_rgb(0_0_0/0.7)]"
          />
        </Link>

        {/* Quick play, revealed on hover or keyboard focus */}
        <button
          type="button"
          onClick={onPlay}
          aria-label={strings.library.play(playlist.name)}
          className="absolute right-2.5 bottom-2.5 grid size-11 translate-y-1 cursor-pointer place-items-center rounded-full bg-accent text-bg-deep opacity-0 shadow-lg transition group-hover:translate-y-0 group-hover:opacity-100 focus-visible:translate-y-0 focus-visible:opacity-100 max-lg:translate-y-0 max-lg:opacity-100"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
            <path d="M8 5.5v13L19 12z" />
          </svg>
        </button>
      </div>

      <Link to={href} className="mt-3 block rounded-sm">
        <span
          className={`line-clamp-2 text-[0.95rem] leading-snug font-[600] ${isPlaying ? "text-accent" : "text-ink"}`}
        >
          {playlist.name}
        </span>
        <span className="mt-0.5 block truncate text-sm text-ink-faint">
          {isPlaying ? strings.library.playing : meta}
        </span>
      </Link>
    </li>
  );
}
