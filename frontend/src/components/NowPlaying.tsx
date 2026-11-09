import type { ReactNode } from "react";

import type { Playback } from "../api/types";
import { strings } from "../lib/strings";
import { LikeButton } from "./LikeButton";
import { SeekBar } from "./SeekBar";

interface Props {
  playback: Playback;
  progressMs: number;
  controls: ReactNode;
  /** Devices, volume, queue link: shown under the controls. */
  extras?: ReactNode;
  onSeek: (positionMs: number) => void;
}

export function NowPlaying({ playback, progressMs, controls, extras, onSeek }: Props) {
  const { track, is_playing } = playback;

  return (
    <section
      aria-label="Now playing"
      className="grid grid-cols-[6.5rem_minmax(0,1fr)] items-center gap-x-4 gap-y-4 lg:flex lg:flex-col lg:items-stretch lg:gap-5"
    >
      <div className="relative aspect-square w-full max-w-[22rem] overflow-hidden rounded-md bg-line shadow-[0_30px_80px_-20px_rgb(0_0_0/0.6)]">
        {track.artwork_url ? (
          <img
            key={track.artwork_url}
            src={track.artwork_url}
            alt={`Cover of ${track.album}`}
            className="h-full w-full object-cover"
          />
        ) : null}
        {!is_playing && (
          <span className="absolute inset-x-0 bottom-0 bg-bg-deep/75 px-3 py-1.5 text-sm text-ink-soft backdrop-blur max-lg:text-xs">
            {strings.playback.paused}
          </span>
        )}
      </div>

      <div className="flex min-w-0 items-start gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-[2rem] leading-[1.05] font-[650] tracking-[-0.02em] text-balance [font-stretch:92%] max-lg:text-2xl">
            {track.title}
          </h1>
          <p className="mt-2 text-lg text-ink-soft max-lg:mt-1 max-lg:text-base">{track.artist}</p>
          <p className="mt-0.5 text-sm text-ink-faint">{track.album}</p>
        </div>
        <div className="-mt-1 -mr-2">
          <LikeButton track={track} size={22} />
        </div>
      </div>

      <SeekBar
        progressMs={progressMs}
        durationMs={track.duration_ms}
        onSeek={onSeek}
        className="w-full max-w-[22rem] max-lg:hidden"
      />

      <div className="col-span-2 flex flex-col gap-3 lg:gap-5">
        {controls}
        {extras}
      </div>
    </section>
  );
}
