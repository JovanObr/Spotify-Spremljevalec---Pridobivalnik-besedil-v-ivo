
import requests

URL = (
    "https://ec.europa.eu/eurostat/api/"
    "dissemination/statistics/1.0/data/ilc_scp03"
)

response = requests.get(URL, params={"lang": "en"}, timeout=60)
response.raise_for_status()

dataset = response.json()

print("Dataset:", dataset.get("label", "ilc_scp03"))
print("\nDimensions:")

for dimension_name in dataset["id"]:
    dimension = dataset["dimension"][dimension_name]
    categories = dimension["category"]

    print(f"\n{dimension_name}: {dimension.get('label', '')}")

    labels = categories.get("label", {})
    indexes = categories.get("index", {})

    if isinstance(indexes, dict):
        for code, index in sorted(
            indexes.items(), key=lambda item: item[1]
        ):
            print(f"  {code}: {labels.get(code, code)}")
    else:
        for code, label in labels.items():
            print(f"  {code}: {label}")

print("\nNumber of observations:", len(dataset.get("value", {})))
