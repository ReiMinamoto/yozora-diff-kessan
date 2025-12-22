"""
DOM走査に関するヘルパー。
"""

from __future__ import annotations

import logging

from bs4.element import NavigableString, Tag

from src.document_parser.xbrl_parser.constants import REVIEW_REPORT_TITLE, TABLE_PLACEHOLDER_FORMAT
from src.document_parser.xbrl_parser.html_utils import normalize_text

logger = logging.getLogger(__name__)


def extract_content_from_element(
    element: Tag | NavigableString,
    table_counter: int,
    table_replacements: list[tuple[str, str]] | None = None,
) -> tuple[list[str], int]:
    """
    要素からテキストを抽出し、テーブルはプレースホルダー化する。

    Args:
        element: 抽出対象のHTML要素またはテキスト。
        table_counter: プレースホルダー用の連番カウンター。
        table_replacements: プレースホルダーと元テーブル文字列の対応を格納するリスト。
            テーブルを置換する際に追記する。不要ならNone。

    Returns:
        テキストパーツのリストと、次に使用するテーブルカウンターの値。
    """
    if isinstance(element, NavigableString):
        text = normalize_text(str(element))
        return ([text] if text else []), table_counter

    if not isinstance(element, Tag):
        text = normalize_text(str(element).strip())
        return ([text] if text else []), table_counter

    if element.name == "table":
        table_text = normalize_text(element.get_text(strip=True))
        if REVIEW_REPORT_TITLE in table_text:
            for td in element.find_all("td"):
                td_text = normalize_text(td.get_text(strip=True))
                if REVIEW_REPORT_TITLE in td_text:
                    # プロネクサスでのみ必要: レビュー報告書のタイトルが構造化に必要だが、表に含まれるので抽出する
                    logger.debug(f"表からレビュー報告書のタイトルを抽出: {td_text}")
                    return [td_text], table_counter

        placeholder = TABLE_PLACEHOLDER_FORMAT.format(table_counter)
        if table_replacements is not None:
            table_replacements.append((placeholder, table_text))
        return [placeholder], table_counter + 1

    parts: list[str] = []
    for child in element.children:
        child_parts, table_counter = extract_content_from_element(child, table_counter, table_replacements)
        parts.extend(child_parts)
    return parts, table_counter


def find_next_sibling_element_skipping_tables(element: Tag | NavigableString) -> Tag | None:
    """
    テーブル内部に潜らず兄弟要素を探索する。

    Args:
        element: 探索の起点となる要素またはテキストノード。

    Returns:
        見つかった次の兄弟タグ。見つからない場合はNone。
    """
    current = element
    while current:
        nxt = current.find_next_sibling()
        if nxt:
            return nxt
        current = current.parent
    return None
