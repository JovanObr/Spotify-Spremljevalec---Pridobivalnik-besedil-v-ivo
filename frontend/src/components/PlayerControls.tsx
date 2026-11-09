import type { PlayerAction, RepeatMode } from "../api/types";
import { strings } from "../lib/strings";
import { RepeatIcon, ShuffleIcon } from "./icons";

interface Props {
  isPlaying: boolean;
  disabled: boolean;
  onAction: (action: PlayerAction) => void;
  /** Smaller buttons for the mini player (no shuffle/repeat). */
  compact?: boolean;
  shuffle?: boolean;
  repeat?: RepeatMode;
  onShuffle?: () => void;
  onRepeat?: () => void;
}

const SKIP =
  "grid size-10 shrink-0 cursor-pointer place-items-center rounded-full text-ink-soft transition-colors hover:bg-line hover:text-ink disabled:cursor-default disabled:opacity-40";

export function PlayerControls({
  isPlaying,
  disabled,
  onAction,
  compact = false,
  shuffle = false,
  repeat = "off",
  onShuffle,
  onRepeat,
}: Props) {
  const showModes = !compact && onShuffle && onRepeat;

  const repeatLabel =
    repeat === "track"
      ? strings.playback.repeatOne
      : repeat === "context"
        ? strings.playback.repeatAll
        : strings.playback.repeatOff;

  return (
    <div
      className={compact ? "flex items-center gap-1" : "-ml-2.5 flex items-center gap-2 max-lg:-ml-2"}
      role="group"
      aria-label="Playback controls"
    >
      {showModes && (
        <ModeButton
          active={shuffle}
          label={shuffle ? strings.playback.shuffleOn : strings.playback.shuffleOff}
          onClick={onShuffle}
          disabled={disabled}
        >
          <ShuffleIcon size={19} />
        </ModeButton>
      )}

      <button
        type="button"
        className={SKIP}
        disabled={disabled}
        onClick={() => onAction("previous")}
        aria-label={strings.playback.previous}
        title={strings.playback.previous}
      >
        <Icon path="M7 6h2v12H7zM10.5 12 19 6v12z" />
      </button>

      <button
        type="button"
        className={`${compact ? "size-10" : "size-12"} grid shrink-0 cursor-pointer place-items-center rounded-full bg-accent text-bg-deep transition-transform hover:scale-105 active:scale-95 disabled:cursor-default disabled:opacity-60`}
        disabled={disabled}
        onClick={() => onAction(isPlaying ? "pause" : "play")}
        aria-label={isPlaying ? strings.playback.pause : strings.playback.play}
        title={`${isPlaying ? strings.playback.pause : strings.playback.play} (Space)`}
      >
        {isPlaying ? (
          <Icon path="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" size={compact ? 18 : 22} />
        ) : (
          <Icon path="M8 5.5v13L19 12z" size={compact ? 18 : 22} />
        )}
      </button>

      <button
        type="button"
        className={SKIP}
        disabled={disabled}
        onClick={() => onAction("next")}
        aria-label={strings.playback.next}
        title={strings.playback.next}
      >
        <Icon path="M15 6h2v12h-2zM13.5 12 5 18V6z" />
      </button>

      {showModes && (
        <ModeButton
          active={repeat !== "off"}
          label={repeatLabel}
          onClick={onRepeat}
          disabled={disabled}
        >
          <RepeatIcon size={19} one={repeat === "track"} />
        </ModeButton>
      )}
    </div>
  );
}

/** Shuffle/repeat: highlighted with a dot underneath when on. */
function ModeButton({
  active,
  label,
  onClick,
  disabled,
  children,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  disabled: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      aria-label={label}
      title={label}
      className={`relative grid size-10 shrink-0 cursor-pointer place-items-center rounded-full transition-colors hover:bg-line disabled:cursor-default disabled:opacity-40 ${
        active
          ? "text-accent after:absolute after:bottom-1 after:size-1 after:rounded-full after:bg-accent"
          : "text-ink-faint hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function Icon({ path, size = 18 }: { path: string; size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}
