import { TrackRow } from "../components/library/TrackRow";
import { useQueue } from "../hooks/queries";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";

export function QueueView() {
  const { playback, playSong } = usePlayback();
  const currentUri = playback?.track.uri;
  const { data, isPending, isError } = useQueue(currentUri);

  return (
    <div className="mx-auto max-w-[90rem] px-6 py-10 lg:px-12 lg:py-14">
      <h1 className="text-[clamp(2.2rem,4vw,3.25rem)] leading-none font-[720] tracking-[-0.03em] [font-stretch:88%]">
        {strings.queue.title}
      </h1>

      {!playback ? (
        <p className="mt-6 text-lg text-ink-soft">{strings.queue.nothingPlaying}</p>
      ) : isPending ? null : isError ? (
        <p className="mt-6 text-lg text-ink-soft">{strings.queue.error}</p>
      ) : (
        <>
          <section className="mt-10">
            <h2 className="mb-3 text-xl font-[650] text-ink-soft">{strings.queue.nowPlaying}</h2>
            <ol className="-mx-3">
              <TrackRow
                track={data.current ?? playback.track}
                number={1}
                isCurrent
                isPlaying={playback.is_playing}
                onPlay={() => {}}
              />
            </ol>
          </section>

          <section className="mt-10">
            <h2 className="mb-3 text-xl font-[650] text-ink-soft">{strings.queue.next}</h2>
            {data.next.length === 0 ? (
              <p className="text-ink-soft">{strings.queue.empty}</p>
            ) : (
              <ol className="-mx-3">
                {data.next.map((track, index) => (
                  <TrackRow
                    key={`${index}-${track.uri}`}
                    track={track}
                    number={index + 1}
                    isCurrent={false}
                    isPlaying={false}
                    onPlay={() => playSong(track)}
                  />
                ))}
              </ol>
            )}
          </section>
        </>
      )}
    </div>
  );
}
