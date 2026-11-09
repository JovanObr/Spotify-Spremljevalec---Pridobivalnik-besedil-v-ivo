import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from google.genai import errors

from services import ai_service
from services.ai_service import (
    AINotConfiguredError,
    AIServiceError,
    generate_track_facts,
)


CONFIG = ("test-key", "gemini-test-model")


class TestAIService(unittest.TestCase):

    def setUp(self):
        ai_service.clear_cache()

        self.client = MagicMock()
        self.client.interactions.create.return_value = SimpleNamespace(
            output_text='{"facts": ["Fact one.", "Fact two.", " "]}'
        )

        patches = [
            patch.object(ai_service, "get_gemini_config", return_value=CONFIG),
            patch.object(
                ai_service, "get_gemini_facts_model", return_value="gemini-test-model"
            ),
            patch.object(
                ai_service, "get_gemini_recommendations_model",
                return_value="gemini-recs-model",
            ),
            patch.object(ai_service, "_get_client", return_value=self.client),
        ]

        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_returns_facts_from_structured_response(self):
        facts = generate_track_facts("Example Artist", "Example Song")

        self.assertEqual(facts, ["Fact one.", "Fact two."])

        kwargs = self.client.interactions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-test-model")
        self.assertEqual(
            kwargs["response_format"]["mime_type"], "application/json"
        )
        self.assertIn("Example Song", kwargs["input"])
        # Gemini 3 models reject sampling parameters
        self.assertNotIn("temperature", kwargs.get("generation_config", {}))

    def test_flash_lite_uses_its_default_thinking(self):
        with patch.object(
            ai_service, "get_gemini_facts_model",
            return_value="gemini-3.5-flash-lite",
        ):
            generate_track_facts("A", "B")

        kwargs = self.client.interactions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-3.5-flash-lite")
        self.assertNotIn("generation_config", kwargs)

    def test_flash_uses_low_thinking(self):
        generate_track_facts("A", "B")

        kwargs = self.client.interactions.create.call_args.kwargs
        self.assertEqual(kwargs["generation_config"], {"thinking_level": "low"})

    def test_rejected_thinking_level_is_retried_without_it(self):
        self.client.interactions.create.side_effect = [
            errors.ClientError(400, {"error": {
                "code": 400,
                "message": "Thinking level LOW is not supported for this model.",
            }}),
            SimpleNamespace(output_text='{"facts": ["Ok."]}'),
        ]

        self.assertEqual(generate_track_facts("A", "B"), ["Ok."])
        retry = self.client.interactions.create.call_args_list[1].kwargs
        self.assertNotIn("generation_config", retry)

    def test_results_are_cached_per_track(self):
        generate_track_facts("Example Artist", "Example Song")
        generate_track_facts("Example Artist", "Example Song")
        generate_track_facts("Example Artist", "Other Song")

        self.assertEqual(self.client.interactions.create.call_count, 2)

    def test_language_is_included_in_prompt(self):
        generate_track_facts("A", "B", language="Slovenian")

        prompt = self.client.interactions.create.call_args.kwargs["input"]
        self.assertIn("Slovenian", prompt)

    def test_empty_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_track_facts(" ", "Song")

    def test_invalid_json_raises_service_error(self):
        self.client.interactions.create.return_value = SimpleNamespace(
            output_text="not json"
        )

        with self.assertRaises(AIServiceError):
            generate_track_facts("A", "B")

    def test_empty_response_raises_service_error(self):
        self.client.interactions.create.return_value = SimpleNamespace(
            output_text=None
        )

        with self.assertRaises(AIServiceError):
            generate_track_facts("A", "B")

    def test_api_error_keeps_status_code(self):
        self.client.interactions.create.side_effect = errors.ClientError(
            429, {"error": {"code": 429, "message": "quota"}}
        )

        with self.assertRaises(AIServiceError) as context:
            generate_track_facts("A", "B")

        self.assertEqual(context.exception.status_code, 429)

    def test_failures_are_not_cached(self):
        self.client.interactions.create.side_effect = [
            RuntimeError("network down"),
            SimpleNamespace(output_text='{"facts": ["Ok."]}'),
        ]

        with self.assertRaises(AIServiceError):
            generate_track_facts("A", "B")

        self.assertEqual(generate_track_facts("A", "B"), ["Ok."])

    def test_suggestions_use_main_model_and_are_cleaned(self):
        self.client.interactions.create.return_value = SimpleNamespace(
            output_text=(
                '{"songs": [{"title": " Song X ", "artist": "Band", "reason": "Same mood."},'
                ' {"title": " ", "artist": "Nobody", "reason": "x"}]}'
            )
        )

        songs = ai_service.suggest_similar_songs("Artist", "Song")

        self.assertEqual([(s.title, s.artist) for s in songs], [("Song X", "Band")])
        kwargs = self.client.interactions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-recs-model")
        self.assertIn("Do not include this song", kwargs["input"])

    def test_suggestions_are_cached(self):
        self.client.interactions.create.return_value = SimpleNamespace(
            output_text='{"songs": [{"title": "X", "artist": "Y", "reason": "Z"}]}'
        )

        ai_service.suggest_similar_songs("Artist", "Song")
        ai_service.suggest_similar_songs("Artist", "Song")

        self.assertEqual(self.client.interactions.create.call_count, 1)

    def _use_gemma(self):
        p = patch.object(
            ai_service, "get_gemini_recommendations_model",
            return_value="gemma-4-31b-it",
        )
        p.start()
        self.addCleanup(p.stop)

    def test_gemma_uses_generate_content_with_json_schema(self):
        self._use_gemma()
        self.client.models.generate_content.return_value = SimpleNamespace(
            text='{"songs": [{"title": "X", "artist": "Y", "reason": "Z"}]}'
        )

        songs = ai_service.suggest_similar_songs("Artist", "Song")

        self.assertEqual(songs[0].title, "X")
        self.client.interactions.create.assert_not_called()
        kwargs = self.client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemma-4-31b-it")
        self.assertEqual(kwargs["config"]["response_mime_type"], "application/json")
        self.assertNotIn("thinking_config", kwargs["config"])

    def test_gemma_falls_back_to_prompt_described_json(self):
        self._use_gemma()
        self.client.models.generate_content.side_effect = [
            errors.ClientError(400, {"error": {"code": 400, "message": "JSON mode is not enabled"}}),
            SimpleNamespace(
                text='Sure!\n```json\n{"songs": [{"title": "X", "artist": "Y", "reason": "Z"}]}\n```'
            ),
        ]

        songs = ai_service.suggest_similar_songs("Artist", "Song")

        self.assertEqual(songs[0].artist, "Y")
        retry = self.client.models.generate_content.call_args_list[1].kwargs
        self.assertNotIn("config", retry)
        self.assertIn("JSON schema", retry["contents"])
        self.assertIn("music curator", retry["contents"])  # system text folded in

    def test_gemma_quota_error_keeps_status(self):
        self._use_gemma()
        self.client.models.generate_content.side_effect = errors.ClientError(
            429, {"error": {"code": 429, "message": "quota"}}
        )

        with self.assertRaises(AIServiceError) as context:
            ai_service.suggest_similar_songs("Artist", "Song")

        self.assertEqual(context.exception.status_code, 429)

    def test_lenient_json_parsing(self):
        parsed = ai_service.parse_json_answer(
            'Here you go: {"facts": ["One."]} Hope that helps.', ai_service.TrackFacts
        )
        self.assertEqual(parsed.facts, ["One."])

        with self.assertRaises(AIServiceError):
            ai_service.parse_json_answer("no json here", ai_service.TrackFacts)

    def test_missing_api_key_raises_not_configured(self):
        with patch.object(
            ai_service,
            "get_gemini_config",
            side_effect=RuntimeError("Missing GEMINI_API_KEY"),
        ):
            with self.assertRaises(AINotConfiguredError):
                generate_track_facts("A", "B")


if __name__ == "__main__":
    unittest.main()
