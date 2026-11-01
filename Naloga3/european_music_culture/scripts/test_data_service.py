
from src.data_service import (
    get_countries, 
    get_country_data, 
    load_data, 
    get_countries_data, 
    get_country_ranking)

data = load_data()

print("Total rows:", len(data))
print("Missing observations:", data["DATA"].isna().sum())

countries = get_countries()
print("\nNumber of countries:", len(countries))
print("First five countries:", countries[:5])

print("\nSlovenia — all available years:")
print(get_country_data("Slovenia"))

print("\nSlovenia — 2015 and 2022:")
print(get_country_data("slovenia", ["2015", "2022"]))

print("\nInvalid country:")
print(get_country_data("Atlantis"))

print("\nCountry comparison — 2015 and 2022:")
comparison = get_countries_data(
    ["Slovenia", "Austria", "Croatia"],
    ["2015", "2022"],
)
print(comparison)

print("\nRows returned:", len(comparison))
print("Countries returned:", sorted(comparison["geo"].unique()))
print("Years returned:", sorted(comparison["time"].unique()))


print("\nTop 5 countries in 2022:")
print(get_country_ranking("2022").head(5))

print("\nBottom 5 countries in 2022:")
print(get_country_ranking("2022", ascending=True).head(5))

print("\nCountries ranked in 2022:")
print(len(get_country_ranking("2022")))

print("\nRanking for an unavailable year:")
print(get_country_ranking("1999"))


print("\nData completeness by year:")

data = load_data()

for year, group in data.groupby("time"):
    total = len(group)
    available = group["DATA"].notna().sum()
    missing = group["DATA"].isna().sum()

    print(
        f"{year}: {available}/{total} available, "
        f"{missing} missing"
    )
