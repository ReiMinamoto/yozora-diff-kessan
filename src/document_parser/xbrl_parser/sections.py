"""
iXBRLセクション解析処理。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
import logging
import os
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from src.document_parser.xbrl_parser.constants import (
    ATTACHMENT_DIR,
    COMPREHENSIVE_INCOME_KEYWORD,
    INCOME_STATEMENT_KEYWORD,
    MANIFEST_XML,
    PATTERN_LAYER2,
    PERIOD_KEYWORD,
    SPLIT_KEYWORD,
    XBRL_DATA_DIR,
)
from src.document_parser.xbrl_parser.dom_utils import extract_content_from_element, find_next_sibling_element_skipping_tables
from src.document_parser.xbrl_parser.html_utils import normalize_text

logger = logging.getLogger(__name__)


def _generate_additional_section_names(section_names: list[str]) -> tuple[list[str], dict[str, str]]:
    """
    連結損益計算書などの分割見出し、括弧付き見出しに対応する追加名称を生成。

    Args:
        section_names: 目次から取得した見出し名のリスト。

    Returns:
        追加で検出する見出し名のリストと、追加名から元の見出し名へのマッピング。
    """
    additional = []
    defaults = {}

    def register(name: str, original: str):
        """name と (name) の両方を original にマッピング"""
        defaults[name] = original
        defaults[f"({name})"] = original
        if name not in additional:
            additional.append(name)
        if f"({name})" not in additional:
            additional.append(f"({name})")

    for sec in section_names:
        if INCOME_STATEMENT_KEYWORD in sec and SPLIT_KEYWORD in sec and COMPREHENSIVE_INCOME_KEYWORD in sec:
            left, right = sec.split(SPLIT_KEYWORD, 1)
            if PATTERN_LAYER2.match(left):
                left = PATTERN_LAYER2.sub("", left).strip()
            for part in (left, right):
                register(part, sec)
            break

    for sec in section_names:
        if INCOME_STATEMENT_KEYWORD in sec and SPLIT_KEYWORD not in sec:
            register(sec, sec)
            break

    for sec in section_names:
        if COMPREHENSIVE_INCOME_KEYWORD in sec and SPLIT_KEYWORD not in sec:
            register(sec, sec)
            break

    for sec in section_names:
        if PERIOD_KEYWORD in sec:
            register(sec, sec)
            break

    return additional, defaults


def _find_initial_heading(soup: BeautifulSoup, section_names: list[str], additional_names: list[str], heading_only: bool):
    """
    解析開始となる見出し(NavigableString)を取得。

    Args:
        soup: 解析対象のBeautifulSoupオブジェクト。
        section_names: 目次に含まれる見出し名のリスト。
        additional_names: 追加名称のリスト。
        heading_only: 見出しのみを抽出するモードかどうか。

    Returns:
        見つかった見出しのテキストノード。存在しない場合はNone。
    """
    if heading_only:
        return soup.find(
            string=lambda text: (text and normalize_text(text) in section_names)
            or (text and normalize_text(text) in additional_names)
        )
    return soup.find(string=lambda text: text and normalize_text(text) == section_names[0])


def _find_toc_index(toc: list[tuple[float, str]], heading: str) -> int | None:
    """
    TOCから見出し名に対応するインデックスを返す。

    Args:
        toc: 目次のオフセットと見出しのリスト。
        heading: 探索対象の見出し名。

    Returns:
        見出しが一致するインデックス。見つからない場合はNone。
    """
    for idx, (_, title) in enumerate(toc):
        if title == heading:
            return idx
    return None


def _flush_section(
    sections: list[tuple[float, str, str]],
    toc: list[tuple[float, str]],
    current_index: int,
    content_elements: list[str],
    heading_only: bool,
    section_names: list[str],
    additional_section_names: list[str],
    default_section_names: dict[str, str],
    next_heading_text: str | None,
) -> None:
    """
    現在のセクション内容を確定させてリストへ追加する。
    目次に1つしかないタイトルが複数個存在する場合は、既存内容に「,」で接続する。
    同じタイトルが複数個存在する場合があるので、その場合は新規追加する。

    Args:
        sections: セクション結果を格納するリスト。
        toc: 目次のオフセットと見出しのリスト。
        current_index: 現在処理している目次のインデックス。
        content_elements: 現在のセクションに蓄積したコンテンツ要素。
        heading_only: 見出しのみ抽出モードかどうか。
        section_names: 目次に存在する見出し名のリスト。
        additional_section_names: 追加で扱う見出し名のリスト。
        default_section_names: 追加名称から既定名称へのマッピング。
        next_heading_text: 次に遭遇した見出しテキスト。
    """
    if current_index == -1:
        return

    level, heading = toc[current_index]
    if heading_only:
        if sections:
            section_title = (
                default_section_names.get(heading, heading)
                if (heading in additional_section_names and heading not in section_names)
                else heading
            )
            if any(section[1] == section_title for section in sections):
                return
        sections.append((level, heading, ""))
        return

    heading_count = sum(1 for _, title in toc if title == heading)
    if heading_count == 1:
        for i, (_, existing_heading, existing_content) in enumerate(sections):
            if existing_heading == heading:
                new_content = "\n".join(content_elements)
                if existing_content:
                    sections[i] = (level, heading, f"{existing_content}, {new_content}")
                    logger.debug(
                        "qualitative.htm内で目次に1つしかないセクションが複数見つかりました。内容を結合します: %s",
                        heading,
                    )
                else:
                    sections[i] = (level, heading, new_content)
                return

    sections.append((level, heading, "\n".join(content_elements)))


def parse_sections(
    file_path: str,
    toc: list[tuple[float, str]],
    heading_only: bool = False,
    table_replacements: list[tuple[str, str]] | None = None,
) -> list[tuple[float, str, str]]:
    """
    qualitative/iXBRLファイルからセクションを抽出する。

    Args:
        file_path: 対象となるHTMLまたはiXBRLファイルのパス。
        toc: 目次のオフセットと見出しのリスト。
        heading_only: 見出しだけを抽出するモードかどうか。
        table_replacements: プレースホルダーと元テーブル文字列の対応リスト。省略可。

    Returns:
        (レベル、見出し、内容)のタプルリスト。見出しのみの場合、内容は空文字となる。
    """
    with open(file_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    sections: list[tuple[float, str, str]] = []
    section_names = [c[1] for c in toc]

    additional_section_names, default_section_names = _generate_additional_section_names(section_names)

    initial_heading = _find_initial_heading(soup, section_names, additional_section_names, heading_only)
    current = initial_heading

    if not current:
        logger.warning("見出しが見つかりません: %s", file_path.split("/")[-1])
        return sections

    current = current.parent
    current_index = -1
    content_elements: list[str] = []
    table_count = 0

    while current:
        extracted_parts, table_count = extract_content_from_element(current, table_count, table_replacements)
        for extracted_part in extracted_parts:
            extracted_part = normalize_text(extracted_part)
            if extracted_part in section_names or extracted_part in additional_section_names:
                if extracted_part in section_names:
                    toc_index = _find_toc_index(toc, extracted_part)
                else:
                    default_section_name = default_section_names.get(extracted_part)
                    toc_index = _find_toc_index(toc, default_section_name) if default_section_name else None
                    if toc_index is not None and heading_only:
                        logger.debug(
                            "iXBRLファイルに対応するセクション名が目次に存在しないので、追加名称を考慮します: %s -> %s",
                            extracted_part,
                            default_section_name,
                        )
                if toc_index is None:
                    continue
                if current_index != -1:
                    _flush_section(
                        sections,
                        toc,
                        current_index,
                        content_elements,
                        heading_only,
                        section_names,
                        additional_section_names,
                        default_section_names,
                        extracted_part,
                    )
                current_index = toc_index
                content_elements = []
            else:
                content_elements.append(extracted_part)
        current = find_next_sibling_element_skipping_tables(current)

    if content_elements and current_index != -1:
        _flush_section(
            sections,
            toc,
            current_index,
            content_elements,
            heading_only,
            section_names,
            additional_section_names,
            default_section_names,
            None,
        )
    return sections


def extract_ixbrl_file_paths(xbrl_path: str) -> list[str]:
    """
    manifest.xmlからiXBRLファイルパスを取得。

    Args:
        xbrl_path: XBRLデータディレクトリのパス。

    Returns:
        manifest.xmlに記載されたiXBRLファイルパスのリスト。取得できない場合は空リスト。
    """
    manifest_path = os.path.join(xbrl_path, XBRL_DATA_DIR, ATTACHMENT_DIR, MANIFEST_XML)
    try:
        tree = ET.parse(manifest_path)
    except (FileNotFoundError, ET.ParseError) as exc:
        logger.warning("manifest.xmlの読み込みに失敗しました: %s", exc)
        return []

    root = tree.getroot()
    ixbrl_files: list[str] = []
    for elem in root.iter():
        if not elem.tag.endswith("ixbrl"):
            continue
        if elem.text and elem.text.strip():
            ixbrl_files.append(elem.text.strip())
        else:
            logger.warning("manifest.xmlのixbrl要素にパスがありません。")
    return ixbrl_files


def build_table_section_index(xbrl_path: str, toc: list[tuple[float, str]]) -> dict[str, Iterator[str]]:
    """
    iXBRL内でテーブルセクションの位置をインデックス化する。

    Args:
        xbrl_path: XBRLデータディレクトリのパス。
        toc: 目次のオフセットと見出しのリスト。

    Returns:
        セクションタイトルをキーに、該当iXBRLファイルパスのイテレータを返す辞書。
    """
    table_sections_lists: dict[str, list[str]] = defaultdict(list)
    for ixbrl_path in extract_ixbrl_file_paths(xbrl_path):
        sections = parse_sections(os.path.join(xbrl_path, XBRL_DATA_DIR, ATTACHMENT_DIR, ixbrl_path), toc, heading_only=True)
        for _, section_title, _ in sections:
            table_sections_lists[section_title].append(ixbrl_path)

    results: dict[str, Iterator[str]] = {}
    for title, paths in table_sections_lists.items():
        if len(paths) > 1:
            logger.debug("複数のiXBRLファイル間でセクションが重複しています: %s %s", title, paths)
        results[title] = iter(paths)
    return results
