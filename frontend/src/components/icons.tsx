// Small stroke icons used across the app. 24x24 grid, currentColor.

interface IconProps {
  size?: number;
}

function Stroke({ size = 22, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/** Lines of text of different length: lyrics / now playing. */
export function NowPlayingIcon(props: IconProps) {
  return (
    <Stroke {...props}>
      <path d="M4 7h16M4 12h11M4 17h14" />
    </Stroke>
  );
}

/** Stacked records: library. */
export function LibraryIcon(props: IconProps) {
  return (
    <Stroke {...props}>
      <rect x="4" y="9" width="12" height="11" rx="1.5" />
      <path d="M7 6h12.5a.5.5 0 0 1 .5.5V17" />
      <path d="M10 13.5v3M10 16.5a1.5 1.5 0 1 1-1.5-1.5" />
    </Stroke>
  );
}

export function LogoutIcon(props: IconProps) {
  return (
    <Stroke {...props}>
      <path d="M14 5h4a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-4M10 16l-4-4 4-4M6 12h9" />
    </Stroke>
  );
}

/** The app mark: three lyric lines, as in the favicon. */
export function AppMark({ size = 28 }: IconProps) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--c-bg-deep)" />
      <path
        d="M8 11h16M8 16h11M8 21h14"
        stroke="var(--c-accent)"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Stroke {...props}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </Stroke>
  );
}

export function HeartIcon({ size = 20, filled = false }: IconProps & { filled?: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z" />
    </svg>
  );
}

export function ShuffleIcon(props: IconProps) {
  return (
    <Stroke {...props}>
      <path d="M4 7h3.5c4 0 5 10 9 10H20M4 17h3.5c1.6 0 2.7-1.6 3.6-3.6M13 9.6C13.9 8 15 7 16.5 7H20M17.5 4.5 20 7l-2.5 2.5M17.5 14.5 20 17l-2.5 2.5" />
    </Stroke>
  );
}

export function RepeatIcon({ size = 22, one = false }: IconProps & { one?: boolean }) {
  return (
    <Stroke size={size}>
      <path d="M5 11V9a2 2 0 0 1 2-2h11M15.5 4.5 18 7l-2.5 2.5M19 13v2a2 2 0 0 1-2 2H6M8.5 19.5 6 17l2.5-2.5" />
      {one && <path d="M11.5 10.5 12.5 10v4" strokeWidth={1.6} />}
    </Stroke>
  );
}

export function DevicesIcon(props: IconProps) {
  return (
    <Stroke {...props}>
      <rect x="3" y="5" width="12" height="9" rx="1.5" />
      <path d="M6 18h6M9 14v4" />
      <rect x="17" y="8" width="4" height="10" rx="1" />
    </Stroke>
  );
}

export function VolumeIcon({ size = 20, muted = false }: IconProps & { muted?: boolean }) {
  return (
    <Stroke size={size}>
      <path d="M4 9.5h3l4.5-4v13l-4.5-4H4z" />
      {muted ? <path d="m16 10 4 4m0-4-4 4" /> : <path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" />}
    </Stroke>
  );
}

export function QueueIcon(props: IconProps) {
  return (
    <Stroke {...props}>
      <path d="M4 6h12M4 11h12M4 16h7M17 14v6M14 17h6" />
    </Stroke>
  );
}
