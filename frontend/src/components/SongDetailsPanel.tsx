import type { CountryInfo, InfoField, Track } from "../api/types";
import { useDetails } from "../hooks/queries";
import { strings } from "../lib/strings";

// Song rows shown in the side panel, in this order (Wikipedia's labels)
const SONG_ROWS = ["Released", "Genre", "Length", "Label", "Songwriter(s)", "Producer(s)"];
const ARTIST_ROWS = ["Genres", "Years active"];

/**
 * "Song details" and "About the artist": scraped from Wikipedia by the
 * server, with the artist's country from CountryInfoService (SOAP).
 */
export function SongDetailsPanel({ track }: { track: Track }) {
  const { data, isPending, isError, refetch } = useDetails(track);

  return (
    <section aria-labelledby="details-heading" className="border-t border-line pt-5">
      <h2 id="details-heading" className="text-base font-[600] text-ink">
        {strings.details.heading}
      </h2>

      {isPending ? (
        <p className="mt-2 text-sm text-ink-faint" aria-live="polite">
          {strings.details.loading}
        </p>
      ) : isError ? (
        <div className="mt-2 text-sm text-ink-soft">
          <p>{strings.details.error}</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-2 cursor-pointer text-accent underline decoration-accent/40 underline-offset-4 hover:decoration-accent"
          >
            {strings.details.retry}
          </button>
        </div>
      ) : (
        <>
          {data.song ? (
            <>
              {data.song.album && (
                <p className="mt-2 text-sm text-ink-soft">{strings.details.fromAlbum(data.song.album)}</p>
              )}
              <Fields fields={data.song.fields} order={SONG_ROWS} />
              <a
                href={data.song.url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-block text-sm text-ink-faint underline decoration-line underline-offset-4 hover:text-ink"
              >
                {strings.details.readMore}
              </a>
            </>
          ) : (
            <p className="mt-2 text-sm text-ink-faint">{strings.details.notFound}</p>
          )}

          {data.artist && (
            <div className="mt-5">
              <h3 className="text-sm font-[600] text-ink">{strings.details.artistHeading}</h3>
              {data.artist.summary && (
                <p className="mt-2 text-[0.95rem] leading-relaxed text-ink-soft">{data.artist.summary}</p>
              )}
              {data.country ? (
                <Country country={data.country} origin={data.artist.origin} />
              ) : (
                data.errors.country && (
                  <p className="mt-2 text-sm text-ink-faint">{strings.details.countryUnavailable}</p>
                )
              )}
              <Fields fields={data.artist.fields} order={ARTIST_ROWS} />
              <a
                href={data.artist.url}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-block text-sm text-ink-faint underline decoration-line underline-offset-4 hover:text-ink"
              >
                {strings.details.readMore}
              </a>
            </div>
          )}

          {(data.song || data.artist) && (
            <p className="mt-3 text-xs text-ink-faint">{strings.details.attribution}</p>
          )}
        </>
      )}
    </section>
  );
}

function Fields({ fields, order }: { fields: InfoField[]; order: string[] }) {
  const shown = order
    .map((label) => fields.find((field) => field.label === label))
    .filter((field): field is InfoField => Boolean(field));
  if (shown.length === 0) return null;

  return (
    <dl className="mt-3 grid grid-cols-[minmax(5.5rem,auto)_1fr] gap-x-4 gap-y-1.5 text-sm">
      {shown.map((field) => (
        <div key={field.label} className="contents">
          <dt className="text-ink-faint">{field.label.replace("(s)", "s")}</dt>
          <dd className="text-ink-soft">{field.values.slice(0, 4).join(", ")}</dd>
        </div>
      ))}
    </dl>
  );
}

function Country({ country, origin }: { country: CountryInfo; origin: string | null }) {
  return (
    <div className="mt-3 flex items-start gap-3">
      {country.flag_url && (
        <img
          src={country.flag_url}
          alt={strings.details.flagAlt(country.name)}
          loading="lazy"
          className="mt-0.5 h-6 w-9 shrink-0 rounded-[3px] object-cover ring-1 ring-line"
          onError={(event) => (event.currentTarget.style.display = "none")}
        />
      )}
      <dl className="grid grid-cols-[minmax(5.5rem,auto)_1fr] gap-x-4 gap-y-1.5 text-sm">
        <dt className="text-ink-faint">{strings.details.country}</dt>
        <dd className="text-ink-soft">
          {country.name}
          {origin && <span className="text-ink-faint"> ({origin})</span>}
        </dd>
        {country.capital && (
          <>
            <dt className="text-ink-faint">{strings.details.capital}</dt>
            <dd className="text-ink-soft">{country.capital}</dd>
          </>
        )}
        {country.languages.length > 0 && (
          <>
            <dt className="text-ink-faint">{strings.details.language}</dt>
            <dd className="text-ink-soft">{country.languages.join(", ")}</dd>
          </>
        )}
        {country.currency && (
          <>
            <dt className="text-ink-faint">{strings.details.currency}</dt>
            <dd className="text-ink-soft">{country.currency}</dd>
          </>
        )}
      </dl>
    </div>
  );
}
