import { useEffect, useRef } from "react";

import { ApiError } from "../api/client";
import type { Lyrics, Track } from "../api/types";
import { useLyrics, useTranslation } from "../hooks/queries";
import { findActiveLine } from "../lib/format";
import { strings } from "../lib/strings";
import { TRANSLATION_LANGUAGES, useTranslationSettings } from "../lib/translation";

// Show each line slightly early: polling and rendering add a little delay.
const LYRICS_LEAD_MS = 300;
// After the user scrolls by hand, wait this long before following again.
const MANUAL_SCROLL_PAUSE_MS = 4000;

interface Props {
  track: Track;
  progressMs: number;
  onSeek: (positionMs: number) => void;
  /** Gemini is configured, so lyrics can be translated. */
  aiEnabled: boolean;
}

export function LyricsView({ track, progressMs, onSeek, aiEnabled }: Props) {
  const { data, isPending, isError } = useLyrics(track);
  const settings = useTranslationSettings();

  const lyrics = data?.lyrics;
  const translatable = aiEnabled && Boolean(lyrics) && !lyrics?.instrumental;
  const translation = useTranslation(
    track,
    translatable && settings.enabled ? settings.language : null,
  );
  const translated = translation.data?.lines ?? null;

  if (isPending) return <Message>{strings.lyrics.loading}</Message>;
  if (isError) return <Message>{strings.lyrics.error}</Message>;

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

  const toolbar = translatable && (
    <TranslationBar
      enabled={settings.enabled}
      language={settings.language}
      onToggle={() => settings.setEnabled(!settings.enabled)}
      onLanguage={settings.setLanguage}
      status={
        !settings.enabled
          ? null
          : translation.isFetching
            ? { text: strings.translation.loading(settings.language) }
            : translation.isError
              ? {
                  text:
                    translation.error instanceof ApiError && translation.error.status === 429
                      ? strings.translation.rateLimited
                      : strings.translation.error,
                  retry: () => translation.refetch(),
                }
              : null
      }
    />
  );

  const footer = (
    <>
      <Source name={lyrics.source} />
      {settings.enabled && translated && (
        <p className="mt-1 text-xs text-ink-faint">
          {strings.translation.disclaimer(settings.language)}
        </p>
      )}
    </>
  );

  return (
    <div className="flex h-full flex-col">
      {toolbar}
      <div className="min-h-0 flex-1">
        {lyrics.lines.length === 0 ? (
          <PlainLyrics lyrics={lyrics} translated={settings.enabled ? translated : null} footer={footer} />
        ) : (
          <SyncedLyrics
            key={track.id ?? track.title}
            lines={lyrics.lines}
            translated={settings.enabled ? translated : null}
            progressMs={progressMs + LYRICS_LEAD_MS}
            footer={footer}
            onSeek={onSeek}
          />
        )}
      </div>
    </div>
  );
}

function PlainLyrics({
  lyrics,
  translated,
  footer,
}: {
  lyrics: Lyrics;
  translated: string[] | null;
  footer: React.ReactNode;
}) {
  const lines = (lyrics.plain_lyrics ?? "").split("\n");

  return (
    <div className="h-full overflow-y-auto pr-4">
      <p className="mb-6 text-sm text-ink-faint">{strings.lyrics.unsynced}</p>
      {translated ? (
        <div className="space-y-1">
          {lines.map((line, index) =>
            line.trim() ? (
              <div key={index} className="py-1">
                <p className="text-2xl leading-snug font-[450] text-ink-soft">{line}</p>
                <Translated text={translated[index]} line={line} className="text-lg" />
              </div>
            ) : (
              <div key={index} className="h-6" aria-hidden="true" />
            ),
          )}
        </div>
      ) : (
        <p className="text-2xl leading-relaxed font-[450] whitespace-pre-line text-ink-soft">
          {lyrics.plain_lyrics}
        </p>
      )}
      {footer}
    </div>
  );
}

/** A translated line, hidden when it just repeats the original. */
function Translated({ text, line, className }: { text?: string; line: string; className: string }) {
  if (!text || text.trim().toLowerCase() === line.trim().toLowerCase()) return null;
  return (
    <span className={`mt-1 block font-[420] leading-snug tracking-normal text-ink-faint ${className}`}>
      {text}
    </span>
  );
}

function TranslationBar({
  enabled,
  language,
  onToggle,
  onLanguage,
  status,
}: {
  enabled: boolean;
  language: string;
  onToggle: () => void;
  onLanguage: (language: string) => void;
  status: { text: string; retry?: () => void } | null;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 pb-2 lg:pt-6">
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={enabled}
        className={[
          "flex h-9 cursor-pointer items-center gap-2 rounded-full px-3.5 text-sm transition-colors",
          enabled
            ? "bg-accent text-bg-deep hover:opacity-90"
            : "text-ink-soft ring-1 ring-line hover:bg-line hover:text-ink",
        ].join(" ")}
      >
        <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 5h9M8.5 3v2M6 5c.6 3.4 2.9 6 6 7.5M11 5c-.8 3.7-3.3 6.6-7 8M13 21l4-9 4 9M14.4 18h5.2" />
        </svg>
        {enabled ? strings.translation.hide : strings.translation.show}
      </button>

      {enabled && (
        <label className="relative flex h-9 items-center">
          <span className="sr-only">{strings.translation.language}</span>
          <select
            value={language}
            onChange={(event) => onLanguage(event.target.value)}
            className="h-9 cursor-pointer appearance-none rounded-full bg-transparent pr-8 pl-3.5 text-sm text-ink ring-1 ring-line transition-colors hover:bg-line [&>option]:bg-bg-deep [&>option]:text-ink"
          >
            {TRANSLATION_LANGUAGES.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" className="pointer-events-none absolute right-3 text-ink-soft" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </label>
      )}

      {status && (
        <p className="text-sm text-ink-faint" aria-live="polite">
          {status.text}
          {status.retry && (
            <button
              type="button"
              onClick={status.retry}
              className="ml-2 cursor-pointer text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent"
            >
              {strings.translation.retry}
            </button>
          )}
        </p>
      )}
    </div>
  );
}

function SyncedLyrics({
  lines,
  translated,
  progressMs,
  footer,
  onSeek,
}: {
  lines: { time_ms: number; text: string }[];
  translated: string[] | null;
  progressMs: number;
  footer: React.ReactNode;
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
  }, [active, translated]);

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
              {translated && line.text && (
                <Translated
                  text={translated[index]}
                  line={line.text}
                  className="text-[0.55em] [font-variation-settings:'wght'_430]"
                />
              )}
            </p>
          );
        })}
        {footer}
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
