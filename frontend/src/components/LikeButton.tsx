import type { Track } from "../api/types";
import { useLike } from "../hooks/useLike";
import { strings } from "../lib/strings";
import { HeartIcon } from "./icons";

export function LikeButton({ track, size = 20 }: { track: Track; size?: number }) {
  const { isLiked, isReady, toggle } = useLike(track);

  if (!track.uri) return null;

  const label = isLiked ? strings.like.unlike(track.title) : strings.like.like(track.title);

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={!isReady}
      aria-pressed={isLiked}
      aria-label={label}
      title={label}
      className={`grid size-10 shrink-0 cursor-pointer place-items-center rounded-full transition-colors hover:bg-line disabled:cursor-default disabled:opacity-40 ${
        isLiked ? "text-accent" : "text-ink-soft hover:text-ink"
      }`}
    >
      <HeartIcon size={size} filled={isLiked} />
    </button>
  );
}
