
from flask import Flask, jsonify, request, render_template
import pandas as pd
from src.data_service import (
    get_countries, 
    get_country_data, 
    get_countries_data, 
    get_country_ranking)


app = Flask(__name__)

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/countries")
def countries():
    """Return all countries available in the dataset."""
    return jsonify(get_countries())


VALID_YEARS = {"2006", "2015", "2022"}


@app.get("/api/observations")
def observations():
    """Return observations for one country, optionally filtered by year."""
    country = request.args.get("country", "").strip()

    if not country:
        return jsonify({"error": "The 'country' parameter is required."}), 400

    available_countries = get_countries()
    matching_country = next(
        (
            name
            for name in available_countries
            if name.casefold() == country.casefold()
        ),
        None,
    )

    if matching_country is None:
        return jsonify({"error": f"Unknown country: {country}"}), 404

    years_parameter = request.args.get("years")
    years = None

    if years_parameter is not None:
        years = [year.strip() for year in years_parameter.split(",")]

        if not years or any(year not in VALID_YEARS for year in years):
            return jsonify({
                "error": "Years must be selected from 2006, 2015, and 2022."
            }), 400

        if len(years) != len(set(years)):
            return jsonify({"error": "Duplicate years are not allowed."}), 400

    data = get_country_data(matching_country, years)

    records = [
        {
            "country": row.geo,
            "year": row.time,
            "participation_rate": (
                None if pd.isna(row.DATA) else float(row.DATA)
            ),
        }
        for row in data.itertuples(index=False)
    ]

    return jsonify({
        "country": matching_country,
        "observations": records,
    })


@app.get("/api/comparison")
def comparison():
    """Compare multiple countries across selected years."""
    countries_parameter = request.args.get("countries", "").strip()

    if not countries_parameter:
        return jsonify({
            "error": "The 'countries' parameter is required."
        }), 400

    requested_countries = [
        country.strip()
        for country in countries_parameter.split(",")
    ]

    if any(not country for country in requested_countries):
        return jsonify({
            "error": "Country names must not be empty."
        }), 400

    if len(requested_countries) != len(
        {country.casefold() for country in requested_countries}
    ):
        return jsonify({
            "error": "Duplicate countries are not allowed."
        }), 400

    available_countries = get_countries()
    country_lookup = {
        country.casefold(): country
        for country in available_countries
    }

    unknown_countries = [
        country
        for country in requested_countries
        if country.casefold() not in country_lookup
    ]

    if unknown_countries:
        return jsonify({
            "error": "Unknown countries.",
            "countries": unknown_countries,
        }), 404

    normalized_countries = [
        country_lookup[country.casefold()]
        for country in requested_countries
    ]

    if len(normalized_countries) > 36:
        return jsonify({
            "error": "You can compare at most 36 countries."
        }), 400

    years_parameter = request.args.get("years")
    years = None

    if years_parameter is not None:
        years = [year.strip() for year in years_parameter.split(",")]

        if any(year not in VALID_YEARS for year in years):
            return jsonify({
                "error": "Years must be selected from 2006, 2015, and 2022."
            }), 400

        if len(years) != len(set(years)):
            return jsonify({
                "error": "Duplicate years are not allowed."
            }), 400

    data = get_countries_data(normalized_countries, years)

    records = [
        {
            "country": row.geo,
            "year": row.time,
            "participation_rate": (
                None if pd.isna(row.DATA) else float(row.DATA)
            ),
        }
        for row in data.itertuples(index=False)
    ]

    return jsonify({
        "countries": normalized_countries,
        "years": years if years is not None else sorted(data["time"].unique()),
        "observations": records,
    })


@app.get("/api/ranking")
def ranking():
    """Return countries ranked by participation rate for a given year."""
    year = request.args.get("year", "").strip()

    if not year:
        return jsonify({
            "error": "The 'year' parameter is required."
        }), 400

    if year not in VALID_YEARS:
        return jsonify({
            "error": "Year must be one of 2006, 2015, or 2022."
        }), 400

    order = request.args.get("order", "desc").strip().lower()

    if order not in {"asc", "desc"}:
        return jsonify({
            "error": "Order must be either 'asc' or 'desc'."
        }), 400

    limit_parameter = request.args.get("limit")

    if limit_parameter is None:
        limit = None
    else:
        try:
            limit = int(limit_parameter)
        except ValueError:
            return jsonify({
                "error": "Limit must be a positive integer."
            }), 400

        if limit <= 0:
            return jsonify({
                "error": "Limit must be a positive integer."
            }), 400

        limit = min(limit, 36)

    data = get_country_ranking(
        year,
        ascending=(order == "asc"),
    )

    if limit is not None:
        data = data.head(limit)

    records = [
        {
            "rank": int(row.rank),
            "country": row.geo,
            "year": row.time,
            "participation_rate": float(row.DATA),
        }
        for row in data.itertuples(index=False)
    ]

    return jsonify({
        "year": year,
        "order": order,
        "count": len(records),
        "ranking": records,
    })


if __name__ == "__main__":
    app.run(debug=True)
