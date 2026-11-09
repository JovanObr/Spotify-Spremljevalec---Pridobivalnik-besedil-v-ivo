// The frame around every view: navigation (a rail on desktop, a tab bar on
// mobile), the mini player and notices. Views render into <Outlet />.

import { useEffect, useRef } from "react";
import { NavLink, Outlet, useLocation } from "react-router";

import { usePlayback } from "../../playback/PlaybackProvider";
import { useDisconnect } from "../../hooks/useDisconnect";
import { strings } from "../../lib/strings";
import { AppMark, LibraryIcon, LogoutIcon, NowPlayingIcon, SearchIcon } from "../icons";
import { MiniPlayer } from "./MiniPlayer";

const NAV_ITEMS = [
  { to: "/", label: strings.nav.nowPlaying, Icon: NowPlayingIcon, end: true },
  { to: "/search", label: strings.nav.search, Icon: SearchIcon, end: false },
  { to: "/library", label: strings.nav.library, Icon: LibraryIcon, end: false },
];

export function AppShell() {
  const { playback, notice } = usePlayback();
  const { pathname } = useLocation();
  const disconnect = useDisconnect();

  // Each new view starts at the top (desktop scrolls this pane, mobile the window)
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scroller.current?.scrollTo(0, 0);
    window.scrollTo(0, 0);
  }, [pathname]);

  // The full player is already on screen in Now Playing
  const showMiniPlayer = Boolean(playback) && pathname !== "/";

  return (
    <div className="lg:grid lg:h-dvh lg:grid-cols-[5.5rem_1fr]">
      {/* Desktop rail */}
      <nav
        aria-label={strings.nav.main}
        className="flex flex-col items-center gap-2 border-r border-line py-6 max-lg:hidden"
      >
        <div className="mb-6">
          <AppMark />
        </div>
        {NAV_ITEMS.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              [
                "relative flex w-[4.5rem] flex-col items-center gap-1.5 rounded-lg py-2.5 text-center text-[0.7rem] leading-tight transition-colors",
                isActive
                  ? "text-accent before:absolute before:top-2.5 before:-left-3 before:h-6 before:w-[3px] before:rounded-full before:bg-accent"
                  : "text-ink-faint hover:bg-line hover:text-ink",
              ].join(" ")
            }
          >
            <Icon />
            {label}
          </NavLink>
        ))}
        <button
          type="button"
          onClick={disconnect}
          className="mt-auto grid size-11 cursor-pointer place-items-center rounded-lg text-ink-faint transition-colors hover:bg-line hover:text-ink"
          aria-label={strings.playback.disconnect}
          title={strings.playback.disconnect}
        >
          <LogoutIcon size={20} />
        </button>
      </nav>

      <div className="flex min-h-0 flex-col max-lg:min-h-dvh">
        <div
          ref={scroller}
          className={`min-h-0 flex-1 lg:overflow-y-auto ${
            // Mobile: leave room for the tab bar, plus the mini player when shown
            showMiniPlayer
              ? "max-lg:pb-[calc(8rem+env(safe-area-inset-bottom))]"
              : "max-lg:pb-[calc(4rem+env(safe-area-inset-bottom))]"
          }`}
        >
          <Outlet />
        </div>

        {showMiniPlayer && <MiniPlayer />}
      </div>

      {/* Mobile tab bar */}
      <nav
        aria-label={strings.nav.main}
        className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-3 border-t border-line bg-bg-deep/85 pb-[env(safe-area-inset-bottom)] backdrop-blur-lg lg:hidden"
      >
        {NAV_ITEMS.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex h-16 flex-col items-center justify-center gap-1 text-xs ${isActive ? "text-accent" : "text-ink-faint"}`
            }
          >
            <Icon size={20} />
            {label}
          </NavLink>
        ))}
      </nav>

      {notice && (
        <p
          role="status"
          className="fixed top-4 right-4 z-30 max-w-sm rounded-2xl border border-line bg-bg-deep/90 px-4 py-2.5 text-sm text-ink shadow-lg backdrop-blur max-lg:left-4"
        >
          {notice}
        </p>
      )}
    </div>
  );
}
