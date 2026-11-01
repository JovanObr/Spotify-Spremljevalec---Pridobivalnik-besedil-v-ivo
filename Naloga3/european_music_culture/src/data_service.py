
from pathlib import Path

import pandas as pd
from pyaxis import pyaxis


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PX_PATH = PROJECT_ROOT / "data" / "european_live_performances.px"


def load_data() -> pd.DataFrame:
    """Load the Eurostat PC-Axis dataset into a DataFrame."""
    parsed = pyaxis.parse(str(PX_PATH), encoding="utf-8")

    data = parsed["DATA"].copy()
    data["geo"] = data["geo"].astype(str)
    data["time"] = data["time"].astype(str).str.strip()
    data["DATA"] = pd.to_numeric(data["DATA"], errors="coerce")

    return data


def get_countries() -> list[str]:
    """Return all available country names in alphabetical order."""
    data = load_data()
    return sorted(data["geo"].unique().tolist())


def get_country_data(
    country: str,
    years: list[str] | None = None,
) -> pd.DataFrame:
    """Return observations for one country, optionally filtered by year."""
    data = load_data()

    filtered = data[data["geo"].str.casefold() == country.casefold()]

    if years is not None:
        filtered = filtered[filtered["time"].isin(years)]

    return filtered.sort_values("time").reset_index(drop=True)


def get_countries_data(
    countries: list[str],
    years: list[str] | None = None,
) -> pd.DataFrame:
    """Return observations for multiple countries, optionally filtered by year."""
    data = load_data()

    country_names = {country.casefold() for country in countries}

    filtered = data[
        data["geo"].str.casefold().isin(country_names)
    ]

    if years is not None:
        filtered = filtered[filtered["time"].isin(years)]

    return filtered.sort_values(
        ["time", "geo"]
    ).reset_index(drop=True)


def get_country_ranking(
    year: str,
    ascending: bool = False,
) -> pd.DataFrame:
    """Rank countries by live-performance participation for one year."""
    data = load_data()

    filtered = data[data["time"] == year].copy()

    # Exclude missing observations from the ranking.
    filtered = filtered.dropna(subset=["DATA"])

    ranked = filtered.sort_values(
        "DATA",
        ascending=ascending,
    ).reset_index(drop=True)

    ranked.insert(0, "rank", range(1, len(ranked) + 1))

    return ranked
