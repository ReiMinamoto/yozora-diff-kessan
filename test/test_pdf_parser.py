import sys
import types
import unittest

if "fitz" not in sys.modules:
    sys.modules["fitz"] = types.SimpleNamespace(Document=object)

from src.document_parser import pdf_parser


class TestPdfParser(unittest.TestCase):
    def test_normalize_text_strips_spaces(self):
        text = "決算  123  テキスト"
        self.assertEqual(pdf_parser.normalize_text(text), "決算123テキスト")

    def test_structure_heading_levels(self):
        self.assertEqual(pdf_parser.structure_heading("1. 売上高", base_level=0), (0, "1. 売上高"))
        self.assertEqual(pdf_parser.structure_heading("(1) 営業利益", base_level=0), (1, "(1) 営業利益"))
        self.assertEqual(pdf_parser.structure_heading("その他", base_level=0), (2, "その他"))

    def test_extract_toc_from_page_parses_titles(self):
        page_text = """
前置き
(123A) 決算短信
ヘッダー行
売上........5
利益........10
期中レビュー報告書
"""
        toc, header, footer = pdf_parser.extract_toc_from_page(page_text, page_number=3)

        self.assertEqual(len(toc), 3)
        self.assertEqual(toc[0]["title"], "売上")
        self.assertEqual(toc[0]["page"], 7)
        self.assertEqual(toc[1]["page"], 12)
        self.assertEqual(toc[2]["title"], pdf_parser.REVIEW_REPORT_TITLE)
        self.assertIn("決算短信", header)
        self.assertIn("{i}", footer)


if __name__ == "__main__":
    unittest.main()
