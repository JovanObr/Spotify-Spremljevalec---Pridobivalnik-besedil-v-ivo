import { useEffect, useRef, useState } from "react";

const KEYBOARD_DELAY_MS = 400; // wait for the user to stop pressing arrows
const SETTLE_MS = 800; // keep showing the chosen value until Spotify catches up

/**
 * Shared behaviour for the seek and volume sliders.
 *
 * - Dragging: the slider follows the pointer; one command is sent on release.
 * - Keyboard: arrow presses are combined; one command is sent after a pause.
 * - After sending, the chosen value stays on screen briefly, so the slider
 *   doesn't jump back while Spotify applies it.
 */
export function useRangeInput(actual: number, onCommit: (value: number) => void) {
  const [draft, setDraft] = useState<number | null>(null);
  const draftRef = useRef<number | null>(null);
  const pointerDown = useRef(false);
  const keyTimer = useRef<number>();
  const settleTimer = useRef<number>();

  useEffect(
    () => () => {
      window.clearTimeout(keyTimer.current);
      window.clearTimeout(settleTimer.current);
    },
    [],
  );

  const update = (value: number) => {
    draftRef.current = value;
    setDraft(value);
  };

  const commit = () => {
    window.clearTimeout(keyTimer.current);
    const value = draftRef.current;
    if (value == null) return;
    onCommit(value);
    draftRef.current = null;
    window.clearTimeout(settleTimer.current);
    settleTimer.current = window.setTimeout(() => {
      if (draftRef.current == null) setDraft(null);
    }, SETTLE_MS);
  };

  return {
    value: draft ?? actual,
    inputProps: {
      onChange: (event: React.ChangeEvent<HTMLInputElement>) => {
        update(Number(event.target.value));
        if (!pointerDown.current) {
          window.clearTimeout(keyTimer.current);
          keyTimer.current = window.setTimeout(commit, KEYBOARD_DELAY_MS);
        }
      },
      onPointerDown: () => {
        pointerDown.current = true;
      },
      onPointerUp: () => {
        pointerDown.current = false;
        commit();
      },
      onBlur: commit,
    },
  };
}
