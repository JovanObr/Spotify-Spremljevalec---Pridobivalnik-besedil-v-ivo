import { useEffect, useMemo, useRef, useState } from "react";

// The reference categorical palette, dark-surface steps, in fixed order
// (validated for adjacent series; see the dataviz guidance). A series keeps
// its colour when others are hidden: colour follows the entity.
export const SERIES_COLORS = [
  "#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767",
];

export interface Series {
  key: string;
  label: string;
  color: string;
  values: (number | null)[];
}

interface Props {
  labels: string[];
  series: Series[];
  units?: string | null;
  format: (value: number) => string;
}

const HEIGHT = 320;
const PAD = { top: 16, right: 16, bottom: 32, left: 64 };

function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0];
  const rough = max / count;
  const power = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? rough;
  const ticks = [];
  for (let value = 0; value <= max + step * 0.001; value += step) ticks.push(value);
  if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + step);
  return ticks;
}

/** A line chart with a hover crosshair and tooltip. One y-axis, starting at zero. */
export function LineChart({ labels, series, units, format }: Props) {
  const [hover, setHover] = useState<number | null>(null);

  // Drawn at the container's real width, so text stays at its normal size
  const box = useRef<HTMLDivElement>(null);
  const [WIDTH, setWidth] = useState(720);
  useEffect(() => {
    if (!box.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    observer.observe(box.current);
    return () => observer.disconnect();
  }, []);

  const { ticks, top } = useMemo(() => {
    const max = Math.max(0, ...series.flatMap((s) => s.values.filter((v): v is number => v != null)));
    const ticks = niceTicks(max);
    return { ticks, top: ticks[ticks.length - 1] || 1 };
  }, [series]);

  const innerW = WIDTH - PAD.left - PAD.right;
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const x = (i: number) => PAD.left + (labels.length === 1 ? innerW / 2 : (i / (labels.length - 1)) * innerW);
  const y = (v: number) => PAD.top + innerH - (v / top) * innerH;

  // Only label every nth year when there are many
  const every = Math.ceil(labels.length / 10);

  const path = (values: (number | null)[]) => {
    let d = "";
    let pen = false;
    values.forEach((value, i) => {
      if (value == null) {
        pen = false; // a gap, not a drop to zero
        return;
      }
      d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(value).toFixed(1)}`;
      pen = true;
    });
    return d;
  };

  const onMove = (event: React.PointerEvent<SVGRectElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - box.left) / box.width;
    const index = Math.round(ratio * (labels.length - 1));
    setHover(Math.max(0, Math.min(labels.length - 1, index)));
  };

  return (
    <div ref={box} className="relative">
      <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="block" role="img" aria-label="Line chart">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(tick)} y2={y(tick)} stroke="var(--color-line)" strokeWidth={1} />
            <text x={PAD.left - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle" className="fill-ink-faint text-[11px]">
              {format(tick)}
            </text>
          </g>
        ))}
        {labels.map((label, i) =>
          i % every === 0 || i === labels.length - 1 ? (
            <text key={label} x={x(i)} y={HEIGHT - 10} textAnchor="middle" className="fill-ink-faint text-[11px]">
              {label}
            </text>
          ) : null,
        )}

        {hover != null && (
          <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + innerH} stroke="var(--color-ink-faint)" strokeDasharray="3 3" />
        )}

        {series.map((s) => (
          <g key={s.key}>
            <path d={path(s.values)} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            {s.values.map((value, i) =>
              value != null && (hover === i || labels.length <= 12) ? (
                <circle
                  key={i}
                  cx={x(i)}
                  cy={y(value)}
                  r={hover === i ? 5 : 3}
                  fill={s.color}
                  stroke="var(--c-bg-deep)"
                  strokeWidth={2}
                />
              ) : null,
            )}
          </g>
        ))}

        <rect
          x={PAD.left}
          y={PAD.top}
          width={innerW}
          height={innerH}
          fill="transparent"
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
        />
      </svg>

      {hover != null && (
        <div
          className="pointer-events-none absolute top-2 z-10 min-w-44 rounded-lg border border-line bg-bg-deep/95 p-3 text-sm shadow-xl backdrop-blur"
          style={
            x(hover) / WIDTH > 0.6
              ? { right: `${100 - (x(hover) / WIDTH) * 100 + 2}%` }
              : { left: `${(x(hover) / WIDTH) * 100 + 2}%` }
          }
        >
          <p className="font-[600] text-ink">{labels[hover]}</p>
          <ul className="mt-1.5 space-y-1">
            {series.map((s) => (
              <li key={s.key} className="flex items-center gap-2">
                <span className="size-2.5 shrink-0 rounded-full" style={{ background: s.color }} aria-hidden="true" />
                <span className="flex-1 text-ink-soft">{s.label}</span>
                <span className="text-ink tabular-nums">
                  {s.values[hover] == null ? "–" : format(s.values[hover]!)}
                </span>
              </li>
            ))}
          </ul>
          {units && <p className="mt-1.5 text-xs text-ink-faint">{units}</p>}
        </div>
      )}
    </div>
  );
}
