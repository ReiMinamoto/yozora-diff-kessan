import unittest

from src.data_models import AlignedSentence, AlignmentType, SentencePair
from src.llm_summarizer import edit_tagger


class TestEditTagger(unittest.TestCase):
    def test_replace_numbers_extracts_digits(self):
        replaced, nums = edit_tagger.replace_numbers("売上は1,234億円")
        self.assertEqual(replaced, "売上は<NUM>億円")
        self.assertEqual(nums, ["1,234"])

    def test_make_diff_marks_changes(self):
        diff = edit_tagger.make_diff("売上は100億円", "売上は120億円")
        self.assertEqual(diff, "<del>売上は100億円</del><add>売上は120億円</add>")

    def test_make_edit_unit_behaviour(self):
        added = AlignedSentence(old_sentence=None, new_sentence="新規文", similarity_score=0.0, alignment_type=AlignmentType.ADDED)
        deleted = AlignedSentence(old_sentence="削除文", new_sentence=None, similarity_score=0.0, alignment_type=AlignmentType.DELETED)
        unchanged = AlignedSentence(
            old_sentence="同じ文", new_sentence="同じ文", similarity_score=1.0, alignment_type=AlignmentType.MATCHED
        )

        added_text, next_id = edit_tagger.make_edit_unit(added, edit_id=0)
        self.assertEqual(added_text, "<edit 0><add>新規文</add></edit 0>")
        self.assertEqual(next_id, 1)

        deleted_text, next_id = edit_tagger.make_edit_unit(deleted, edit_id=next_id)
        self.assertEqual(deleted_text, "<edit 1><del>削除文</del></edit 1>")
        self.assertEqual(next_id, 2)

        unchanged_text, next_id = edit_tagger.make_edit_unit(unchanged, edit_id=next_id)
        self.assertEqual(unchanged_text, "同じ文")
        self.assertEqual(next_id, 2)

    def test_preprocess_sentence_pairs_increments_edit_ids(self):
        alignment1 = AlignedSentence(old_sentence="旧", new_sentence="新", similarity_score=0.0, alignment_type=AlignmentType.MATCHED)
        alignment2 = AlignedSentence(old_sentence=None, new_sentence="追加", similarity_score=0.0, alignment_type=AlignmentType.ADDED)

        pairs = [
            SentencePair(
                old_heading="1. 概要",
                new_heading="1. 概要",
                old_content="A",
                new_content="B",
                overall_similarity_score=0.0,
                sentence_alignments=[alignment1],
            ),
            SentencePair(
                old_heading="2. 詳細",
                new_heading="2. 詳細",
                old_content="C",
                new_content="D",
                overall_similarity_score=0.0,
                sentence_alignments=[alignment2],
            ),
        ]

        processed = edit_tagger.preprocess_sentence_pairs(pairs)

        self.assertEqual(len(processed), 2)
        self.assertIn("<edit 0>", processed[0]["processed_sentence_pair"])
        self.assertIn("<edit 1>", processed[1]["processed_sentence_pair"])
        self.assertEqual(processed[0]["edit_units"][0].startswith("<edit 0>"), True)
        self.assertEqual(processed[1]["edit_units"][0].startswith("<edit 1>"), True)


if __name__ == "__main__":
    unittest.main()
