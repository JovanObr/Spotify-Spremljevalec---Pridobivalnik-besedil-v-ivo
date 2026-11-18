import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../../api/client";
import type { StatsResponse } from "../../api/types";
import { useStats } from "../../hooks/queries";
import { formatPxDate, timeAgo } from "../../lib/format";
import { strings } from "../../lib/strings";
import { LineChart, SERIES_COLORS, type Series } from "./LineChart";

const MAX_SERIES = SERIES_COLORS.length;
const numberFormat = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });
const format = (value: number) => numberFormat.format(value);

/** "Music in Slovenia": the SiStat table, filterable, as a chart and a table. */
export function StatsPanel() {
  const { data, isPending, isError, error, refetch } = useStats();

  if (isPending) return <p className="text-ink-faint">{strings.stats.loading}</p>;
  if (isError) {
    return (
      <div className="text-ink-soft">
        <p>
          {error instanceof ApiError && error.status === 503 ? strings.stats.notConfigured : strings.stats.error}
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="mt-2 cursor-pointer text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent"
        >
          {strings.stats.retry}
        </button>
      </div>
    );
  }
  return <StatsExplorer data={data} />;
}

/** A sensible starting value: a "total" if the dimension has one. */
function defaultIndex(values: string[]) {
  const total = values.findIndex((value) =>
    /(^|- ?)(total|skupaj)$|^(total|skupaj|all\b|slovenia$|slovenija$)/i.test(value.trim()),
  );
  return total >= 0 ? total : 0;
}

function StatsExplorer({ data }: { data: StatsResponse }) {
  const dims = data.dimensions;
  const timeIndex = dims.findIndex((d) => d.name === data.time_dimension);
  const otherDims = dims.map((_, i) => i).filter((i) => i !== timeIndex);

  // Look a cell up by its coordinates
  const cells = useMemo(() => {
    const map = new Map<string, number | null>();
    for (const row of data.observations) {
      map.set(row.slice(0, -1).join("|"), row[row.length - 1] as number | null);
    }
    return map;
  }, [data.observations]);

  // Compare along the non-time dimension with the most values (e.g. types of
  // music); the others (e.g. performances / attendance) become dropdowns
  const initialCompare =
    otherDims
      .filter((i) => dims[i].values.length > 1)
      .sort((a, b) => dims[b].values.length - dims[a].values.length)[0] ?? otherDims[0];

  const [compare, setCompare] = useState<number>(initialCompare ?? -1);
  const [fixed, setFixed] = useState<Record<number, number>>(() =>
    Object.fromEntries(otherDims.map((i) => [i, defaultIndex(dims[i].values)])),
  );
  const [shown, setShown] = useState<number[]>([]);
  const timeLabels = timeIndex >= 0 ? dims[timeIndex].values : ["Value"];
  const [range, setRange] = useState<[number, number]>([0, timeLabels.length - 1]);
  const [view, setView] = useState<"chart" | "table">("chart");
  const [sort, setSort] = useState<{ column: number; descending: boolean }>({ column: -1, descending: false });

  // When the compared dimension changes, start with its first few values
  useEffect(() => {
    if (compare < 0) return;
    const values = dims[compare].values;
    const start = values
      .map((_, i) => i)
      .filter((i) => i !== defaultIndex(values) || values.length === 1)
      .slice(0, 4);
    setShown(start.length ? start : [0]);
  }, [compare, dims]);

  const years = timeLabels.map((_, i) => i).slice(range[0], range[1] + 1);

  const series: Series[] = (compare >= 0 ? shown : [0]).map((valueIndex) => ({
    key: String(valueIndex),
    label: compare >= 0 ? dims[compare].values[valueIndex] : data.contents ?? data.title,
    // Colour follows the value, so hiding one series never repaints the others
    color: SERIES_COLORS[valueIndex % MAX_SERIES],
    values: years.map((year) => {
      const coords = dims.map((_, d) =>
        d === timeIndex ? year : d === compare ? valueIndex : (fixed[d] ?? 0),
      );
      return cells.get(coords.join("|")) ?? null;
    }),
  }));

  const hasData = series.some((s) => s.values.some((v) => v != null));

  // Table rows, optionally sorted by a column (-1 = by year)
  const rows = years.map((year, r) => ({ label: timeLabels[year], values: series.map((s) => s.values[r]) }));
  const sortedRows =
    sort.column < 0
      ? sort.descending
        ? [...rows].reverse()
        : rows
      : [...rows].sort((a, b) => {
          const av = a.values[sort.column] ?? -Infinity;
          const bv = b.values[sort.column] ?? -Infinity;
          return sort.descending ? bv - av : av - bv;
        });

  const toggleSeries = (index: number) =>
    setShown((current) =>
      current.includes(index)
        ? current.filter((i) => i !== index)
        : current.length >= MAX_SERIES
          ? current
          : [...current, index].sort((a, b) => a - b),
    );

  const downloadCsv = () => {
    const header = [data.time_dimension ?? "", ...series.map((s) => s.label)];
    const lines = [header, ...rows.map((row) => [row.label, ...row.values.map((v) => (v == null ? "" : String(v)))])];
    const csv = lines.map((line) => line.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    link.download = "music-in-slovenia.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const select =
    "h-9 max-w-full cursor-pointer appearance-none truncate rounded-full bg-transparent pr-8 pl-3.5 text-sm text-ink ring-1 ring-line transition-colors hover:bg-line [&>option]:bg-bg-deep [&>option]:text-ink";

  return (
    <div>
      <h2 className="text-xl font-[650] text-ink">{data.title}</h2>
      <p className="mt-1 text-sm text-ink-faint">
        {[
          data.units && `Unit: ${data.units}.`,
          data.last_updated && strings.stats.updated(formatPxDate(data.last_updated) ?? ""),
          strings.stats.fetched(timeAgo(data.fetched_at)),
        ]
          .filter(Boolean)
          .join(" ")}
      </p>
      {data.stale && <p className="mt-2 text-sm text-ink-soft">{strings.stats.stale}</p>}

      {/* Filters, in one row above the chart */}
      <div className="mt-6 flex flex-wrap items-end gap-3">
        {otherDims.length > 1 && (
          <Labelled label={strings.stats.compareBy}>
            <select className={select} value={compare} onChange={(e) => setCompare(Number(e.target.value))}>
              {otherDims.map((i) => (
                <option key={i} value={i}>
                  {dims[i].name.toLowerCase()}
                </option>
              ))}
            </select>
          </Labelled>
        )}
        {otherDims
          .filter((i) => i !== compare && dims[i].values.length > 1)
          .map((i) => (
            <Labelled key={i} label={dims[i].name.toLowerCase()}>
              <select
                className={select}
                value={fixed[i] ?? 0}
                onChange={(e) => setFixed((current) => ({ ...current, [i]: Number(e.target.value) }))}
              >
                {dims[i].values.map((value, v) => (
                  <option key={value} value={v}>
                    {value}
                  </option>
                ))}
              </select>
            </Labelled>
          ))}
        {timeIndex >= 0 && timeLabels.length > 1 && (
          <>
            <Labelled label={strings.stats.from}>
              <select
                className={select}
                value={range[0]}
                onChange={(e) => setRange(([, to]) => [Math.min(Number(e.target.value), to), to])}
              >
                {timeLabels.map((label, i) => (
                  <option key={label} value={i}>
                    {label}
                  </option>
                ))}
              </select>
            </Labelled>
            <Labelled label={strings.stats.to}>
              <select
                className={select}
                value={range[1]}
                onChange={(e) => setRange(([from]) => [from, Math.max(Number(e.target.value), from)])}
              >
                {timeLabels.map((label, i) => (
                  <option key={label} value={i}>
                    {label}
                  </option>
                ))}
              </select>
            </Labelled>
          </>
        )}
      </div>

      {/* Which values of the compared dimension are drawn: the legend doubles as the filter */}
      {compare >= 0 && (
        <div className="mt-4">
          <p className="mb-2 text-sm text-ink-faint">{strings.stats.show}</p>
          <ul className="flex flex-wrap gap-2">
            {dims[compare].values.map((value, i) => {
              const on = shown.includes(i);
              return (
                <li key={value}>
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() => toggleSeries(i)}
                    disabled={!on && shown.length >= MAX_SERIES}
                    className={`flex h-8 cursor-pointer items-center gap-2 rounded-full px-3 text-sm ring-1 transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                      on ? "text-ink ring-ink-faint" : "text-ink-faint ring-line hover:text-ink-soft"
                    }`}
                  >
                    <span
                      className="size-2.5 rounded-full"
                      style={{ background: on ? SERIES_COLORS[i % MAX_SERIES] : "transparent", boxShadow: `inset 0 0 0 1.5px ${SERIES_COLORS[i % MAX_SERIES]}` }}
                      aria-hidden="true"
                    />
                    {value}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="mt-6 flex items-center gap-1" role="tablist">
        {(["chart", "table"] as const).map((option) => (
          <button
            key={option}
            type="button"
            role="tab"
            aria-selected={view === option}
            onClick={() => setView(option)}
            className={`h-8 cursor-pointer rounded-full px-3.5 text-sm transition-colors ${
              view === option ? "bg-line text-ink" : "text-ink-faint hover:text-ink"
            }`}
          >
            {option === "chart" ? strings.stats.chart : strings.stats.table}
          </button>
        ))}
        <button
          type="button"
          onClick={downloadCsv}
          className="ml-auto h-8 cursor-pointer rounded-full px-3.5 text-sm text-ink-faint ring-1 ring-line transition-colors hover:bg-line hover:text-ink"
        >
          {strings.stats.download}
        </button>
      </div>

      <div className="mt-4">
        {!hasData ? (
          <p className="text-ink-faint">{strings.stats.noData}</p>
        ) : view === "chart" ? (
          <LineChart labels={years.map((y) => timeLabels[y])} series={series} units={data.units} format={format} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-ink-faint">
                  {[data.time_dimension ?? "", ...series.map((s) => s.label)].map((label, column) => (
                    <th key={label + column} className={`py-2 pr-4 font-[500] ${column > 0 ? "text-right" : ""}`}>
                      <button
                        type="button"
                        onClick={() =>
                          setSort((current) => ({
                            column: column - 1,
                            descending: current.column === column - 1 ? !current.descending : column > 0,
                          }))
                        }
                        aria-label={strings.stats.sortBy(label)}
                        className="cursor-pointer hover:text-ink"
                      >
                        {label}
                        {sort.column === column - 1 ? (sort.descending ? " ↓" : " ↑") : ""}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row) => (
                  <tr key={row.label} className="border-b border-line/60">
                    <td className="py-2 pr-4 text-ink-soft">{row.label}</td>
                    {row.values.map((value, i) => (
                      <td key={i} className="py-2 pr-4 text-right text-ink tabular-nums">
                        {value == null ? "–" : format(value)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data.notes.length > 0 && (
        <ul className="mt-6 space-y-1 text-sm text-ink-faint">
          {data.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
      <p className="mt-6 text-xs text-ink-faint">
        {strings.stats.source}.{" "}
        <a href={data.table_url} target="_blank" rel="noreferrer" className="underline decoration-line underline-offset-4 hover:text-ink">
          {strings.stats.openOnSiStat}
        </a>
      </p>
    </div>
  );
}

function Labelled({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="relative flex min-w-0 flex-col gap-1.5">
      <span className="text-xs text-ink-faint first-letter:uppercase">{label}</span>
      <span className="relative flex items-center">
        {children}
        <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" className="pointer-events-none absolute right-3 text-ink-soft" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </span>
    </label>
  );
}
