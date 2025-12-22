import unittest

from src.data_models import AlignmentType, SectionPair
from src.text_aligner import sentence_aligner


class TestSentenceAligner(unittest.TestCase):
    def test_normalize_text_replaces_numbers_and_spaces(self):
        normalized = sentence_aligner.normalize_text("売上 1,234 円 増加")
        self.assertEqual(normalized, "売上<NUM>円増加")

    def test_split_sentences_handles_newlines(self):
        sentences = sentence_aligner.split_sentences("第一。第二\n第三。")
        self.assertEqual(sentences, ["第一。", "第二", "第三。"])

    def test_extract_headings_and_remove_tables(self):
        text = "I 概要\nこれは本文です。\n追加行"
        _, headings = sentence_aligner.extract_headings_and_remove_tables(text, threshold=40)
        self.assertEqual(headings, ["I 概要"])

    def test_find_ordered_matches_keeps_sequence(self):
        matches = sentence_aligner.find_ordered_matches(["A", "C"], ["A", "B", "C"])
        self.assertEqual(matches[0][0], 0)
        self.assertEqual(matches[1][0], 2)

    def test_align_sentences_returns_similarity_scores(self):
        old_text = "売上は増加。\n利益は横ばい。"
        new_text = "売上は増加。\n利益は減少。"
        alignments = sentence_aligner.align_sentences(old_text, new_text, [], [])
        self.assertEqual(len(alignments), 2)
        self.assertEqual(alignments[0].alignment_type, AlignmentType.MATCHED)
        self.assertLess(alignments[1].similarity_score, 1.0)

    def test_get_aligned_sentences_builds_pairs(self):
        section_pair = SectionPair(
            level=0,
            old_heading="1. 概要",
            new_heading="1. 概要",
            old_content="売上は増加。\n利益は横ばい。",
            new_content="売上は増加。\n利益は減少。",
            alignment_type=AlignmentType.MATCHED,
            similarity_score=1.0,
            heading_similarity_score=1.0,
            subsection_similarity_score=1.0,
            content_similarity_score=1.0,
        )

        results = sentence_aligner.get_aligned_sentences([section_pair])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].old_heading, "1. 概要")
        self.assertEqual(len(results[0].sentence_alignments), 2)
        self.assertEqual(results[0].sentence_alignments[0].alignment_type, AlignmentType.MATCHED)


if __name__ == "__main__":
    unittest.main()
