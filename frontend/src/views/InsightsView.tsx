import { NavLink, Route, Routes } from "react-router";

import { SourcesPanel } from "../components/insights/SourcesPanel";
import { StatsPanel } from "../components/insights/StatsPanel";
import { strings } from "../lib/strings";

/** Insights: Music in Slovenia (SiStat) and the Data sources overview. */
export function InsightsView() {
  const tab = ({ isActive }: { isActive: boolean }) =>
    `h-9 rounded-full px-4 text-sm leading-9 transition-colors ${
      isActive ? "bg-accent font-[600] text-bg-deep" : "text-ink-soft ring-1 ring-line hover:bg-line hover:text-ink"
    }`;

  return (
    <div className="mx-auto max-w-[90rem] px-6 py-8 lg:px-12 lg:py-10">
      <h1 className="text-[clamp(2.2rem,5vw,3.5rem)] leading-[1] font-[720] tracking-[-0.03em] [font-stretch:88%]">
        {strings.insights.title}
      </h1>
      <nav className="mt-6 flex gap-2" aria-label={strings.insights.title}>
        <NavLink to="/insights" end className={tab}>
          {strings.insights.tabs.stats}
        </NavLink>
        <NavLink to="/insights/sources" className={tab}>
          {strings.insights.tabs.sources}
        </NavLink>
      </nav>

      <div className="mt-8">
        <Routes>
          <Route index element={<StatsPanel />} />
          <Route path="sources" element={<SourcesPanel />} />
        </Routes>
      </div>
    </div>
  );
}
