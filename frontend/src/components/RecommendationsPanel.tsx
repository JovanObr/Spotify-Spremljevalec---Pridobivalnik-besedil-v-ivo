import { ApiError } from "../api/client";
import type { Recommendation, Track } from "../api/types";
import { useRecommendations } from "../hooks/queries";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";

interface Props {
  track: Track;
  /** MusicAtlas or the AI is configured. */
  enabled: boolean;
}

/** "If you like this": three songs (MusicAtlas, or AI checked on Spotify). */
export function RecommendationsPanel({ track, enabled }: Props) {
  const { data, isPending, isError, error, refetch, isFetching } = useRecommendations(
    track,
    enabled,
  );

  // Nothing configured: the facts panel already explains how to enable AI
  if (!enabled) return null;

  return (
    <section aria-labelledby="recs-heading" className="border-t border-line pt-5">
      <h2 id="recs-heading" className="text-base font-[600] text-ink">
        {strings.recommendations.heading}
      </h2>

      {isPending || (isFetching && !data) ? (
        <>
          <p className="sr-only" aria-live="polite">
            {strings.recommendations.loading}
          </p>
          <ul className="mt-3 space-y-1" aria-hidden="true">
            {[0, 1, 2].map((row) => (
              <li key={row} className="flex items-center gap-3 py-2">
                <div className="size-11 shrink-0 rounded bg-line" />
                <div className="flex-1">
                  <div className="h-3.5 w-2/3 rounded bg-line" />
                  <div className="mt-2 h-3 w-1/3 rounded bg-line" />
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-1 text-sm text-ink-faint">{strings.recommendations.loading}</p>
        </>
      ) : isError ? (
        <div className="mt-2 text-sm text-ink-soft">
          <p>
            {error instanceof ApiError && error.status === 429
              ? strings.recommendations.rateLimited
              : strings.recommendations.error}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-2 cursor-pointer text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent"
          >
            {strings.recommendations.retry}
          </button>
        </div>
      ) : data.items.length === 0 ? (
        <p className="mt-2 text-sm text-ink-faint">{strings.recommendations.empty}</p>
      ) : (
        <>
          {data.tags.length > 0 && (
            <p className="mt-1.5 text-sm text-ink-faint">
              {data.tags.slice(0, 4).map((tag) => `#${tag}`).join("  ")}
            </p>
          )}
          <ul className="mt-2 -mx-2">
            {data.items.map((recommendation) => (
              <RecommendationRow
                key={recommendation.track.uri ?? recommendation.track.title}
                recommendation={recommendation}
              />
            ))}
          </ul>
          <p className="mt-2 text-xs text-ink-faint">
            {data.source === "ai"
              ? strings.recommendations.disclaimer.ai
              : data.items.some((item) => item.reason)
                ? strings.recommendations.disclaimer.musicatlas
                : strings.recommendations.disclaimer.musicatlasNoReasons}
          </p>
        </>
      )}
    </section>
  );
}

function RecommendationRow({ recommendation }: { recommendation: Recommendation }) {
  const { playSong, addToQueue, isBusy } = usePlayback();
  const { track, reason } = recommendation;
  const uri = track.uri;

  return (
    <li className="group flex gap-3 rounded-md p-2 transition-colors hover:bg-line">
      <div className="size-11 shrink-0 overflow-hidden rounded bg-line">
        {track.thumbnail_url && (
          <img src={track.thumbnail_url} alt="" loading="lazy" className="h-full w-full object-cover" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-[0.95rem] font-[600] text-ink">{track.title}</p>
        <p className="truncate text-sm text-ink-soft">{track.artist}</p>
        {reason && <p className="mt-1 text-sm leading-snug text-ink-faint">{reason}</p>}
      </div>

      {uri && (
        <div className="flex shrink-0 items-start gap-0.5">
          <IconButton
            label={strings.recommendations.playNow(track.title)}
            disabled={isBusy}
            onClick={() => playSong(track)}
            path="M8 5.5v13L19 12z"
            filled
          />
          <IconButton
            label={strings.recommendations.addToQueue(track.title)}
            disabled={isBusy}
            onClick={() => addToQueue(uri, track.title)}
            path="M4 7h11M4 12h11M4 17h7M17 14v6M14 17h6"
          />
        </div>
      )}
    </li>
  );
}

function IconButton({
  label,
  onClick,
  disabled,
  path,
  filled = false,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  path: string;
  filled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className="grid size-9 cursor-pointer place-items-center rounded-full text-ink-soft transition-colors hover:bg-accent hover:text-bg-deep disabled:cursor-default disabled:opacity-40"
    >
      <svg
        viewBox="0 0 24 24"
        width="18"
        height="18"
        aria-hidden="true"
        fill={filled ? "currentColor" : "none"}
        stroke={filled ? "none" : "currentColor"}
        strokeWidth={1.9}
        strokeLinecap="round"
      >
        <path d={path} />
      </svg>
    </button>
  );
}
