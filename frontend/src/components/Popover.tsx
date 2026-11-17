import { useEffect, useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

const MARGIN = 8;

interface Props {
  open: boolean;
  onClose: () => void;
  /** The button the panel belongs to; clicks on it don't count as "outside". */
  anchor: RefObject<HTMLElement | null>;
  width?: number;
  /** Preferred side; flips automatically when there isn't room. */
  placement?: "above" | "below";
  /** Anything that changes the panel's height (so it's placed again). */
  contentKey?: unknown;
  label?: string;
  children: ReactNode;
}

/**
 * A floating panel next to a button (device list, add to playlist).
 *
 * It's rendered into <body> (a portal) with position: fixed, so scrolling
 * containers can't clip it and blurred bars (backdrop-filter changes what
 * "fixed" is relative to) can't shift it. It stays inside the window and
 * closes on an outside click or Escape.
 */
export function Popover({
  open,
  onClose,
  anchor,
  width = 288,
  placement = "below",
  contentKey,
  label,
  children,
}: Props) {
  const panel = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<React.CSSProperties>({ visibility: "hidden" });

  useLayoutEffect(() => {
    if (!open) {
      setPosition({ visibility: "hidden" });
      return;
    }
    if (!anchor.current || !panel.current) return;
    const place = () => {
      const box = anchor.current!.getBoundingClientRect();
      const height = panel.current!.offsetHeight;
      const roomBelow = window.innerHeight - box.bottom - MARGIN;
      const below = placement === "below" ? roomBelow >= height || roomBelow > box.top : box.top < height;
      const left = Math.min(
        Math.max(MARGIN, box.left),
        document.documentElement.clientWidth - width - MARGIN,
      );
      setPosition(
        below ? { top: box.bottom + MARGIN, left } : { bottom: window.innerHeight - box.top + MARGIN, left },
      );
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open, placement, width, contentKey, anchor]);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!anchor.current?.contains(target) && !panel.current?.contains(target)) onClose();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose, anchor]);

  if (!open) return null;

  return createPortal(
    <div
      ref={panel}
      role="dialog"
      aria-label={label}
      style={{ ...position, width }}
      className="fixed z-50 max-h-[60vh] overflow-y-auto rounded-xl border border-line bg-bg-deep/95 p-2 shadow-2xl backdrop-blur-lg"
    >
      {children}
    </div>,
    document.body,
  );
}
