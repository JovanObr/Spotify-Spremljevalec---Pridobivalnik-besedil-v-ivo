import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.app import app
from services import ai_service
from services.ai_service import AINotConfiguredError, AIServiceError
from services.lyrics_service import Lyrics


def make_lyrics(synced=None, plain=None, instrumental=False):
    return Lyrics(
        track_name="Song", artist_name="Artist", album_name=None,
        plain_lyrics=plain, synced_lyrics=synced, instrumental=instrumental,
    )


class TestTranslateLyrics(unittest.TestCase):

    def setUp(self):
        ai_service.clear_cache()
        self.ask = MagicMock()
        for p in [
            patch.object(ai_service, "get_gemini_config", return_value=("k", "m")),
            patch.object(ai_service, "get_gemini_facts_model", return_value="facts-model"),
            patch.object(ai_service, "get_gemini_recommendations_model", return_value="recs-model"),
            patch.object(ai_service, "_ask", self.ask),
        ]:
            p.start()
            self.addCleanup(p.stop)

    def answer(self, pairs):
        return ai_service.Translation(
            lines=[ai_service.LineTranslation(n=n, text=t) for n, t in pairs]
        )

    def test_repeated_lines_are_sent_once_and_mapped_back(self):
        self.ask.return_value = self.answer([(1, "Hola"), (2, "Adiós")])

        result = ai_service.translate_lyrics(
            "A", "B", ["Hello", "", "Goodbye", "Hello"], "Spanish"
        )

        self.assertEqual(result, ["Hola", "", "Adiós", "Hola"])
        model, _, prompt, schema = self.ask.call_args.args
        self.assertEqual(model, "facts-model")
        self.assertIs(schema, ai_service.Translation)
        self.assertEqual(prompt.count("Hello"), 1)
        self.assertIn("Spanish", prompt)

    def test_missing_lines_become_empty(self):
        self.ask.return_value = self.answer([(2, "Adiós")])

        result = ai_service.translate_lyrics("A", "B", ["Hello", "Goodbye"], "Spanish")

        self.assertEqual(result, ["", "Adiós"])

    def test_empty_answer_is_an_error(self):
        self.ask.return_value = self.answer([])

        with self.assertRaises(AIServiceError):
            ai_service.translate_lyrics("A", "B", ["Hello"], "Spanish")

    def test_cached_per_language(self):
        self.ask.return_value = self.answer([(1, "Hola")])

        ai_service.translate_lyrics("A", "B", ["Hello"], "Spanish")
        ai_service.translate_lyrics("A", "B", ["Hello"], "Spanish")
        self.assertEqual(self.ask.call_count, 1)

        ai_service.translate_lyrics("A", "B", ["Hello"], "German")
        self.assertEqual(self.ask.call_count, 2)

    def test_rejects_empty_language(self):
        with self.assertRaises(ValueError):
            ai_service.translate_lyrics("A", "B", ["Hello"], " ")

    def test_not_configured(self):
        with patch.object(ai_service, "is_configured", return_value=False):
            with self.assertRaises(AINotConfiguredError):
                ai_service.translate_lyrics("A", "B", ["Hello"], "Spanish")


class TestExplainSong(unittest.TestCase):

    def setUp(self):
        ai_service.clear_cache()
        self.ask = MagicMock(return_value=ai_service.SongMeaning(
            summary=" About leaving home. ", themes=["home", " ", "change"]
        ))
        for p in [
            patch.object(ai_service, "get_gemini_config", return_value=("k", "m")),
            patch.object(ai_service, "get_gemini_recommendations_model", return_value="recs-model"),
            patch.object(ai_service, "_ask", self.ask),
        ]:
            p.start()
            self.addCleanup(p.stop)

    def test_uses_lyrics_and_recommendations_model(self):
        meaning = ai_service.explain_song("A", "B", "Album", "line one\nline two")

        self.assertEqual(meaning.summary, "About leaving home.")
        self.assertEqual(meaning.themes, ["home", "change"])
        model, instruction, prompt, _ = self.ask.call_args.args
        self.assertEqual(model, "recs-model")
        self.assertIn("line two", prompt)
        self.assertIn("never quote", instruction)

    def test_without_lyrics(self):
        ai_service.explain_song("A", "B")

        prompt = self.ask.call_args.args[2]
        self.assertIn("No lyrics available", prompt)

    def test_cached(self):
        ai_service.explain_song("A", "B", lyrics="x")
        ai_service.explain_song("A", "B", lyrics="x")

        self.assertEqual(self.ask.call_count, 1)

    def test_empty_summary_is_an_error(self):
        self.ask.return_value = ai_service.SongMeaning(summary=" ", themes=[])

        with self.assertRaises(AIServiceError):
            ai_service.explain_song("A", "B")


class TestPhase6Api(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    @patch("services.ai_service.translate_lyrics", return_value=["Hola", "Adiós"])
    @patch("services.lyrics_service.get_lyrics")
    def test_translation_uses_synced_lines(self, get_lyrics, translate):
        get_lyrics.return_value = make_lyrics(
            synced="[00:01.00]Hello\n[00:02.00]Goodbye", plain="Hello\nGoodbye"
        )

        response = self.client.get("/api/lyrics/translation", params={
            "artist": "A", "title": "B", "language": "Spanish",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"language": "Spanish", "lines": ["Hola", "Adiós"]})
        translate.assert_called_with("A", "B", ["Hello", "Goodbye"], "Spanish")

    @patch("services.ai_service.translate_lyrics", return_value=["X"])
    @patch("services.lyrics_service.get_lyrics")
    def test_translation_falls_back_to_plain_lines(self, get_lyrics, translate):
        get_lyrics.return_value = make_lyrics(plain="One\nTwo")

        self.client.get("/api/lyrics/translation", params={
            "artist": "A", "title": "B", "language": "Spanish",
        })

        translate.assert_called_with("A", "B", ["One", "Two"], "Spanish")

    @patch("services.lyrics_service.get_lyrics", return_value=None)
    def test_translation_without_lyrics_is_404(self, _):
        response = self.client.get("/api/lyrics/translation", params={
            "artist": "A", "title": "B", "language": "Spanish",
        })
        self.assertEqual(response.status_code, 404)

    @patch("services.ai_service.translate_lyrics",
           side_effect=AIServiceError("quota", status_code=429))
    @patch("services.lyrics_service.get_lyrics")
    def test_translation_rate_limited(self, get_lyrics, _):
        get_lyrics.return_value = make_lyrics(plain="One")

        response = self.client.get("/api/lyrics/translation", params={
            "artist": "A", "title": "B", "language": "Spanish",
        })
        self.assertEqual(response.status_code, 429)

    @patch("services.ai_service.translate_lyrics",
           side_effect=AINotConfiguredError("no key"))
    @patch("services.lyrics_service.get_lyrics")
    def test_translation_not_configured(self, get_lyrics, _):
        get_lyrics.return_value = make_lyrics(plain="One")

        response = self.client.get("/api/lyrics/translation", params={
            "artist": "A", "title": "B", "language": "Spanish",
        })
        self.assertEqual(response.status_code, 503)

    @patch("services.ai_service.explain_song")
    @patch("services.lyrics_service.get_lyrics")
    def test_meaning_with_lyrics(self, get_lyrics, explain):
        get_lyrics.return_value = make_lyrics(plain="One\n\nTwo")
        explain.return_value = ai_service.SongMeaning(summary="S.", themes=["t"])

        data = self.client.get("/api/meaning", params={"artist": "A", "title": "B"}).json()

        self.assertEqual(data, {"summary": "S.", "themes": ["t"], "based_on_lyrics": True})
        explain.assert_called_with("A", "B", None, "One\nTwo", "English")

    @patch("services.ai_service.explain_song")
    @patch("services.lyrics_service.get_lyrics", side_effect=ValueError("bad"))
    def test_meaning_survives_lyrics_failure(self, _, explain):
        explain.return_value = ai_service.SongMeaning(summary="S.", themes=[])

        data = self.client.get("/api/meaning", params={"artist": "A", "title": "B"}).json()

        self.assertFalse(data["based_on_lyrics"])
        explain.assert_called_with("A", "B", None, None, "English")


if __name__ == "__main__":
    unittest.main()
