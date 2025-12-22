import logging
import re
import unicodedata

import fitz

from src.data_models import Section
from src.document_parser.text_utils import normalize_newlines

# 定数定義
TOC_CHARS = ["添", "付", "資", "料", "目", "次"]
TOC_CHARS_MINI = ["目", "次"]
TOC_PATTERN = re.compile(r"(.+?)\s*[\.・]+[\s\n]*([0-9]+)")
HEADER_PATTERN = r"\([0-9]{3}[0-9A-Z]\).*決算短信"
PAGE_PLACEHOLDER = "{i}"
PATTERN_LAYER1 = re.compile(r"^\d+\.")
PATTERN_LAYER2 = re.compile(r"^\(\d+\)")
REVIEW_REPORT_PATTERN = re.compile(r"期中レビュー報告書")
REVIEW_REPORT_TITLE = "独立監査人の四半期連結財務諸表に対する期中レビュー報告書"

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    テキストを正規化する関数

    Args:
        text (str): 正規化するテキスト

    Returns:
        str: 正規化されたテキスト(NFKC正規化済み、改行以外の空白文字除去済み)
    """
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\S\n]+", "", text)
    return text


def extract_toc_from_page(text: str, page_number: int) -> tuple[list[dict[str, str | int]], str, str]:
    """
    ページテキストから目次を抽出する共通処理

    Args:
        text: ページのテキスト
        page_number: ページ番号

    Returns:
        tuple: (目次リスト, ヘッダー文字列, フッター文字列)
    """
    toc = []
    header = ""
    footer = ""

    norm_text = normalize_text(text)
    pattern = re.compile(HEADER_PATTERN, re.DOTALL)
    m = re.search(pattern, norm_text)
    if m:
        footers = ["", ""]
        start = norm_text.rfind("\n", 0, m.start())  # -1の場合も+1で0になるのでOK
        end = norm_text.find("\n", m.end())
        header = norm_text[start + 1 : end + 1]
        if start != -1:
            prev_start = norm_text.rfind("\n", 0, start)
            if prev_start != -1:
                footer = norm_text[prev_start + 1 : start]
                if footer:
                    footers[0] = footer
        if end != -1:
            next_end = norm_text.find("\n", end + 1)
            if next_end != -1:
                footer = norm_text[end + 1 : next_end]
                if footer:
                    footers[1] = footer

        for footer in footers:
            if footer:
                if "1" in footer:
                    footer = footer.replace("1", PAGE_PLACEHOLDER) + "\n"
                else:
                    footer = footer + "\n" + PAGE_PLACEHOLDER + "\n" + footer
                break

    titles = []
    for match in TOC_PATTERN.finditer(norm_text):
        title, page = match.groups()
        if not title:
            continue
        title = title.strip()
        toc.append({"title": normalize_text(title), "page": int(page) + page_number - 1})
        titles.append(normalize_text(title))

    if REVIEW_REPORT_PATTERN.search(norm_text) and not any(REVIEW_REPORT_PATTERN.search(title) for title in titles):
        toc.append({"title": REVIEW_REPORT_TITLE, "page": int(page) + page_number - 1})

    return toc, header, footer


def search_toc_with_chars(
    doc: fitz.Document, chars: list[str], toc_page_found: bool
) -> tuple[list[dict[str, str | int]], str, str, bool, int]:
    """
    指定された文字リストで目次を検索する

    Args:
        doc: PDFドキュメント
        chars: 検索に使用する文字リスト
        toc_page_found: 目次ページが見つかったかどうか

    Returns:
        tuple: (目次リスト, ヘッダー文字列, フッター文字列, 目次ページが見つかったかどうか, 目次ページ番号)
    """
    header = ""
    footer = ""
    for page in doc:
        text = page.get_text()
        if all(char in text for char in chars):
            toc_page_found = True
            toc, header, footer = extract_toc_from_page(text, page.number)
            if toc:
                return toc, header, footer, toc_page_found, page.number
    return [], header, footer, toc_page_found, 0


def process_toc(doc: fitz.Document) -> tuple[list[dict[str, str | int]], str, str, int]:
    """
    目次、ヘッダーとフッター、目次ページ番号を返す関数

    Args:
        doc: PDFドキュメント

    Returns:
        tuple: (見出しテキストとページ番号のリスト, ヘッダー文字列, フッター文字列, 目次ページ番号)

    Raises:
        ValueError: 目次または目次テーブルが見つからない場合
    """
    toc_page_found = False

    toc, header, footer, toc_page_found, toc_page_number = search_toc_with_chars(doc, TOC_CHARS, toc_page_found)

    if not toc:
        toc, header, footer, toc_page_found, toc_page_number = search_toc_with_chars(doc, TOC_CHARS_MINI, toc_page_found)
    if not toc_page_found:
        raise ValueError("目次ページが見つかりません")
    if not header or not footer:
        logger.warning("ヘッダーかフッターが見つかりません")
    if not toc:
        raise ValueError("目次が見つかりません")
    return toc, header, footer, toc_page_number


def remove_tables(pdf_path: str, page_num: int) -> str:
    """
    指定されたページから表を除いた本文テキストを抽出。
    リダクションを一時的に使用して表のテキストを無効化する。

    Args:
        pdf_path: PDFファイルへのパス (str)
        page_num: 抽出するページ番号(int)

    Returns:
        表を除いた本文テキスト (str)
    """
    doc = fitz.open(pdf_path)

    temp_doc = fitz.open()
    temp_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    temp_page = temp_doc[0]

    tabs = temp_page.find_tables()

    for tab in tabs:
        rect = tab.bbox
        temp_page.add_redact_annot(rect, fill=(1, 0, 0))
    temp_page.apply_redactions()
    body_text = temp_page.get_text()

    temp_doc.close()
    doc.close()

    return body_text


def extract_text(pdf_path: str, page_num: int, section_title: str, next_title: str, header: str, footer: str) -> str:
    """
    表の除去、ヘッダーとフッターの除去、セクションの切り出しを行う

    Args:
        pdf_path: PDFファイルのパス
        page_num: ページ番号
        section_title: セクションのタイトル
        next_title: 次のセクションのタイトル
        header: ヘッダー
        footer: フッター

    Returns:
        str: セクションのテキスト
    """
    text = remove_tables(pdf_path, page_num)
    text = normalize_text(text)

    if header:
        text = text.replace(header, "")
    if footer:
        text = text.replace(footer, "")

    if section_title in text:
        text = text[text.find(section_title) + len(section_title) + 1 :]
    if next_title and next_title in text:
        next_title_pos = text.find(next_title)
        last_newline_pos = text.rfind("\n", 0, next_title_pos)
        if last_newline_pos == -1:
            text = ""
        else:
            text = text[:last_newline_pos]
    return text


def structure_heading(heading_text: str, base_level: int) -> tuple[int, str]:
    """
    heading_textをPATTERN_LAYER1とPATTERN_LAYER2を使って階層レベルと見出しテキストを判定する

    Args:
        heading_text: 構造化する見出しテキスト
        base_level: ベースとなる階層レベル

    Returns:
        tuple: (階層レベル, 見出しテキスト)
    """
    heading_stripped = heading_text.strip()

    if PATTERN_LAYER1.match(heading_stripped) or REVIEW_REPORT_TITLE == heading_stripped:
        return (base_level, heading_stripped)

    elif PATTERN_LAYER2.match(heading_stripped):
        return (base_level + 1, heading_stripped)

    return (base_level + 2, heading_stripped)


def parse_document(pdf_path: str) -> list[Section]:
    """
    ドキュメントを解析する関数

    Args:
        pdf_path: PDFファイルのパス

    Returns:
        list[Section]: セクションのリスト
    """
    doc = fitz.open(pdf_path)
    try:
        total_pages = len(doc)

        toc, header, footer, toc_page_number = process_toc(doc)

        result: list[Section] = []

        for i, section in enumerate(toc):
            text = ""
            if i == len(toc) - 1:
                next_title = ""
                next_page = total_pages
            else:
                next_title = toc[i + 1]["title"]
                next_page = toc[i + 1]["page"] + 1
            for j in range(section["page"], next_page):
                current_footer = footer.format(i=j - toc_page_number + 1) if footer else ""
                text += extract_text(pdf_path, j, section["title"], next_title, header, current_footer)

            text = normalize_newlines(text)
            heading_text = section["title"]
            level, normalized_heading = structure_heading(heading_text, base_level=0)
            new_section = Section(level=level, heading_text=normalized_heading, content=text, subsections=[])

            if i == 0:
                result.append(new_section)
            else:
                if level == 0:
                    result.append(new_section)
                elif level == 1:
                    result[-1].add_subsection(new_section)
                elif level == 2:
                    if result[-1].subsections:
                        result[-1].subsections[-1].add_subsection(new_section)
                    else:
                        result[-1].add_subsection(new_section)

        return result
    finally:
        doc.close()
