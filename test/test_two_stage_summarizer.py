import sys
import types
import unittest
from unittest import mock

if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda: None)
if "google" not in sys.modules:
    sys.modules["google"] = types.SimpleNamespace(genai=types.SimpleNamespace(Client=type("DummyClient", (), {})))
if "google.genai" not in sys.modules:
    sys.modules["google.genai"] = sys.modules["google"].genai
if "openai" not in sys.modules:
    sys.modules["openai"] = types.SimpleNamespace(OpenAI=type("DummyOpenAI", (), {}))

from src.llm_summarizer import two_stage_summarizer


class TestTwoStageSummarizer(unittest.TestCase):
    def test_fallback_stage1_when_no_data(self):
        output = two_stage_summarizer._fallback_stage1([])
        self.assertIn("差分データがありません", output)

    def test_two_stage_summarize_uses_fallback_when_client_missing(self):
        processed = [
            {
                "old_heading": "1. A",
                "new_heading": "1. A",
                "processed_sentence_pair": "<edit 0><add>x</add></edit 0>",
                "edit_units": [],
            }
        ]

        with (
            mock.patch("src.llm_summarizer.two_stage_summarizer.CLIENT", None),
            mock.patch("src.llm_summarizer.two_stage_summarizer._fallback_stage1", return_value="stage1") as stage1_mock,
            mock.patch("src.llm_summarizer.two_stage_summarizer._fallback_stage2", return_value="stage2") as stage2_mock,
        ):
            output = two_stage_summarizer.two_stage_summarize(processed)

        stage1_mock.assert_called_once_with(processed)
        stage2_mock.assert_called_once_with(processed)
        self.assertEqual(output, {"stage1": "stage1", "stage2": "stage2"})


if __name__ == "__main__":
    unittest.main()
