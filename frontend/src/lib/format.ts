export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "--:--";

  const total = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  const ss = String(seconds).padStart(2, "0");

  return hours
    ? `${hours}:${String(minutes).padStart(2, "0")}:${ss}`
    : `${minutes}:${ss}`;
}

/** Index of the last line whose time has passed (binary search), or -1. */
export function findActiveLine(
  lines: { time_ms: number }[],
  progressMs: number,
): number {
  let low = 0;
  let high = lines.length - 1;
  let found = -1;

  while (low <= high) {
    const mid = (low + high) >> 1;
    if (lines[mid].time_ms <= progressMs) {
      found = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  return found;
}

/** Long durations in words: "42 min", "1 h 12 min". */
export function formatTotalDuration(ms: number): string {
  const minutes = Math.round(ms / 60000);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

/** "just now", "5 minutes ago", "3 hours ago", "2 days ago" (from Unix seconds). */
export function timeAgo(unixSeconds: number, now = Date.now()): string {
  const seconds = Math.max(0, Math.round(now / 1000 - unixSeconds));
  if (seconds < 45) return "just now";
  const units: [number, string][] = [
    [86400, "day"],
    [3600, "hour"],
    [60, "minute"],
  ];
  for (const [size, name] of units) {
    if (seconds >= size) {
      const count = Math.round(seconds / size);
      return `${count} ${name}${count === 1 ? "" : "s"} ago`;
    }
  }
  return "a minute ago";
}

/** SiStat's "20250601 10:00" as "1 June 2025". */
export function formatPxDate(value: string | null | undefined): string | null {
  const match = value?.match(/^(\d{4})(\d{2})(\d{2})/);
  if (!match) return value ?? null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}
