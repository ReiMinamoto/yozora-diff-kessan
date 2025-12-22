from difflib import SequenceMatcher
import logging
import re
import unicodedata

import numpy as np
from scipy.optimize import linear_sum_assignment

from src.data_models import AlignmentType, Section, SectionPair

HEADING_THRESHOLD = 0.6
CONTENT_THRESHOLD = 0.3

logger = logging.getLogger(__name__)


def flatten_single_ixbrl_subsection(section: Section) -> None:
    """
    contentが空でサブセクションがixbrlファイルのみの場合、そのサブセクションのcontentを親セクションに昇格させる。
    アライメント精度を向上させるための前処理。

    Args:
        section: フラット化するセクション
    """
    for subsection in section.subsections:
        flatten_single_ixbrl_subsection(subsection)

    if (
        not section.content
        and section.subsections
        and all(subsection.content.endswith("ixbrl.htm") for subsection in section.subsections)
    ):
        logger.debug(" %s : subsectionのixbrlファイルパスを結合してcontentに昇格", section.heading_text)
        section.content = ", ".join([subsection.content for subsection in section.subsections])
        section.subsections = []


def normalize_heading(heading: str) -> str:
    """
    見出しを正規化して比較しやすくする

    Args:
        heading: 正規化する見出し文字列

    Returns:
        正規化された見出し文字列(数字、括弧を除去し小文字に変換)
    """
    normalized = re.sub(r"[0-9\(\)\[\]（）【】]", "", heading).strip()
    return normalized.lower()


def normalize_text(text: str) -> str:
    """
    テキストを正規化する関数。
    Unicode正規化(NFKC)と空白除去、数字の<NUM>変換を行う。

    Args:
        text: 正規化対象の文字列。

    Returns:
        正規化され、数字が<NUM>に変換され、空白が除去された文字列。
    """
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[0-9][0-9,\.]*", "<NUM>", text)
    text = re.sub(r"\s+", "", text)
    return text


def calculate_similarity(text1: str, text2: str, is_content: bool = False) -> float:
    """
    2つのテキストの類似度をSequenceMatcherで計算、見出しの場合は短い方に合わせて正規化、コンテンツの場合はそのまま

    Args:
        text1: 比較する最初のテキスト
        text2: 比較する2番目のテキスト
        is_content: コンテンツかどうか

    Returns:
        0.0から1.0の間の類似度スコア
    """
    if is_content:
        return SequenceMatcher(None, text1, text2).ratio()
    else:
        return SequenceMatcher(None, text1, text2).ratio() * (len(text1) + len(text2)) / 2 / min(len(text1), len(text2))


def calculate_section_similarity(old_section: Section, new_section: Section) -> tuple[float, float, float]:
    """
    見出しとサブセクションの見出しリストを考慮してセクションの類似度を計算

    Args:
        old_section: 旧セクション
        new_section: 新セクション

    Returns:
        見出しの類似度スコアとサブセクションの見出しリストの類似度スコアとコンテンツの類似度スコア
    """
    subheading_similarity = -1.0
    content_similarity = -1.0
    old_heading = normalize_heading(old_section.heading_text)
    new_heading = normalize_heading(new_section.heading_text)
    heading_similarity = calculate_similarity(old_heading, new_heading)
    if old_section.subsections and new_section.subsections:
        old_subsection_headings = " ".join([normalize_heading(s.heading_text) for s in old_section.subsections])
        new_subsection_headings = " ".join([normalize_heading(s.heading_text) for s in new_section.subsections])
        subheading_similarity = calculate_similarity(old_subsection_headings, new_subsection_headings)
    if old_section.content and new_section.content:
        old_content = normalize_text(old_section.content)
        new_content = normalize_text(new_section.content)
        content_similarity = calculate_similarity(old_content, new_content, is_content=True)
    return heading_similarity, subheading_similarity, content_similarity


def find_ordered_matches(
    old_items: list[Section], new_items: list[Section], level: int = 0
) -> dict[int, tuple[int, float, float, float, float]]:
    """
    順番を保持したマッチングを見つける

    Args:
        old_items: 旧データのセクションリスト
        new_items: 新データのセクションリスト
        level: 現在の階層レベル

    Returns:
        旧データのインデックスをキーとし、(新データのインデックス, 使用する類似度, 見出しの類似度, サブセクションの見出しリストの類似度, コンテンツの類似度)を値とする辞書
    """
    if not old_items or not new_items:
        return {}

    matches = {}
    past_new_index = -1

    for i, old_item in enumerate(old_items):
        # トップレベルの最初のセクション(1章目)は確定マッチ
        if level == 0 and i == 0:
            matches[0] = (0, 1.0, -1.0, -1.0, -1.0)
            past_new_index = 0
            continue

        for j, new_item in enumerate(new_items):
            if j <= past_new_index:
                continue
            heading_similarity, subsection_similarity, content_similarity = calculate_section_similarity(old_item, new_item)

            similarity_to_use = None
            if heading_similarity > HEADING_THRESHOLD:
                similarity_to_use = heading_similarity
            elif subsection_similarity > HEADING_THRESHOLD:
                similarity_to_use = subsection_similarity
                logger.debug(f"subsection_similarityを使用: {old_item.heading_text} -> {new_item.heading_text}")
            elif level <= 1 and content_similarity > CONTENT_THRESHOLD:
                logger.debug(f"content_similarityを使用: {old_item.heading_text} -> {new_item.heading_text}")
                similarity_to_use = content_similarity

            if similarity_to_use is not None:
                matches[i] = (j, similarity_to_use, heading_similarity, subsection_similarity, content_similarity)
                past_new_index = j
                break  # 閾値を超えた瞬間にマッチング確定

    return matches


def find_optimal_matches(
    old_items: list[Section], new_items: list[Section], level: int = 0
) -> dict[int, tuple[int, float, float, float, float]]:
    """
    最適マッチングを見つける。注記事項の場合のみ使用するので、サブセクションの類似度とコンテンツの類似度は考慮しない。

    Args:
        old_items: 旧データのセクションリスト
        new_items: 新データのセクションリスト
        level: 現在の階層レベル

    Returns:
        旧データのインデックスをキーとし、(新データのインデックス, 使用する類似度, 見出しの類似度, サブセクションの見出しリストの類似度, コンテンツの類似度)を値とする辞書
    """
    if not old_items or not new_items:
        return {}

    m, n = len(old_items), len(new_items)
    similarity_matrix = np.zeros((m, n))
    similarity_details = []

    for i, old_item in enumerate(old_items):
        details_row = []
        for j, new_item in enumerate(new_items):
            heading_sim, subsection_sim, content_sim = calculate_section_similarity(old_item, new_item)
            if heading_sim > HEADING_THRESHOLD:
                similarity_matrix[i, j] = heading_sim
            else:
                similarity_matrix[i, j] = -1.0
            details_row.append((heading_sim, -1.0, -1.0))
        similarity_details.append(details_row)

    row_indices, col_indices = linear_sum_assignment(similarity_matrix, maximize=True)

    optimal_matches = {}

    for i, j in zip(row_indices, col_indices):
        sim_score = similarity_matrix[i, j]
        if sim_score > 0:
            heading_sim, subsection_sim, content_sim = similarity_details[i][j]
            optimal_matches[i] = (
                j,
                sim_score,
                heading_sim,
                subsection_sim,
                content_sim,
            )

    return optimal_matches


def _create_matched_pair(
    old_section: Section,
    new_section: Section,
    match_data: tuple[int, float, float, float, float],
    level: int,
) -> SectionPair:
    """
    マッチしたセクションからSectionPairを作成する

    Args:
        old_section: 旧セクション
        new_section: 新セクション
        match_data: (新データのインデックス, 使用する類似度, 見出しの類似度, サブセクションの見出しリストの類似度, コンテンツの類似度)
        level: 現在の階層レベル

    Returns:
        作成されたSectionPair
    """
    _, similarity_score, heading_sim, subsection_sim, content_sim = match_data
    subsections_alignments = align_sections(old_section.subsections, new_section.subsections, level + 1)

    return SectionPair(
        level=level,
        old_heading=old_section.heading_text,
        new_heading=new_section.heading_text,
        old_content=old_section.content,
        new_content=new_section.content,
        alignment_type=AlignmentType.MATCHED,
        similarity_score=similarity_score,
        heading_similarity_score=heading_sim,
        subsection_similarity_score=subsection_sim,
        content_similarity_score=content_sim,
        subsections=subsections_alignments,
    )


def align_sections(old_data: list[Section], new_data: list[Section], level: int = 0) -> list[SectionPair]:
    """
    oldとnewのデータのアライメントを取って対応するセクションを特定する

    Args:
        old_data: 旧データのセクションリスト
        new_data: 新データのセクションリスト
        level: 現在の階層レベル

    Returns:
        アライメント結果のリスト
    """
    aligned_results = []

    def add_unmatched_section(section: Section, alignment_type: AlignmentType) -> None:
        """マッチしなかったセクションを結果に追加する内部関数"""
        aligned_results.append(
            SectionPair(
                level=level,
                old_heading=section.heading_text if alignment_type == AlignmentType.DELETED else None,
                new_heading=section.heading_text if alignment_type == AlignmentType.ADDED else None,
                old_content=section.content if alignment_type == AlignmentType.DELETED else None,
                new_content=section.content if alignment_type == AlignmentType.ADDED else None,
                alignment_type=alignment_type,
                similarity_score=0.0,
                heading_similarity_score=0.0,
                subsection_similarity_score=0.0,
                content_similarity_score=0.0,
                subsections=[],
            )
        )

    for section in old_data:
        flatten_single_ixbrl_subsection(section)
    for section in new_data:
        flatten_single_ixbrl_subsection(section)

    # 注記事項の場合は最適マッチング、それ以外は順序保持マッチング
    is_note = (
        old_data
        and new_data
        and all(section.heading_text.startswith("(") and section.heading_text.endswith(")") for section in old_data)
        and all(section.heading_text.startswith("(") and section.heading_text.endswith(")") for section in new_data)
    )

    if is_note:
        matches = find_optimal_matches(old_data, new_data, level)
        used_new_indices = {matches[i][0] for i in matches}

        for i in range(len(old_data)):
            if i in matches:
                aligned_results.append(_create_matched_pair(old_data[i], new_data[matches[i][0]], matches[i], level))
            else:
                add_unmatched_section(old_data[i], AlignmentType.DELETED)

        for j in range(len(new_data)):
            if j not in used_new_indices:
                add_unmatched_section(new_data[j], AlignmentType.ADDED)
    else:
        matches = find_ordered_matches(old_data, new_data, level)
        past_new_index = -1

        for i in range(len(old_data)):
            if i in matches:
                new_idx = matches[i][0]
                if past_new_index < new_idx:
                    for j in range(past_new_index + 1, new_idx):
                        add_unmatched_section(new_data[j], AlignmentType.ADDED)
                    past_new_index = new_idx

                aligned_results.append(_create_matched_pair(old_data[i], new_data[new_idx], matches[i], level))
            else:
                add_unmatched_section(old_data[i], AlignmentType.DELETED)

        for j in range(past_new_index + 1, len(new_data)):
            add_unmatched_section(new_data[j], AlignmentType.ADDED)

    return aligned_results
