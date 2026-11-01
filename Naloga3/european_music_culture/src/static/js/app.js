
const rankingYear = document.getElementById("ranking-year");
const rankingChart = document.getElementById("ranking-chart");
const rankingStatus = document.getElementById("ranking-status");

const countrySelect = document.getElementById("comparison-countries");
const compareButton = document.getElementById("compare-button");
const comparisonChart = document.getElementById("comparison-chart");
const comparisonStatus = document.getElementById("comparison-status");

const YEARS = ["2006", "2015", "2022"];

async function fetchJson(url) {
    const response = await fetch(url);
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || `Request failed: ${response.status}`);
    }

    return result;
}

function showError(element, message) {
    element.textContent = message;
}

async function loadRanking() {
    rankingStatus.textContent = "Loading ranking...";

    try {
        const year = rankingYear.value;
        const result = await fetchJson(
            `/api/ranking?year=${encodeURIComponent(year)}&limit=10`
        );

        const countries = result.ranking.map(item => item.country);
        const rates = result.ranking.map(item => item.participation_rate);

        await Plotly.react(
            rankingChart,
            [{
                type: "bar",
                orientation: "h",
                x: rates,
                y: countries,
                marker: { color: "#4776c5" },
                text: rates.map(value => `${value}%`),
                textposition: "auto",
                hovertemplate: "%{y}<br>Participation: %{x}%<extra></extra>"
            }],
            {
                margin: { l: 125, r: 30, t: 15, b: 55 },
                xaxis: {
                    title: "People participating (%)",
                    rangemode: "tozero"
                },
                yaxis: {
                    autorange: "reversed"
                },
                showlegend: false,
                paper_bgcolor: "white",
                plot_bgcolor: "white"
            },
            { responsive: true }
        );

        rankingStatus.textContent =
            `Showing ${result.count} countries with available data for ${year}.`;
    } catch (error) {
        showError(rankingStatus, `Could not load ranking: ${error.message}`);
    }
}

async function loadCountries() {
    countrySelect.innerHTML = "";

    const countries = await fetchJson("/api/countries");

    for (const country of countries) {
        const option = document.createElement("option");
        option.value = country;
        option.textContent = country;

        if (["Slovenia", "Austria", "Croatia"].includes(country)) {
            option.selected = true;
        }

        countrySelect.appendChild(option);
    }
}

async function loadComparison() {
    const countries = Array.from(countrySelect.selectedOptions)
        .map(option => option.value);

    if (countries.length === 0) {
        showError(comparisonStatus, "Select at least one country.");
        return;
    }

    if (countries.length > 10) {
        showError(comparisonStatus, "Please select no more than 10 countries.");
        return;
    }

    comparisonStatus.textContent = "Loading comparison...";

    try {
        const params = new URLSearchParams({
            countries: countries.join(",")
        });

        const result = await fetchJson(`/api/comparison?${params}`);

        const traces = countries.map(country => {
            const observations = result.observations.filter(
                item => item.country === country
            );

            const valuesByYear = new Map(
                observations.map(item => [
                    item.year,
                    item.participation_rate
                ])
            );

            return {
                type: "scatter",
                mode: "lines+markers",
                name: country,
                x: YEARS,
                y: YEARS.map(year => valuesByYear.get(year) ?? null),
                connectgaps: false,
                hovertemplate:
                    `${country}<br>Year: %{x}<br>Participation: %{y}%<extra></extra>`
            };
        });

        await Plotly.react(
            comparisonChart,
            traces,
            {
                margin: { l: 65, r: 25, t: 20, b: 55 },
                xaxis: {
                    title: "Year",
                    type: "category",
                    categoryorder: "array",
                    categoryarray: YEARS
                },
                yaxis: {
                    title: "People participating (%)",
                    rangemode: "tozero"
                },
                legend: { orientation: "h", y: -0.25 },
                hovermode: "x unified",
                paper_bgcolor: "white",
                plot_bgcolor: "white"
            },
            { responsive: true }
        );

        comparisonStatus.textContent =
            `Comparing ${countries.length} countries. Missing observations are shown as gaps.`;
    } catch (error) {
        showError(
            comparisonStatus,
            `Could not load comparison: ${error.message}`
        );
    }
}

rankingYear.addEventListener("change", loadRanking);
compareButton.addEventListener("click", loadComparison);

async function initialize() {
    try {
        await loadCountries();
        await Promise.all([loadRanking(), loadComparison()]);
    } catch (error) {
        showError(
            comparisonStatus,
            `Could not initialize the dashboard: ${error.message}`
        );
    }
}

initialize();
