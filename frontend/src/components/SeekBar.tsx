import { useRangeInput } from "../hooks/useRangeInput";
import { formatDuration } from "../lib/format";

interface Props {
  progressMs: number;
  durationMs: number | null;
  onSeek: (positionMs: number) => void;
  /** Show elapsed/total times under the bar. */
  showTimes?: boolean;
  className?: string;
}

/**
 * Song progress that can be dragged, clicked or moved with the arrow keys.
 * Spotify is asked to seek once per drag or burst of key presses.
 */
export function SeekBar({ progressMs, durationMs, onSeek, showTimes = true, className = "" }: Props) {
  const duration = durationMs ?? 0;
  const range = useRangeInput(progressMs, onSeek);
  const value = Math.min(range.value, duration);
  const ratio = duration ? value / duration : 0;

  return (
    <div className={className}>
      <input
        type="range"
        className="seek-bar"
        min={0}
        max={duration || 1}
        step={1000}
        value={value}
        disabled={!duration}
        aria-label="Seek"
        aria-valuetext={`${formatDuration(value)} of ${formatDuration(duration)}`}
        style={{ "--ratio": ratio } as React.CSSProperties}
        {...range.inputProps}
      />
      {showTimes && (
        <div className="mt-1.5 flex justify-between text-xs text-ink-faint tabular-nums">
          <span>{formatDuration(value)}</span>
          <span>{formatDuration(durationMs)}</span>
        </div>
      )}
    </div>
  );
}
