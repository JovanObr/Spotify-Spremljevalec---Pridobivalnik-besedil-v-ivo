import { useState } from "react";

import { ApiError } from "../api/client";
import type { Track } from "../api/types";
import { useMeaning } from "../hooks/queries";
import { strings } from "../lib/strings";

interface Props {
  track: Track;
  aiEnabled: boolean;
}

/** "What's this song about": written on request, so it doesn't spend AI quota on every song. */
export function MeaningPanel({ track, aiEnabled }: Props) {
  const [asked, setAsked] = useState(false);
  const { data, isFetching, isError, error, refetch } = useMeaning(track, aiEnabled && asked);

  // Without a key the facts panel already explains how to enable AI
  if (!aiEnabled) return null;

  const linkButton =
    "cursor-pointer text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent";

  return (
    <section aria-labelledby="meaning-heading" className="border-t border-line pt-5">
      <h2 id="meaning-heading" className="text-base font-[600] text-ink">
        {strings.meaning.heading}
      </h2>

      {!asked && !data ? (
        <button
          type="button"
          onClick={() => setAsked(true)}
          className="mt-3 h-9 cursor-pointer rounded-full px-4 text-sm text-ink ring-1 ring-line transition-colors hover:bg-accent hover:text-bg-deep hover:ring-accent"
        >
          {strings.meaning.ask}
        </button>
      ) : isFetching && !data ? (
        <p className="mt-2 text-sm text-ink-faint" aria-live="polite">
          {strings.meaning.loading}
        </p>
      ) : isError ? (
        <div className="mt-2 text-sm text-ink-soft">
          <p>
            {error instanceof ApiError && error.status === 429
              ? strings.meaning.rateLimited
              : strings.meaning.error}
          </p>
          <button type="button" onClick={() => refetch()} className={`mt-2 ${linkButton}`}>
            {strings.meaning.retry}
          </button>
        </div>
      ) : data ? (
        <>
          <p className="mt-3 text-[0.95rem] leading-relaxed text-ink-soft">{data.summary}</p>
          {data.themes.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Themes">
              {data.themes.map((theme) => (
                <li key={theme} className="rounded-full bg-line px-2.5 py-1 text-xs text-ink-soft">
                  {theme}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-ink-faint">
            {data.based_on_lyrics ? strings.meaning.fromLyrics : strings.meaning.withoutLyrics}
          </p>
        </>
      ) : null}
    </section>
  );
}
