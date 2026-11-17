import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { ApiError, api } from "../api/client";
import type { PlaylistSummary, Track } from "../api/types";
import { usePlaylists } from "../hooks/queries";
import { strings } from "../lib/strings";
import { usePlayback } from "../playback/PlaybackProvider";
import { AddIcon } from "./icons";
import { PlaylistCover } from "./library/PlaylistCover";
import { Popover } from "./Popover";

// Show a filter box when the list gets long
const FILTER_FROM = 8;

interface Props {
  track: Track;
  size?: number;
  placement?: "above" | "below";
  /** Extra classes for the round button (e.g. to show it on row hover). */
  className?: string;
}

/** "Add to playlist": a button that opens the user's editable playlists. */
export function AddToPlaylistButton({ track, size = 18, placement = "below", className = "" }: Props) {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => setOpen(false), []);

  if (!track.uri || track.is_local) return null;
  const label = strings.addToPlaylist.button(track.title);

  return (
    <>
      <button
        ref={button}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={label}
        title={label}
        className={`grid size-9 shrink-0 cursor-pointer place-items-center rounded-full transition-colors hover:bg-line hover:text-ink ${
          open ? "bg-line text-ink" : "text-ink-soft"
        } ${className}`}
      >
        <AddIcon size={size} />
      </button>

      <Popover open={open} onClose={close} anchor={button} placement={placement} label={strings.addToPlaylist.heading}>
        {/* Mounted only while open, so lists of songs don't all load playlists */}
        <PlaylistChoices track={track} onDone={close} />
      </Popover>
    </>
  );
}

function PlaylistChoices({ track, onDone }: { track: Track; onDone: () => void }) {
  const { data: playlists, isPending, isError } = usePlaylists();
  const { notify } = usePlayback();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("");

  const add = useMutation({
    mutationFn: (playlist: PlaylistSummary) => api.addToPlaylist(playlist.id, [track.uri!]),
    onSuccess: (_, playlist) => {
      notify(strings.addToPlaylist.added(track.title, playlist.name));
      queryClient.invalidateQueries({ queryKey: ["playlists"] });
      queryClient.invalidateQueries({ queryKey: ["playlist", playlist.id] });
      queryClient.invalidateQueries({ queryKey: ["playlist-items", playlist.id] });
      onDone();
    },
    onError: (error) => {
      notify(
        error instanceof ApiError && error.status === 403
          ? strings.addToPlaylist.forbidden
          : strings.addToPlaylist.failed,
      );
    },
  });

  // Spotify only lets you add to playlists you own or collaborate on
  const editable = (playlists ?? []).filter((playlist) => playlist.is_owned);
  const query = filter.trim().toLowerCase();
  const shown = query ? editable.filter((p) => p.name.toLowerCase().includes(query)) : editable;

  return (
    <>
      <p className="px-2.5 pt-1.5 pb-2 text-sm font-[600] text-ink">{strings.addToPlaylist.heading}</p>

      {isError ? (
        <p className="px-2.5 pb-2 text-sm text-ink-soft">{strings.addToPlaylist.error}</p>
      ) : isPending ? (
        <p className="px-2.5 pb-2 text-sm text-ink-faint">{strings.addToPlaylist.loading}</p>
      ) : editable.length === 0 ? (
        <p className="px-2.5 pb-2 text-sm text-ink-soft">{strings.addToPlaylist.none}</p>
      ) : (
        <>
          {editable.length >= FILTER_FROM && (
            <input
              type="search"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              placeholder={strings.addToPlaylist.filter}
              aria-label={strings.addToPlaylist.filter}
              autoFocus
              className="mx-1 mb-1.5 h-9 w-[calc(100%-0.5rem)] rounded-lg bg-line px-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            />
          )}
          {shown.length === 0 ? (
            <p className="px-2.5 pb-2 text-sm text-ink-faint">{strings.addToPlaylist.noMatch}</p>
          ) : (
            <ul>
              {shown.map((playlist) => (
                <li key={playlist.id}>
                  <button
                    type="button"
                    disabled={add.isPending}
                    onClick={() => add.mutate(playlist)}
                    className="flex w-full cursor-pointer items-center gap-3 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-line disabled:cursor-progress"
                  >
                    <PlaylistCover name={playlist.name} imageUrl={playlist.image_url} className="size-9 shrink-0 text-[0.45rem]" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-ink">{playlist.name}</span>
                      {playlist.track_count != null && (
                        <span className="block text-xs text-ink-faint">{strings.library.songs(playlist.track_count)}</span>
                      )}
                    </span>
                    {add.isPending && add.variables?.id === playlist.id && (
                      <span className="size-3.5 animate-spin rounded-full border-2 border-ink-faint border-t-transparent" aria-hidden="true" />
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}
