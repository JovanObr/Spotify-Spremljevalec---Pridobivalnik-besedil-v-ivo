interface Props {
  name: string;
  imageUrl: string | null;
  className?: string;
}

/** Playlist artwork, or the first letter of its name when there's none. */
export function PlaylistCover({ name, imageUrl, className = "" }: Props) {
  return (
    <div className={`overflow-hidden rounded-md bg-line ${className}`}>
      {imageUrl ? (
        <img src={imageUrl} alt="" loading="lazy" className="h-full w-full object-cover" />
      ) : (
        <div
          aria-hidden="true"
          className="grid h-full w-full place-items-center bg-gradient-to-br from-accent/30 to-bg-deep text-[2.5em] font-[720] text-ink-soft"
        >
          {name.trim().charAt(0).toUpperCase() || "♪"}
        </div>
      )}
    </div>
  );
}
