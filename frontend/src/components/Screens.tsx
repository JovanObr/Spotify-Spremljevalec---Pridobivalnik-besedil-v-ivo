// Full-page states: not connected, server down, nothing playing.

import { api } from "../api/client";
import { strings } from "../lib/strings";

function Stage({
  title,
  children,
  inShell = false,
}: {
  title: string;
  children: React.ReactNode;
  inShell?: boolean;
}) {
  const Tag = inShell ? "div" : "main";
  return (
    <Tag
      className={`mx-auto flex max-w-3xl flex-col justify-center px-6 py-16 ${inShell ? "min-h-full" : "min-h-dvh"}`}
    >
      <h1 className="text-[clamp(2.4rem,6vw,4.25rem)] leading-[1] font-[720] tracking-[-0.03em] text-balance [font-stretch:88%]">
        {title}
      </h1>
      <div className="mt-6 max-w-xl text-lg leading-relaxed text-ink-soft">{children}</div>
    </Tag>
  );
}

export function ConnectScreen() {
  const authError = new URLSearchParams(window.location.search).has("auth_error");

  return (
    <Stage title={strings.connect.title}>
      <p>{strings.connect.body}</p>
      {authError && <p className="mt-4 text-accent">{strings.connect.authFailed}</p>}
      <a
        href={api.loginUrl()}
        className="mt-8 inline-flex items-center gap-3 rounded-full bg-accent px-6 py-3 text-base font-[650] text-bg-deep transition-transform hover:scale-[1.03] active:scale-[0.98]"
      >
        <SpotifyGlyph />
        {strings.connect.button}
      </a>
    </Stage>
  );
}

export function ServerDownScreen() {
  return (
    <Stage title={strings.serverDown.title}>
      <p>{strings.serverDown.body}</p>
    </Stage>
  );
}

export function IdleScreen() {
  return (
    <Stage title={strings.idle.title} inShell>
      <p>{strings.idle.body}</p>
    </Stage>
  );
}

function SpotifyGlyph() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="currentColor">
      <path d="M12 1.5a10.5 10.5 0 1 0 0 21 10.5 10.5 0 0 0 0-21Zm4.82 15.15a.65.65 0 0 1-.9.22c-2.46-1.5-5.56-1.84-9.21-1.01a.66.66 0 0 1-.29-1.28c4-.91 7.42-.52 10.18 1.17.31.19.4.59.22.9Zm1.28-2.86a.82.82 0 0 1-1.12.27c-2.82-1.73-7.11-2.23-10.44-1.22a.82.82 0 1 1-.48-1.57c3.8-1.15 8.53-.6 11.77 1.4.38.23.5.73.27 1.12Zm.11-2.98C14.83 8.8 9.27 8.62 6.05 9.6a.98.98 0 1 1-.57-1.88c3.7-1.12 9.84-.9 13.72 1.4a.98.98 0 0 1-1 1.69Z" />
    </svg>
  );
}
