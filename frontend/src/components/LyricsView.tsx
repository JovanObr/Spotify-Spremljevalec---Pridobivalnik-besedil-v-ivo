import { useEffect, useRef } from "react";

import type { Track } from "../api/types";
import { useLyrics } from "../hooks/queries";
import { findActiveLine } from "../lib/format";
import { strings } from "../lib/strings";

// Show each line slightly early: polling and rendering add a little delay.
const LYRICS_LEAD_MS = 300;
// After the user scrolls by hand, wait this long before following again.
const MANUAL_SCROLL_PAUSE_MS = 4000;

interface Props {
  track: Track;
  progressMs: number;
  onSeek: (positionMs: number) => void;
}

export function LyricsView({ track, progressMs, onSeek }: Props) {
  const { data, isPending, isError } = useLyrics(track);

  if (isPending) return <Message>{strings.lyrics.loading}</Message>;
  if (isError) return <Message>{strings.lyrics.error}</Message>;

  const lyrics = data.lyrics;
  if (!lyrics) {
    const query = encodeURIComponent(`${track.artists[0] ?? track.artist} ${track.title}`);
    return (
      <Message
        action={
          <a
            href={`https://genius.com/search?q=${query}`}
            target="_blank"
            rel="noreferrer"
            className="text-lg text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent"
          >
            {strings.lyrics.searchWeb}
          </a>
        }
      >
        {strings.lyrics.notFound}
      </Message>
    );
  }
  if (lyrics.instrumental) return <Message>{strings.lyrics.instrumental}</Message>;

  if (lyrics.lines.length === 0) {
    return (
      <div className="h-full overflow-y-auto pr-4">
        <p className="mb-6 text-sm text-ink-faint">{strings.lyrics.unsynced}</p>
        <p className="text-2xl leading-relaxed font-[450] whitespace-pre-line text-ink-soft">
          {lyrics.plain_lyrics}
        </p>
        <Source name={lyrics.source} />
      </div>
    );
  }

  return (
    <SyncedLyrics
      key={track.id ?? track.title}
      lines={lyrics.lines}
      progressMs={progressMs + LYRICS_LEAD_MS}
      source={lyrics.source}
      onSeek={onSeek}
    />
  );
}

function SyncedLyrics({
  lines,
  progressMs,
  source,
  onSeek,
}: {
  lines: { time_ms: number; text: string }[];
  progressMs: number;
  source: string;
  onSeek: (positionMs: number) => void;
}) {
  const active = findActiveLine(lines, progressMs);
  const scroller = useRef<HTMLDivElement>(null);
  const lineRefs = useRef<(HTMLParagraphElement | null)[]>([]);
  const lastManualScroll = useRef(0);

  useEffect(() => {
    const container = scroller.current;
    const line = lineRefs.current[Math.max(active, 0)];
    if (!container || !line) return;
    if (Date.now() - lastManualScroll.current < MANUAL_SCROLL_PAUSE_MS) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Keep the active line a little above the middle, where the eye rests
    const target = line.offsetTop - container.clientHeight * 0.38 + line.clientHeight / 2;

    container.scrollTo({ top: target, behavior: reduceMotion ? "auto" : "smooth" });
  }, [active]);

  const markManualScroll = () => {
    lastManualScroll.current = Date.now();
  };

  return (
    <div
      ref={scroller}
      onWheel={markManualScroll}
      onTouchMove={markManualScroll}
      className="lyrics-mask h-full overflow-y-auto pr-4 [scrollbar-width:none]"
    >
      <div className="py-[38vh]">
        {lines.map((line, index) => {
          const state = index === active ? "active" : index < active ? "past" : "future";
          return (
            <p
              key={`${line.time_ms}-${index}`}
              ref={(el) => {
                lineRefs.current[index] = el;
              }}
              aria-current={state === "active" ? "true" : undefined}
              onClick={() => {
                // Jump there and resume following the song right away
                lastManualScroll.current = 0;
                onSeek(line.time_ms);
              }}
              title={strings.playback.jumpToLine}
              className={[
                "lyric-line cursor-pointer py-2 text-[clamp(1.6rem,3.4vw,2.9rem)] leading-[1.12] tracking-[-0.015em] text-balance",
                state === "active" && "scale-100 text-accent [font-variation-settings:'wght'_760]",
                state === "past" && "scale-[0.94] text-ink-faint hover:text-ink-soft [font-variation-settings:'wght'_480]",
                state === "future" && "scale-[0.94] text-ink-soft hover:text-ink [font-variation-settings:'wght'_480]",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {line.text || <span aria-hidden="true">♪</span>}
            </p>
          );
        })}
        <Source name={source} />
      </div>
    </div>
  );
}

function Source({ name }: { name: string }) {
  return <p className="mt-10 text-xs text-ink-faint">{strings.lyrics.source(name)}</p>;
}

function Message({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex h-full flex-col items-start justify-center gap-5">
      <p className="max-w-md text-3xl leading-tight font-[550] text-ink-soft">{children}</p>
      {action}
    </div>
  );
}
