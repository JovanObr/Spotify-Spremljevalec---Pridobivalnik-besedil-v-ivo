
import json
from pathlib import Path

import pandas as pd
from pyaxis import pyaxis


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

JSON_PATH = DATA_DIR / "eurostat_response.json"
PX_PATH = DATA_DIR / "european_live_performances.px"
STATUS_PATH = DATA_DIR / "observation_status.csv"


def get_value(collection, index):
    """Read an observation from a sparse or dense JSON-stat array."""
    if isinstance(collection, dict):
        return collection.get(str(index))

    if isinstance(collection, list) and index < len(collection):
        return collection[index]

    return None


# 1. Load the original API response.
with JSON_PATH.open(encoding="utf-8") as file:
    original = json.load(file)

dimensions = original["dimension"]
geo = dimensions["geo"]["category"]
time = dimensions["time"]["category"]

geo_indexes = geo["index"]
time_indexes = time["index"]
geo_labels = geo["label"]

years = sorted(time_indexes, key=time_indexes.get)
countries = sorted(geo_indexes, key=geo_indexes.get)

original_values = original.get("value", {})
original_status = original.get("status", {})

# 2. Parse the generated PC-Axis file.
parsed = pyaxis.parse(str(PX_PATH), encoding="utf-8")
data = parsed["DATA"].copy()

data["geo"] = data["geo"].astype(str)
data["time"] = data["time"].astype(str).str.strip()

# Normalize the parsed values. Missing PC-Axis values may
# appear as empty strings, whitespace, or NaN.
data["DATA"] = pd.to_numeric(data["DATA"], errors="coerce")

parsed_lookup = {
    (row.geo, row.time): row.DATA
    for row in data.itertuples(index=False)
}

# 3. Compare every country-year observation.
checks = []

for country in countries:
    for year in years:
        index = (
            geo_indexes[country] * len(years)
            + time_indexes[year]
        )

        expected = get_value(original_values, index)
        status = get_value(original_status, index)

        country_name = geo_labels.get(country, country)
        actual = parsed_lookup.get((country_name, year))

        if expected is None:
            passed = pd.isna(actual)
            reason = "Missing value preserved" if passed else (
                "Expected missing value"
            )
        else:
            expected = float(expected)

            passed = (
                not pd.isna(actual)
                and abs(float(actual) - expected) < 0.000001
            )

            reason = "Value preserved" if passed else (
                f"Expected {expected}, got {actual}"
            )

        checks.append({
            "country": country_name,
            "year": year,
            "expected": expected,
            "actual": actual,
            "status": status,
            "passed": passed,
            "result": reason,
        })

results = pd.DataFrame(checks)

print("Total observations checked:", len(results))
print("Passed:", int(results["passed"].sum()))
print("Failed:", int((~results["passed"]).sum()))

if not results["passed"].all():
    print("\nFailed checks:")
    print(
        results.loc[
            ~results["passed"],
            ["country", "year", "expected", "actual", "result"],
        ].to_string(index=False)
    )

print("\nMissing observations:")
print(int(results["expected"].isna().sum()))

print("\nObservations with status flags:")
flagged = results[results["status"].notna()]
print(len(flagged))

if not flagged.empty:
    print(flagged[["country", "year", "expected", "status"]].to_string(
        index=False
    ))

print("\nStatus flag counts:")
if STATUS_PATH.exists():
    flags = pd.read_csv(STATUS_PATH)
    if flags.empty:
        print("No flags recorded.")
    else:
        print(flags["status"].value_counts(dropna=False).to_string())

if results["passed"].all():
    print("\nSUCCESS: All converted observations match the source.")
else:
    raise SystemExit("\nERROR: Conversion verification failed.")
