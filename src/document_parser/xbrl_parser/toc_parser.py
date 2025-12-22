"""
qualitative.htmから目次を抽出する処理。
"""

from __future__ import annotations

import logging
import os

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from src.document_parser.xbrl_parser.constants import (
    ATTACHMENT_DIR,
    AUTHOR_PRONEXUS,
    AUTHOR_TAKARA_PRINTING,
    HEADING_TAGS,
    PAGE_NUMBER_SEPARATOR,
    QUALITATIVE_HTML,
    REVIEW_REPORT_PATTERN,
    REVIEW_REPORT_TITLE,
    TOC_CHARS,
    TOC_CHARS_MINI,
    TOC_PATTERN,
    XBRL_DATA_DIR,
)
from src.document_parser.xbrl_parser.dom_utils import extract_content_from_element, find_next_sibling_element_skipping_tables
from src.document_parser.xbrl_parser.html_utils import extract_element_left_offset, normalize_text, parse_css_classes

logger = logging.getLogger(__name__)


def extract_author_from_meta(soup: BeautifulSoup) -> str | None:
    """
    <meta name="author">タグからauthor情報を取得する。

    Args:
        soup: 解析対象のBeautifulSoupオブジェクト。

    Returns:
        author情報。見つからない場合はNone。
    """
    meta_author = soup.find("meta", attrs={"name": "author"})
    if meta_author and meta_author.get("content"):
        author = meta_author.get("content")
        return author
    return None


def find_toc_heading(soup: BeautifulSoup) -> NavigableString:
    """
    目次の見出しを取得。

    Args:
        soup: 解析対象のBeautifulSoupオブジェクト。

    Returns:
        目次見出しに該当するテキストノード。

    Raises:
        ValueError: 見出しが見つからない場合。
    """
    toc_heading = soup.find(string=lambda text: text and all(char in text for char in TOC_CHARS))
    if not toc_heading:
        toc_heading = soup.find(string=lambda text: text and all(char in text for char in TOC_CHARS_MINI))
        if not toc_heading:
            raise ValueError("目次タグが見つかりません。")
    return toc_heading


def extract_toc_from_table(toc_table: Tag, css_classes: dict[str, dict[str, str]], author: str) -> list[tuple[float, float, str]]:
    """
    テーブル形式の目次を抽出する。

    Args:
        toc_table: 目次が書かれたテーブルタグ。
        css_classes: CSSクラス名とプロパティ辞書のマッピング。
        author: 作成者情報。

    Returns:
        (CSSオフセット, テキストオフセット, タイトル文字列)のリスト。
    """
    toc = []
    rows = toc_table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 1:
            title_cell = cells[0]
            title_p = title_cell.find("p")
            if title_p:
                title_text = normalize_text(title_p.get_text(strip=True))
                title_text = title_text.split(PAGE_NUMBER_SEPARATOR)[0].strip()
                if title_text:
                    css_offset, text_offset = extract_element_left_offset(title_p, css_classes, author)
                    toc.append((css_offset, text_offset, title_text))
    return toc


def extract_additional_toc_items(current_element: Tag | None, first_toc_title: str) -> list[tuple[float, float, str]]:
    """
    テーブル外にあるレビュー報告書などを追加抽出する。

    Args:
        current_element: 追加探索を開始する要素。
        first_toc_title: 目次の最初のタイトル(探索終了条件)。

    Returns:
        追加された目次項目のリスト。
    """
    additional_items = []
    while current_element:
        extracted_parts, _ = extract_content_from_element(current_element, 0)
        for extracted_part in extracted_parts:
            extracted_part = normalize_text(extracted_part)
            if extracted_part == first_toc_title:
                return additional_items
            if REVIEW_REPORT_PATTERN.search(extracted_part):
                additional_items.append((0, 0, extracted_part))
                logger.debug("レビュー報告書を目次に追加: %s", extracted_part)
                return additional_items
        current_element = find_next_sibling_element_skipping_tables(current_element)
    return additional_items


def extract_toc_from_paragraphs(
    current_element: Tag | None, css_classes: dict[str, dict[str, str]], author: str
) -> list[tuple[float, float, str]]:
    """
    <p>形式の目次を抽出する。

    Args:
        current_element: 目次候補の<p>タグが連続する先頭要素。
        css_classes: CSSクラス名とプロパティ辞書のマッピング。
        author: 作成者情報。

    Returns:
        (CSSオフセット, テキストオフセット, タイトル文字列)のリスト。
    """
    toc = []
    while current_element:
        if current_element.name in HEADING_TAGS:
            break

        if current_element.name == "p":
            title_text = normalize_text(current_element.get_text(strip=True))
            pattern_match = TOC_PATTERN.search(title_text)
            if pattern_match:
                title_text = pattern_match.group(1).strip()
                if title_text:
                    css_offset, text_offset = extract_element_left_offset(current_element, css_classes, author)
                    toc.append((css_offset, text_offset, title_text))

        current_element = current_element.find_next_sibling()
    return toc


def normalize_toc_offsets(toc: list[tuple[float, float, str]]) -> list[tuple[float, str]]:
    """
    目次データのオフセット値を正規化する。CSSオフセットとテキストオフセットの両方が存在する場合はCSSオフセットを優先。

    Args:
        toc: (CSSオフセット, テキストオフセット, タイトル文字列)のタプル一覧。

    Returns:
        正規化済みのオフセットとタイトルのタプル一覧。
    """
    final_toc: list[tuple[float, str]] = []
    for css_offset, text_offset, title_text in toc:
        if REVIEW_REPORT_PATTERN.search(title_text):
            if title_text != REVIEW_REPORT_TITLE:
                # プロネクサスでのみ必要: 目次のみ[期中レビュー報告書]になっているため標準化
                title_text = REVIEW_REPORT_TITLE
                logger.debug(f"レビュー報告書のタイトルを標準化: {title_text}")
        if css_offset > 0:
            final_toc.append((css_offset, title_text))
        else:
            final_toc.append((text_offset, title_text))
        if text_offset > 0:
            if css_offset > 0:
                logger.debug(
                    "CSS offset (%spx) and leading spaces (%spx) both exist. Using CSS offset. Text: %s",
                    css_offset,
                    text_offset,
                    title_text,
                )
            else:
                logger.debug("Leading spaces (%spx) exists. Text: %s", text_offset, title_text)
    return final_toc


def extract_table_of_contents(xbrl_path: str) -> list[tuple[float, str]]:
    """
    qualitative.htmから目次を抽出する。

    Args:
        xbrl_path: XBRLデータディレクトリのパス。

    Returns:
        オフセットとタイトル文字列のタプルリスト。

    Raises:
        ValueError: 目次が検出できない場合。
    """
    qualitative_path = os.path.join(xbrl_path, XBRL_DATA_DIR, ATTACHMENT_DIR, QUALITATIVE_HTML)
    with open(qualitative_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    author = extract_author_from_meta(soup)
    if author:
        logger.info(f"author情報を取得: {author}")

    css_classes = parse_css_classes(soup)
    toc_heading = find_toc_heading(soup)
    current_element = toc_heading.parent.find_next_sibling()
    if not current_element and toc_heading.parent.parent:
        current_element = toc_heading.parent.parent.find_next_sibling()

    if author == AUTHOR_PRONEXUS:
        toc_table = toc_heading.find_next("table")
        toc = extract_toc_from_table(toc_table, css_classes, author)
        additional_items = extract_additional_toc_items(current_element, toc[0][-1])
        toc.extend(additional_items)
    elif author == AUTHOR_TAKARA_PRINTING:
        toc = extract_toc_from_paragraphs(current_element, css_classes, author)
    else:
        raise ValueError("作成者が未対応です")

    toc = normalize_toc_offsets(toc)
    return toc
