import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { SourceStatus } from "../../api/types";
import { useSources } from "../../hooks/queries";
import { timeAgo } from "../../lib/format";
import { strings } from "../../lib/strings";
import { usePlayback } from "../../playback/PlaybackProvider";

// Which cached queries in the browser depend on each source
const QUERIES: Record<string, string[][]> = {
  spotify: [["now-playing"], ["playlists"], ["liked-tracks"], ["recently-played"]],
  lrclib: [["lyrics"]],
  lyrics_ovh: [["lyrics"]],
  wikipedia: [["details"]],
  countryinfo: [["details"]],
  sistat: [["stats"]],
};

/** Every outside source: technology, refresh schedule, status, and "fetch again". */
export function SourcesPanel() {
  const { data, isPending, isError } = useSources();

  if (isPending) return null;
  if (isError) return <p className="text-ink-soft">The source list couldn't be loaded.</p>;

  return (
    <div>
      <p className="max-w-2xl text-ink-soft">{strings.sources.intro}</p>

      <ul className="mt-6 grid gap-3 md:grid-cols-2">
        {data.sources.map((source) => (
          <SourceCard key={source.id} source={source} />
        ))}
      </ul>

      <h2 className="mt-10 text-base font-[600] text-ink">{strings.sources.delivery}</h2>
      <ul className="mt-3 grid gap-3 md:grid-cols-2">
        {data.delivery.map((item) => (
          <li key={item.id} className="rounded-xl border border-line p-4">
            <div className="flex items-baseline justify-between gap-3">
              <p className="font-[600] text-ink">{item.name}</p>
              <Technology name={item.technology} />
            </div>
            <p className="mt-2 text-sm text-ink-soft">{item.description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SourceCard({ source }: { source: SourceStatus }) {
  const queryClient = useQueryClient();
  const { notify } = usePlayback();

  const refresh = useMutation({
    mutationFn: () => api.refreshSource(source.id),
    onSuccess: () => {
      for (const key of QUERIES[source.id] ?? []) queryClient.invalidateQueries({ queryKey: key });
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      notify(strings.sources.refreshed(source.name));
    },
  });

  const dot = { ok: "bg-[#0ca30c]", error: "bg-[#e66767]", unused: "bg-ink-faint" }[source.state];

  return (
    <li className="flex flex-col rounded-xl border border-line p-4">
      <div className="flex items-baseline justify-between gap-3">
        <a href={source.url} target="_blank" rel="noreferrer" className="font-[600] text-ink hover:underline">
          {source.name}
        </a>
        <Technology name={source.technology} />
      </div>
      <p className="mt-1 text-xs text-ink-faint">{source.format}</p>

      <dl className="mt-3 grid grid-cols-[6.5rem_1fr] gap-x-3 gap-y-1.5 text-sm">
        <dt className="text-ink-faint">{strings.sources.provides}</dt>
        <dd className="text-ink-soft">{source.provides}</dd>
        <dt className="text-ink-faint">{strings.sources.refresh}</dt>
        <dd className="text-ink-soft">{source.refresh}</dd>
        <dt className="text-ink-faint">{strings.sources.lastFetched}</dt>
        <dd className="text-ink-soft">
          {source.last_success ? timeAgo(source.last_success) : strings.sources.never}
          {source.requests_this_run > 0 && (
            <span className="block text-xs text-ink-faint">{strings.sources.requests(source.requests_this_run)}</span>
          )}
        </dd>
      </dl>

      <div className="mt-auto flex items-center gap-2 pt-4 text-sm">
        {/* Status: a dot plus words, never colour alone */}
        <span className={`size-2 rounded-full ${dot}`} aria-hidden="true" />
        <span className="text-ink-soft">{strings.sources.state[source.state]}</span>
        {source.refreshable ? (
          <button
            type="button"
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="ml-auto h-8 cursor-pointer rounded-full px-3 text-sm text-ink ring-1 ring-line transition-colors hover:bg-line disabled:opacity-50"
          >
            {refresh.isPending ? strings.sources.refreshing : strings.sources.refreshNow}
          </button>
        ) : (
          <span className="ml-auto text-xs text-ink-faint">{strings.sources.quota}</span>
        )}
      </div>
      {source.state === "error" && source.last_error && (
        <p className="mt-2 text-xs break-words text-ink-faint">{source.last_error}</p>
      )}
    </li>
  );
}

function Technology({ name }: { name: string }) {
  return (
    <span className="shrink-0 rounded-full bg-line px-2.5 py-0.5 text-xs font-[600] text-ink-soft">{name}</span>
  );
}
