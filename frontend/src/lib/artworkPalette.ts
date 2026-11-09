// Derives the page's colors from the album cover.
//
// The cover is shrunk to 24x24 pixels, pixels are grouped by hue, and the
// hue with the most "colorful weight" wins. From that hue we build a dark
// background and a light accent, so text contrast is always safe no matter
// what the artwork looks like.

export interface Palette {
  background: string;
  backgroundDeep: string;
  accent: string;
}

export const DEFAULT_PALETTE: Palette = {
  background: "hsl(222 24% 15%)",
  backgroundDeep: "hsl(222 28% 9%)",
  accent: "hsl(216 100% 81%)",
};

const cache = new Map<string, Palette>();

function rgbToHsl(r: number, g: number, b: number) {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return { h: 0, s: 0, l };

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h =
    max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h *= 60;
  return { h, s, l };
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous"; // Spotify's image CDN allows this
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

export async function paletteFromArtwork(url: string): Promise<Palette> {
  const cached = cache.get(url);
  if (cached) return cached;

  const img = await loadImage(url);
  const size = 24;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return DEFAULT_PALETTE;

  ctx.drawImage(img, 0, 0, size, size);
  const { data } = ctx.getImageData(0, 0, size, size);

  // 24 hue buckets of 15 degrees each
  const buckets = Array.from({ length: 24 }, () => ({ weight: 0, s: 0 }));
  let grey = 0;

  for (let i = 0; i < data.length; i += 4) {
    const { h, s, l } = rgbToHsl(data[i], data[i + 1], data[i + 2]);
    // Ignore near-black/near-white pixels; they say little about mood
    if (l < 0.08 || l > 0.94) continue;
    if (s < 0.15) {
      grey++;
      continue;
    }
    const bucket = buckets[Math.floor(h / 15) % 24];
    const weight = s * (1 - Math.abs(l - 0.5));
    bucket.weight += weight;
    bucket.s += s * weight;
  }

  let best = { weight: 0, s: 0, index: -1 };
  buckets.forEach((bucket, index) => {
    if (bucket.weight > best.weight) best = { ...bucket, index };
  });

  let palette: Palette;

  if (best.index < 0 || best.weight < grey * 0.05) {
    // Black-and-white artwork: a neutral, slightly warm stage
    palette = {
      background: "hsl(30 6% 15%)",
      backgroundDeep: "hsl(30 6% 8%)",
      accent: "hsl(40 30% 88%)",
    };
  } else {
    const hue = Math.round(best.index * 15 + 7.5);
    const sat = Math.min(1, best.s / best.weight);
    palette = {
      background: `hsl(${hue} ${Math.round(Math.min(55, sat * 60))}% 16%)`,
      backgroundDeep: `hsl(${hue} ${Math.round(Math.min(45, sat * 50))}% 8%)`,
      accent: `hsl(${hue} ${Math.round(Math.max(65, sat * 100))}% 80%)`,
    };
  }

  cache.set(url, palette);
  return palette;
}
