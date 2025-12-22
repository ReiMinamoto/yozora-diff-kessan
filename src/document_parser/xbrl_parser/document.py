"""
XBRLドキュメント全体の解析とCLI。
"""

from __future__ import annotations

from collections import Counter
import logging
import os

from src.data_models import Section
from src.document_parser.text_utils import normalize_newlines
from src.document_parser.xbrl_parser.constants import (
    ATTACHMENT_DIR,
    MIN_SECTIONS_FOR_ADJUSTMENT,
    PATTERN_LAYER1,
    PATTERN_LAYER2,
    QUALITATIVE_HTML,
    REVIEW_REPORT_TITLE,
    XBRL_DATA_DIR,
)
from src.document_parser.xbrl_parser.sections import build_table_section_index, parse_sections
from src.document_parser.xbrl_parser.toc_parser import extract_table_of_contents

logger = logging.getLogger(__name__)


def _log_section_structure(sections: list[Section], indent: int = 0) -> list[tuple[str, str]]:
    """
    セクションの階層構造を再帰的に取得し、テーブルセクションのリストを返す。

    Args:
        sections: 構造化済みセクションのリスト。
        indent: ログ出力時のインデント幅。

    Returns:
        見出しテキストとテーブルコンテンツのタプル一覧。
    """
    table_sections = []
    for section in sections:
        indent_str = " " * indent
        logger.info(f"{indent_str}{section.heading_text}")
        if section.content and "ixbrl.htm" in section.content:
            table_sections.append((section.heading_text, section.content))
        if section.subsections:
            table_sections.extend(_log_section_structure(section.subsections, indent + 2))
    return table_sections


def _collect_placeholders_in_output(sections: list[Section], placeholders: set[str]) -> set[str]:
    """
    最終出力に含まれるテーブルプレースホルダーのみ抽出する。

    Args:
        sections: 最終的なセクション構造。
        placeholders: 置換候補のプレースホルダー集合。

    Returns:
        出力に実際に含まれているプレースホルダー集合。
    """
    found: set[str] = set()
    for section in sections:
        if section.content:
            for placeholder in placeholders:
                if placeholder in section.content:
                    found.add(placeholder)
        if section.subsections:
            found.update(_collect_placeholders_in_output(section.subsections, placeholders))
    return found


def log_sections(
    toc: list[tuple[float, str]],
    sections: list[tuple[float, str, str]],
    results: list[Section],
    table_replacements: list[tuple[str, str]] | None = None,
) -> None:
    """
    sectionsがtocの順番になっていない場合警告し、パース結果とテーブル置換内容をログに出力する。

    Args:
        toc: 抽出した目次のオフセットと見出しのリスト。
        sections: パースしたセクション情報(レベル、見出し、内容)。
        results: 階層化後のセクションオブジェクト。
        table_replacements: プレースホルダーと元テーブル文字列のリスト。省略可。
    """
    if not sections or not toc:
        return

    toc_titles = [title for _, title in toc]
    section_titles = [heading for _, heading, _ in sections]

    toc_titles_set = set(toc_titles)
    section_titles_set = set(section_titles)
    missing_titles = toc_titles_set - section_titles_set
    extra_titles = section_titles_set - toc_titles_set

    if missing_titles:
        logger.warning("目次にあるがセクションに存在しない見出し: %s", missing_titles)

    if extra_titles:
        logger.warning("セクションにあるが目次に存在しない見出し: %s", extra_titles)

    for i, (toc_title, sec_title) in enumerate(zip(toc_titles, section_titles)):
        if toc_title != sec_title:
            logger.warning(
                "セクションの順番が目次と不一致: (例) セクションの%d番目は'%s'ですが、目次では'%s'です",
                i,
                sec_title,
                toc_title,
            )
            break

    logger.info("=== 目次 =================")
    logger.info(toc)
    logger.info("==========================\n")

    logger.info("== 構造化したセクション ==")
    table_sections = _log_section_structure(results)
    logger.info("==========================\n")

    logger.info("=== テーブルセクション ===")
    for heading, content in table_sections:
        logger.info(f"{heading}: {content}")
    logger.info("==========================\n")

    if table_replacements:
        placeholders_in_output = _collect_placeholders_in_output(results, {placeholder for placeholder, _ in table_replacements})
        filtered_replacements = [item for item in table_replacements if item[0] in placeholders_in_output]
        if not filtered_replacements:
            return
        logger.info("==== テーブル置換ログ ====")
        for placeholder, original in filtered_replacements:
            truncated = f"{original[:50]}..." if len(original) > 50 else original
            logger.info("%s: %s", placeholder, truncated)
        logger.info("==========================\n")


def _add_section_to_hierarchy(
    section: Section,
    level: float,
    results: list[Section],
    stack: list[tuple[Section, float]],
) -> None:
    """
    セクションを階層構造に追加するヘルパー。

    Args:
        section: 追加するセクション。
        level: セクションのレベル値。
        results: ルート階層のセクションリスト。
        stack: 階層構築用のスタック。
    """
    while stack and stack[-1][1] >= level:
        stack.pop()

    if not stack:
        results.append(section)
    else:
        parent_section, _ = stack[-1]
        parent_section.add_subsection(section)

    stack.append((section, level))


def parse_document(xbrl_path: str) -> list[Section]:
    """
    XBRLデータフォルダを解析して階層化セクションを返す。

    Args:
        xbrl_path: XBRLファイル群が格納されたディレクトリへのパス。

    Returns:
        階層構造化されたセクションのリスト。パース失敗時は空リスト。
    """
    toc = extract_table_of_contents(xbrl_path)
    table_sections = build_table_section_index(xbrl_path, toc)
    qualitative_file = os.path.join(xbrl_path, XBRL_DATA_DIR, ATTACHMENT_DIR, QUALITATIVE_HTML)
    table_replacements: list[tuple[str, str]] = []
    sections = parse_sections(qualitative_file, toc, table_replacements=table_replacements)
    if not sections:
        return []

    results: list[Section] = []
    stack: list[tuple[Section, float]] = []

    heading_counts = Counter(heading for _, heading, _ in sections)

    for level, heading_text, content in sections:
        if content:
            table_iter = table_sections.get(heading_text)
            if table_iter:
                try:
                    if heading_counts[heading_text] == 1:
                        all_items = list(table_iter)
                        content = ", ".join(all_items) if all_items else content
                    else:
                        content = next(table_iter)
                except StopIteration:
                    logger.warning("イテレータを消費済み: %s", heading_text)
            content = normalize_newlines(content)
        else:
            content = ""
        section = Section(
            level=level,
            heading_text=heading_text.strip(),
            content=content,
            subsections=[],
        )

        _add_section_to_hierarchy(section, level, results, stack)

    if len(results) < MIN_SECTIONS_FOR_ADJUSTMENT:
        log_sections(toc, sections, results, table_replacements)
        return results

    # 宝印刷でのみ必要: 階層化されていない場合は、タイトル名から階層を推定して階層調整を行う
    logger.info("セクション数が多いので階層調整を行います: %s", len(results))
    adjusted_results: list[Section] = []
    section_stack: list[tuple[Section, float]] = []

    for section in results:
        if PATTERN_LAYER1.match(section.heading_text) or section.heading_text == REVIEW_REPORT_TITLE:
            adjusted_results.append(section)
            section_stack = [(section, 1)]
        elif PATTERN_LAYER2.match(section.heading_text):
            _add_section_to_hierarchy(section, 2, adjusted_results, section_stack)
        else:
            _add_section_to_hierarchy(section, 3, adjusted_results, section_stack)

    log_sections(toc, sections, adjusted_results, table_replacements)
    return adjusted_results
