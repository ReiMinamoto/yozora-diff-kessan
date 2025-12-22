import unittest

from src.data_models import AlignedSentence, AlignmentType, Section, SectionPair, SentencePair


class TestSection(unittest.TestCase):
    def test_section_round_trip(self):
        child = Section(level=1, heading_text="Child", content="child content")
        section = Section(level=0, heading_text="Root", content="root content", subsections=[child])

        serialized = section.to_dict()
        recreated = Section.from_dict(serialized)

        self.assertEqual(serialized, recreated.to_dict())


class TestSectionPair(unittest.TestCase):
    def test_section_pair_round_trip(self):
        child_pair = SectionPair(
            level=1,
            old_heading="Old child",
            new_heading="New child",
            old_content="child old",
            new_content="child new",
            alignment_type=AlignmentType.MATCHED,
            similarity_score=0.9,
            heading_similarity_score=0.9,
            subsection_similarity_score=0.0,
            content_similarity_score=0.8,
        )
        pair = SectionPair(
            level=0,
            old_heading="Old root",
            new_heading="New root",
            old_content="old content",
            new_content="new content",
            alignment_type=AlignmentType.MATCHED,
            similarity_score=0.8,
            heading_similarity_score=0.8,
            subsection_similarity_score=0.1,
            content_similarity_score=0.7,
            subsections=[child_pair],
        )

        serialized = pair.to_dict()
        recreated = SectionPair.from_dict(serialized)

        self.assertEqual(serialized, recreated.to_dict())
        self.assertEqual(recreated.subsections[0].alignment_type, AlignmentType.MATCHED)


class TestSentenceModels(unittest.TestCase):
    def test_sentence_pair_round_trip(self):
        aligned = AlignedSentence(old_sentence="old", new_sentence="new", similarity_score=0.5, alignment_type=AlignmentType.MATCHED)
        pair = SentencePair(
            old_heading="Old heading",
            new_heading="New heading",
            old_content="old body",
            new_content="new body",
            overall_similarity_score=0.4,
            sentence_alignments=[aligned],
        )

        serialized = pair.to_dict()
        recreated = SentencePair.from_dict(serialized)

        self.assertEqual(serialized, recreated.to_dict())
        self.assertEqual(recreated.sentence_alignments[0].alignment_type, AlignmentType.MATCHED)


if __name__ == "__main__":
    unittest.main()
