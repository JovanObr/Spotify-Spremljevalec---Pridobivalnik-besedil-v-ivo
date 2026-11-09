import { ApiError } from "../api/client";
import type { Track } from "../api/types";
import { useFacts } from "../hooks/queries";
import { strings } from "../lib/strings";

interface Props {
  track: Track;
  aiEnabled: boolean;
}

export function FactsPanel({ track, aiEnabled }: Props) {
  const { data, isPending, isError, error, refetch, isFetching } = useFacts(track, aiEnabled);

  return (
    <section aria-labelledby="facts-heading" className="border-t border-line pt-5">
      <h2 id="facts-heading" className="text-base font-[600] text-ink">
        {strings.facts.heading}
      </h2>

      {!aiEnabled ? (
        <p className="mt-2 text-sm text-ink-faint">{strings.facts.disabled}</p>
      ) : isPending || isFetching ? (
        <p className="mt-2 text-sm text-ink-faint" aria-live="polite">
          {strings.facts.loading}
        </p>
      ) : isError ? (
        <div className="mt-2 text-sm text-ink-soft">
          <p>
            {error instanceof ApiError && error.status === 429
              ? strings.facts.rateLimited
              : strings.facts.error}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-2 cursor-pointer text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent"
          >
            {strings.facts.retry}
          </button>
        </div>
      ) : (
        <>
          <ul className="mt-3 space-y-3">
            {data.facts.map((fact) => (
              <li
                key={fact}
                className="border-l-2 border-accent/50 pl-3 text-[0.95rem] leading-relaxed text-ink-soft"
              >
                {fact}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-faint">{strings.facts.disclaimer}</p>
        </>
      )}
    </section>
  );
}
