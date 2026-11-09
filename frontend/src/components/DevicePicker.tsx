import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useDevices } from "../hooks/queries";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";
import { DevicesIcon } from "./icons";

const PANEL_WIDTH = 288;
const MARGIN = 8;

interface Props {
  /** Preferred side; flips automatically when there isn't room. */
  placement?: "above" | "below";
  /** Show the current device's name next to the icon. */
  showName?: boolean;
}

/** "Play on…": lists Spotify devices and moves playback to the chosen one. */
export function DevicePicker({ placement = "below", showName = true }: Props) {
  const [open, setOpen] = useState(false);
  const { playback, transferTo, isBusy } = usePlayback();
  const { data: devices, isPending, isError } = useDevices(open);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<React.CSSProperties>({ visibility: "hidden" });

  // The panel is rendered into <body> (a portal) with position: fixed, so
  // scrolling containers can't clip it and blurred bars (backdrop-filter
  // changes what "fixed" is relative to) can't shift it. It's placed next
  // to the button, inside the window.
  useLayoutEffect(() => {
    if (!open || !button.current || !panel.current) return;
    const place = () => {
      const anchor = button.current!.getBoundingClientRect();
      const height = panel.current!.offsetHeight;
      const roomBelow = window.innerHeight - anchor.bottom - MARGIN;
      const below = placement === "below" ? roomBelow >= height || roomBelow > anchor.top : anchor.top < height;
      const left = Math.min(
        Math.max(MARGIN, anchor.left),
        document.documentElement.clientWidth - PANEL_WIDTH - MARGIN,
      );
      setPosition(
        below
          ? { top: anchor.bottom + MARGIN, left }
          : { bottom: window.innerHeight - anchor.top + MARGIN, left },
      );
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open, placement, devices?.length, isPending]);

  // Close on outside click or Escape
  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!root.current?.contains(target) && !panel.current?.contains(target)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const currentName = playback?.device?.name;

  return (
    <div ref={root} className="relative">
      <button
        ref={button}
        type="button"
        onClick={() => {
          setPosition({ visibility: "hidden" });
          setOpen((value) => !value);
        }}
        aria-expanded={open}
        aria-haspopup="true"
        title={strings.devices.title}
        className={`flex h-10 max-w-48 cursor-pointer items-center gap-2 rounded-full px-2.5 text-sm transition-colors hover:bg-line ${
          open ? "bg-line text-ink" : "text-ink-soft hover:text-ink"
        }`}
      >
        <DevicesIcon size={19} />
        {showName && currentName ? (
          <span className="truncate">{currentName}</span>
        ) : (
          <span className="sr-only">{strings.devices.button}</span>
        )}
      </button>

      {open &&
        createPortal(
        <div
          ref={panel}
          style={{ ...position, width: PANEL_WIDTH }}
          className="fixed z-50 max-h-[60vh] overflow-y-auto rounded-xl border border-line bg-bg-deep/95 p-2 shadow-2xl backdrop-blur-lg"
        >
          <p className="px-2.5 pt-1.5 pb-2 text-sm font-[600] text-ink">{strings.devices.title}</p>

          {isPending ? (
            <p className="px-2.5 pb-2 text-sm text-ink-faint">{strings.devices.loading}</p>
          ) : isError ? (
            <p className="px-2.5 pb-2 text-sm text-ink-soft">{strings.devices.error}</p>
          ) : devices.length === 0 ? (
            <p className="px-2.5 pb-2 text-sm text-ink-soft">{strings.devices.none}</p>
          ) : (
            <ul>
              {devices.map((device) => (
                <li key={device.id ?? device.name}>
                  <button
                    type="button"
                    disabled={!device.id || device.is_active || isBusy}
                    onClick={() => {
                      if (!device.id) return;
                      transferTo(device.id, device.name);
                      setOpen(false);
                    }}
                    className="flex w-full cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-line disabled:cursor-default disabled:hover:bg-transparent"
                  >
                    <DevicesIcon size={18} />
                    <span className="min-w-0 flex-1">
                      <span className={`block truncate ${device.is_active ? "text-accent" : "text-ink"}`}>
                        {device.name}
                      </span>
                      <span className="block text-xs text-ink-faint">
                        {device.is_active ? strings.devices.current : device.type}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>,
          document.body,
        )}
    </div>
  );
}
