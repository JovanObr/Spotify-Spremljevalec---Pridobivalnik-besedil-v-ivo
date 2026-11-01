
import csv
import json
from datetime import date
from pathlib import Path

import requests


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

PX_PATH = DATA_DIR / "european_live_performances.px"
RAW_JSON_PATH = DATA_DIR / "eurostat_response.json"
STATUS_PATH = DATA_DIR / "observation_status.csv"

API_URL = (
    "https://ec.europa.eu/eurostat/api/"
    "dissemination/statistics/1.0/data/ilc_scp03"
)

COUNTRIES = [
    "BE", "BG", "CZ", "DK", "DE", "EE", "IE", "EL",
    "ES", "FR", "HR", "IT", "CY", "LV", "LT", "LU",
    "HU", "MT", "NL", "AT", "PL", "PT", "RO", "SI",
    "SK", "FI", "SE", "IS", "NO", "CH", "UK", "ME",
    "MK", "AL", "RS", "TR",
]

YEARS = ["2006", "2015", "2022"]

FILTERS = [
    ("lang", "en"),
    ("freq", "A"),
    ("frequenc", "GE1"),
    ("acl00", "AC522A"),
    ("isced11", "TOTAL"),
    ("age", "Y_GE16"),
    ("sex", "T"),
    ("unit", "PC"),
]

SOURCE_URL = (
    "https://ec.europa.eu/eurostat/databrowser/view/"
    "ilc_scp03/default/table?lang=en"
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def quote_px(text):
    """Quote a string for a PC-Axis metadata value."""
    text = str(text).replace('"', '""')
    return f'"{text}"'


def px_list(values):
    """Format a list of strings as PC-Axis values."""
    return ",".join(quote_px(value) for value in values)


def get_sparse_value(collection, index):
    """
    JSON-stat may represent observations as a sparse
    dictionary or as a dense list.
    """
    if isinstance(collection, dict):
        return collection.get(str(index))

    if isinstance(collection, list):
        if 0 <= index < len(collection):
            return collection[index]

    return None


# --------------------------------------------------
# 1. Download the selected Eurostat observations
# --------------------------------------------------

params = list(FILTERS)
params.extend(("geo", country) for country in COUNTRIES)
params.extend(("time", year) for year in YEARS)

response = requests.get(API_URL, params=params, timeout=60)
response.raise_for_status()

dataset = response.json()

# Keep the original API response for reproducibility.
RAW_JSON_PATH.write_text(
    json.dumps(dataset, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

dimensions = dataset["dimension"]

geo_dimension = dimensions["geo"]["category"]
time_dimension = dimensions["time"]["category"]

geo_indexes = geo_dimension["index"]
time_indexes = time_dimension["index"]

geo_labels = geo_dimension["label"]
time_labels = time_dimension["label"]

# Order the dimensions using the positions defined by
# the API, not alphabetically.
countries = sorted(
    geo_indexes,
    key=lambda code: geo_indexes[code],
)

years = sorted(
    time_indexes,
    key=lambda year: time_indexes[year],
)

values = dataset.get("value", {})
statuses = dataset.get("status", {})

# The response dimensions are:
# freq, frequenc, acl00, isced11, age, sex, unit, geo, time
#
# The first seven dimensions each have one category.
# Therefore, the flattened JSON-stat index is:
# geo_index * number_of_years + time_index

number_of_years = len(years)

observations = []
status_records = []

for country in countries:
    for year in years:
        flat_index = (
            geo_indexes[country] * number_of_years
            + time_indexes[year]
        )

        value = get_sparse_value(values, flat_index)
        status = get_sparse_value(statuses, flat_index)

        if value is None:
            px_value = "."
        else:
            # Reject unexpected non-numeric observations.
            numeric_value = float(value)

            if not 0 <= numeric_value <= 100:
                raise ValueError(
                    f"Unexpected percentage: {country}, "
                    f"{year}, {value}"
                )

            px_value = f"{numeric_value:.1f}"

        observations.append({
            "country": country,
            "year": year,
            "value": px_value,
            "status": status,
        })

        # Preserve quality/status flags outside the PX file
        # so they can be inspected without losing their codes.
        if status is not None:
            status_records.append({
                "country": country,
                "year": year,
                "value": px_value,
                "status": status,
            })


# --------------------------------------------------
# 2. Create a country-by-year lookup
# --------------------------------------------------

lookup = {
    (item["country"], item["year"]): item["value"]
    for item in observations
}


# --------------------------------------------------
# 3. Generate the PC-Axis file
# --------------------------------------------------

country_names = [geo_labels.get(code, code) for code in countries]

lines = [
    'AXIS-VERSION="2013";',
    'CHARSET="UTF-8";',
    'LANGUAGE="en";',
    'MATRIX="LIVEPERF";',
    'SUBJECT-AREA="Culture";',
    'SUBJECT-CODE="CULT";',
    'CONTENTS="Participation in live performances";',
    (
        'TITLE="People aged 16 and over attending live '
        'performances at least once";'
    ),
    'DESCRIPTION="Percentage of people aged 16 or over who '
    'participated in live performances at least once in the '
    'previous 12 months. Live performances include theatre, '
    'concerts and ballet.";'
    ,
    'UNITS="Percent";',
    'DECIMALS=1;',
    'SHOWDECIMALS=1;',
    f'SOURCE="Eurostat, dataset ilc_scp03. {SOURCE_URL}";',
    f'CREATION-DATE="{date.today().isoformat()}";',
    'STUB="geo";',
    'HEADING="time";',
    f'VALUES("geo")={px_list(country_names)};',
    f'CODES("geo")={px_list(countries)};',
    f'VALUES("time")={px_list(years)};',
    f'CODES("time")={px_list(years)};',
    'DATASYMBOL1=".";',
    'DATA=',
]

# PC-Axis data is written row by row:
# one country per row, with one value per year.
for country in countries:
    row = [
        lookup[(country, year)]
        for year in years
    ]

    formatted_row = [
        quote_px(value) if value == "." else value
        for value in row
    ]

    lines.append(" ".join(formatted_row))

# DATA is the final keyword. Do not add metadata after it.
PX_PATH.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)


# --------------------------------------------------
# 4. Preserve observation status flags
# --------------------------------------------------

with STATUS_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as csv_file:
    writer = csv.DictWriter(
        csv_file,
        fieldnames=["country", "year", "value", "status"],
    )

    writer.writeheader()
    writer.writerows(status_records)


# --------------------------------------------------
# 5. Report conversion results
# --------------------------------------------------

numeric_count = sum(
    item["value"] != "."
    for item in observations
)

missing_count = len(observations) - numeric_count

print("Conversion completed.")
print(f"PC-Axis file: {PX_PATH}")
print(f"Raw API response: {RAW_JSON_PATH}")
print(f"Observation flags: {STATUS_PATH}")
print(f"Countries: {len(countries)}")
print(f"Years: {len(years)}")
print(f"Total country-year cells: {len(observations)}")
print(f"Numeric observations: {numeric_count}")
print(f"Missing observations: {missing_count}")
print(f"Status flags preserved: {len(status_records)}")
