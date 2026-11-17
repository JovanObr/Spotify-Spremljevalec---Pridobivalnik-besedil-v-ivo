import { useCallback, useRef, useState } from "react";

import { useDevices } from "../hooks/queries";
import { strings } from "../lib/strings";
import type { Device } from "../api/types";
import { usePlayback } from "../playback/PlaybackProvider";
import { useWebPlayer } from "../playback/WebPlayerProvider";
import { DevicesIcon } from "./icons";
import { Popover } from "./Popover";

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
  const { data: apiDevices, isPending, isError } = useDevices(open);
  const webPlayer = useWebPlayer();

  // This tab's player can take a moment to appear in Spotify's device list
  const devices: Device[] | undefined =
    apiDevices && webPlayer.deviceId && !apiDevices.some((d) => d.id === webPlayer.deviceId)
      ? [
          {
            id: webPlayer.deviceId,
            name: strings.appName,
            type: "Computer",
            is_active: false,
            volume_percent: null,
            supports_volume: true,
          },
          ...apiDevices,
        ]
      : apiDevices;
  const webNote =
    webPlayer.status === "ready"
      ? null
      : webPlayer.problem
        ? strings.devices.webPlayer[webPlayer.problem]
        : strings.devices.webPlayer.connecting;
  const button = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => setOpen(false), []);

  const currentName = playback?.device?.name;

  return (
    <div className="relative">
      <button
        ref={button}
        type="button"
        onClick={() => setOpen((value) => !value)}
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

      <Popover
        open={open}
        onClose={close}
        anchor={button}
        placement={placement}
        contentKey={`${devices?.length}-${isPending}`}
        label={strings.devices.title}
      >
          <p className="px-2.5 pt-1.5 pb-2 text-sm font-[600] text-ink">{strings.devices.title}</p>

          {isError ? (
            <p className="px-2.5 pb-2 text-sm text-ink-soft">{strings.devices.error}</p>
          ) : isPending || !devices ? (
            <p className="px-2.5 pb-2 text-sm text-ink-faint">{strings.devices.loading}</p>
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
                        {device.is_active
                          ? strings.devices.current
                          : device.id === webPlayer.deviceId
                            ? `${strings.devices.thisBrowser}. ${strings.devices.playHere}`
                            : device.type}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {webNote && <p className="px-2.5 pt-1 pb-2 text-xs text-ink-faint">{webNote}</p>}
      </Popover>
    </div>
  );
}
