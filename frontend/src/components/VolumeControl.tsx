import { useRangeInput } from "../hooks/useRangeInput";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";
import { VolumeIcon } from "./icons";

/** Volume slider for the active device; hidden when the device doesn't allow it. */
export function VolumeControl({ className = "" }: { className?: string }) {
  const { playback, setVolume } = usePlayback();
  const device = playback?.device;
  const range = useRangeInput(device?.volume_percent ?? 0, setVolume);

  if (!device || !device.supports_volume || device.volume_percent == null) return null;

  const value = range.value;

  return (
    <div className={`flex items-center gap-2 text-ink-soft ${className}`}>
      <VolumeIcon size={19} muted={value === 0} />
      <input
        type="range"
        className="seek-bar"
        min={0}
        max={100}
        step={1}
        value={value}
        aria-label={strings.devices.volume}
        aria-valuetext={`${value}%`}
        style={{ "--ratio": value / 100 } as React.CSSProperties}
        {...range.inputProps}
      />
    </div>
  );
}
