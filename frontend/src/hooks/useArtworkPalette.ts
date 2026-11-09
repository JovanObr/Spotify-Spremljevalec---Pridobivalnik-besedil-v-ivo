import { useEffect, useState } from "react";

import {
  DEFAULT_PALETTE,
  type Palette,
  paletteFromArtwork,
} from "../lib/artworkPalette";

/** Applies colors taken from the album cover to the whole page. */
export function useArtworkPalette(artworkUrl: string | null | undefined) {
  const [palette, setPalette] = useState<Palette>(DEFAULT_PALETTE);

  useEffect(() => {
    let cancelled = false;

    if (!artworkUrl) {
      setPalette(DEFAULT_PALETTE);
      return;
    }

    paletteFromArtwork(artworkUrl)
      .then((next) => !cancelled && setPalette(next))
      .catch(() => !cancelled && setPalette(DEFAULT_PALETTE));

    return () => {
      cancelled = true;
    };
  }, [artworkUrl]);

  useEffect(() => {
    const root = document.documentElement.style;
    root.setProperty("--c-bg", palette.background);
    root.setProperty("--c-bg-deep", palette.backgroundDeep);
    root.setProperty("--c-accent", palette.accent);
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", palette.backgroundDeep);
  }, [palette]);

  return palette;
}
