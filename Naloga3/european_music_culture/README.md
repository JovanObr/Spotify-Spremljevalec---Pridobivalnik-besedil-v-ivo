# European Music Culture

A small data-driven web application that visualizes participation in live cultural performances across European countries using official Eurostat statistics. The dashboard provides country rankings and comparisons over time through interactive charts.

## Features

- **Country rankings:** Rank countries by their live-performance participation rate for a selected year.
- **Country comparisons:** Compare participation rates across multiple countries.
- **Interactive visualizations:** Explore rankings and trends using Plotly charts.
- **REST API:** Retrieve country lists, observations, comparisons, and rankings through Flask endpoints.
- **Missing-data handling:** Missing observations are represented as null values rather than zero.
- **Validated dataset:** The converted PC-Axis dataset was checked against the original Eurostat API response.

## Dataset

The application uses the Eurostat dataset:

**Persons participating in cultural or sport activities in the last 12 months by sex, age, educational attainment, activity type and frequency**

- **Dataset code:** `ilc_scp03`
- **Source:** [Eurostat Data Browser](https://ec.europa.eu/eurostat/databrowser/view/ilc_scp03/default/table?lang=en)
- **Data format:** PC-Axis (`.px`)
- **Countries:** 36 European countries
- **Years:** 2006, 2015, 2022
- **Unit:** Percentage of people

### Selected indicators

The dataset is filtered to include people who meet the following criteria:

| Dimension | Selection |
|---|---|
| Activity | Live performances (theatre, concerts, ballet) |
| Frequency | At least once in the last 12 months |
| Age | 16 years or over |
| Sex | Total |
| Educational attainment | All ISCED 2011 levels |
| Unit | Percentage |
| Time frequency | Annual |

The participation rate represents the percentage of people aged 16 or over who attended at least one qualifying live performance during the preceding 12 months.

**Important:** This indicator measures participation in live cultural performances. It does not measure the number of concerts held, music streaming activity, Spotify usage, or music popularity.

Only three years are included, so comparisons between years should not be interpreted as a continuous annual trend.

### Data quality and limitations

The dataset contains 108 possible country-year observations (36 countries × 3 years). Of these, 94 contain numeric values and 14 are missing.

Some observations have Eurostat status flags. These flags are preserved separately in `data/observation_status.csv` so that the original data-quality information is not silently discarded.

Missing observations are not treated as zero. They are excluded from country rankings and represented as null values in API responses and gaps in comparison charts.

The dataset does not include an EU-wide aggregate.

## Technology stack

- **Python** — data processing and application logic
- **Flask** — web application and REST API
- **pandas** — data manipulation
- **Pyaxis** — parsing PC-Axis data
- **Requests** — HTTP requests to the Eurostat API
- **HTML and CSS** — dashboard structure and styling
- **JavaScript** — frontend interactions and API requests
- **Plotly.js** — interactive charts
- **unittest** — automated API tests

## Project structure

```text
european_music_culture/
├── data/
│   ├── european_live_performances.px
│   ├── eurostat_response.json
│   └── observation_status.csv
├── scripts/
│   ├── inspect_dataset.py
│   ├── inspect_filtered_dataset.py
│   ├── covert_to_px.py
│   ├── validate_px.py
│   ├── verify_conversion.py
│   └── test_data_service.py
├── src/
│   ├── __init__.py
│   ├── data_service.py
│   ├── app.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── requirements.txt
├── .gitignore
└── README.md
```

The `data/` directory contains the converted dataset, the saved source API response, and observation status information. The `scripts/` directory contains utilities for inspecting, converting, and validating the data. The `src/` directory contains the data service, Flask application, templates, and frontend assets. The `tests/` directory contains automated API tests.

## Installation and setup

### Prerequisites

- Python 3.10 or newer
- `pip`
- An internet connection to load the Plotly.js CDN resource when viewing the dashboard

### 1. Clone or download the project

If using Git:

```bash
git clone <repository-url>
cd european_music_culture
```

If you already have the project locally, open a terminal in the project root instead.

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If you use Command Prompt instead of PowerShell:

```bat
.venv\Scripts\activate.bat
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running the application

From the project root, with the virtual environment activated, run:

```bash
python -m src.app
```

Open the local address printed by Flask in your browser, typically:

`http://127.0.0.1:5000/`

The dashboard displays a country ranking and allows you to compare selected countries across 2006, 2015, and 2022.

The application reads the local PC-Axis dataset, so the Eurostat API does not need to be queried every time the dashboard is opened.

## REST API

All endpoints are served by the Flask application.

### `GET /api/countries`

Returns the list of available countries.

Example:

```http
GET /api/countries
```

### `GET /api/observations`

Returns observations for one country.

Parameters:

- `country` — required country name
- `years` — optional comma-separated list of years

Example:

```http
GET /api/observations?country=Slovenia&years=2015,2022
```

### `GET /api/comparison`

Returns observations for multiple countries.

Parameters:

- `countries` — required comma-separated list of countries
- `years` — optional comma-separated list of years

Example:

```http
GET /api/comparison?countries=Slovenia,Austria,Croatia&years=2015,2022
```

### `GET /api/ranking`

Returns countries ranked by participation rate for a selected year.

Parameters:

- `year` — required year
- `limit` — optional maximum number of results
- `order` — optional sort order: `desc` or `asc` (defaults to descending)

Example:

```http
GET /api/ranking?year=2022&limit=5&order=desc
```

Invalid parameters produce appropriate HTTP error responses. Missing observations are returned as JSON `null` values where applicable.

## Running the tests

From the project root, activate the virtual environment and run:

```bash
python -m unittest discover -s tests -v
```

The automated tests cover country retrieval, country observations, year filtering, comparisons, rankings, invalid requests, unknown countries, and missing observations.

To run the data-service checks:

```bash
python -m scripts.test_data_service
```

To verify that the PC-Axis conversion matches the saved source data:

```bash
python -m scripts.verify_conversion
```

## Data conversion and validation

The dataset was retrieved from the Eurostat dissemination API and converted into PC-Axis format. The conversion was verified by comparing the parsed `.px` observations with the corresponding source API values.

The validation checked all 108 expected country-year combinations and confirmed that the converted values matched the source, including missing observations. Observation status flags are stored separately.

The conversion script is named `covert_to_px.py` in the current project structure.

## License and attribution

The statistical data is sourced from Eurostat. Consult the [Eurostat website](https://ec.europa.eu/eurostat) and the applicable data reuse conditions for attribution and reuse requirements.

The source code and its licensing terms should be specified by the project author if the project is distributed publicly.
