
import unittest

from src.app import app


class TestMusicCultureAPI(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_countries_endpoint(self):
        response = self.client.get("/api/countries")

        self.assertEqual(response.status_code, 200)

        countries = response.get_json()
        self.assertEqual(len(countries), 36)
        self.assertIn("Slovenia", countries)

    def test_observations_endpoint(self):
        response = self.client.get(
            "/api/observations?country=Slovenia"
        )

        self.assertEqual(response.status_code, 200)

        result = response.get_json()
        self.assertEqual(result["country"], "Slovenia")
        self.assertEqual(len(result["observations"]), 3)

        rates = {
            item["year"]: item["participation_rate"]
            for item in result["observations"]
        }

        self.assertEqual(rates["2006"], 40.2)
        self.assertEqual(rates["2015"], 56.8)
        self.assertEqual(rates["2022"], 32.7)

    def test_observations_year_filter(self):
        response = self.client.get(
            "/api/observations"
            "?country=Slovenia&years=2015,2022"
        )

        self.assertEqual(response.status_code, 200)

        result = response.get_json()
        years = [
            item["year"]
            for item in result["observations"]
        ]

        self.assertEqual(years, ["2015", "2022"])

    def test_unknown_country(self):
        response = self.client.get(
            "/api/observations?country=Atlantis"
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.get_json())

    def test_missing_country_parameter(self):
        response = self.client.get("/api/observations")

        self.assertEqual(response.status_code, 400)

    def test_comparison_endpoint(self):
        response = self.client.get(
            "/api/comparison"
            "?countries=Slovenia,Austria,Croatia"
            "&years=2015,2022"
        )

        self.assertEqual(response.status_code, 200)

        result = response.get_json()
        self.assertEqual(len(result["observations"]), 6)
        self.assertEqual(
            set(result["countries"]),
            {"Slovenia", "Austria", "Croatia"},
        )

    def test_comparison_rejects_unknown_country(self):
        response = self.client.get(
            "/api/comparison?countries=Slovenia,Atlantis"
        )

        self.assertEqual(response.status_code, 404)

    def test_ranking_endpoint(self):
        response = self.client.get(
            "/api/ranking?year=2022&limit=5"
        )

        self.assertEqual(response.status_code, 200)

        result = response.get_json()
        ranking = result["ranking"]

        self.assertEqual(len(ranking), 5)
        self.assertEqual(ranking[0]["country"], "Luxembourg")
        self.assertEqual(ranking[0]["participation_rate"], 48.5)
        self.assertEqual(
            [item["rank"] for item in ranking],
            [1, 2, 3, 4, 5],
        )

    def test_ranking_rejects_invalid_year(self):
        response = self.client.get(
            "/api/ranking?year=2020"
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_observation_is_json_null(self):
        response = self.client.get(
            "/api/observations?country=Germany&years=2022"
        )

        self.assertEqual(response.status_code, 200)

        observation = response.get_json()["observations"][0]
        self.assertIsNone(observation["participation_rate"])


if __name__ == "__main__":
    unittest.main()
