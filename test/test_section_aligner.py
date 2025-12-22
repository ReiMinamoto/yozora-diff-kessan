import unittest

from src.data_models import AlignmentType, Section
from src.text_aligner import section_aligner


class TestSectionAligner(unittest.TestCase):
    def test_flatten_single_ixbrl_subsection_promotes_content(self):
        parent = Section(
            level=0,
            heading_text="Parent",
            content="",
            subsections=[
                Section(level=1, heading_text="Child1", content="child1_ixbrl.htm"),
                Section(level=1, heading_text="Child2", content="child2_ixbrl.htm"),
            ],
        )

        section_aligner.flatten_single_ixbrl_subsection(parent)

        self.assertEqual(parent.content, "child1_ixbrl.htm, child2_ixbrl.htm")
        self.assertEqual(parent.subsections, [])

    def test_align_sections_matches_and_marks_additions(self):
        old_sections = [Section(level=0, heading_text="1. Intro", content="old content")]
        new_sections = [
            Section(level=0, heading_text="1. Intro", content="new content"),
            Section(level=0, heading_text="2. Added", content=""),
        ]

        result = section_aligner.align_sections(old_sections, new_sections)

        self.assertEqual(result[0].alignment_type, AlignmentType.MATCHED)
        self.assertEqual(result[1].alignment_type, AlignmentType.ADDED)
        self.assertIsNone(result[1].old_heading)
        self.assertEqual(result[1].new_heading, "2. Added")

    def test_align_sections_uses_optimal_matching_for_notes(self):
        old_sections = [
            Section(level=0, heading_text="(資産セクション)", content="A"),
            Section(level=0, heading_text="(負債セクション)", content="B"),
        ]
        new_sections = [
            Section(level=0, heading_text="(負債セクション)", content="B updated"),
            Section(level=0, heading_text="(資産セクション改訂)", content="A updated"),
        ]

        result = section_aligner.align_sections(old_sections, new_sections)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].new_heading, "(資産セクション改訂)")
        self.assertEqual(result[1].new_heading, "(負債セクション)")


if __name__ == "__main__":
    unittest.main()
