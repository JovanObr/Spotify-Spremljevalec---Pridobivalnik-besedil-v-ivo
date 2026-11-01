
import requests

URL = (
    "https://ec.europa.eu/eurostat/api/"
    "dissemination/statistics/1.0/data/ilc_scp03"
)

countries = [
    "BE", "BG", "CZ", "DK", "DE", "EE", "IE", "EL",
    "ES", "FR", "HR", "IT", "CY", "LV", "LT", "LU",
    "HU", "MT", "NL", "AT", "PL", "PT", "RO", "SI",
    "SK", "FI", "SE", "IS", "NO", "CH", "UK", "ME",
    "MK", "AL", "RS", "TR",
]

years = ["2006", "2015", "2022"]

# Use a list of tuples so repeated geo and time parameters
# can be sent to the API.
params = [
    ("lang", "en"),
    ("freq", "A"),
    ("frequenc", "GE1"),
    ("acl00", "AC522A"),
    ("isced11", "TOTAL"),
    ("age", "Y_GE16"),
    ("sex", "T"),
    ("unit", "PC"),
]

params.extend(("geo", country) for country in countries)
params.extend(("time", year) for year in years)

response = requests.get(URL, params=params, timeout=60)
response.raise_for_status()

dataset = response.json()

print("Dataset:", dataset.get("label"))
print("Source:", dataset.get("source"))
print("Dimensions:", dataset.get("id"))
print("Dimension sizes:", dataset.get("size"))
print("Number of returned observations:", len(dataset.get("value", {})))

print("\nReturned dimension categories:")

for dimension_name in dataset["id"]:
    dimension = dataset["dimension"][dimension_name]
    categories = dimension["category"]
    labels = categories.get("label", {})

    print(f"\n{dimension_name}: {dimension.get('label', '')}")

    for code in categories.get("index", {}):
        print(f"  {code}: {labels.get(code, code)}")

print("\nFirst five raw observations:")

values = dataset.get("value", {})

if isinstance(values, dict):
    for key, value in list(values.items())[:5]:
        print(f"  Index {key}: {value}")
else:
    for index, value in enumerate(values[:5]):
        print(f"  Index {index}: {value}")

print("\nAPI request URL:")
print(response.url)
