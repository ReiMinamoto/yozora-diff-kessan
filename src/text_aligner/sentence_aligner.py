from difflib import SequenceMatcher
import re
import unicodedata

from src.data_models import AlignedSentence, AlignmentType, SectionPair, SentencePair

THRESHOLD = 0.5
TABLE_PATTERN = re.compile(r"<table\d+>")
ANCHOR_PATTERN = re.compile(
    r"^(?!\(注\))"
    r"(?![\(\[\{\<〔][^\)\]\}〕>][\)\]\}〕>]\s*$)"
    r"(?:[IV]|[\(\[\{\<〔][^\)\]\}〕>]+[\)\]\}〕>]|[0-9](?![0-9.,十百千万億兆]))"
)


def normalize_heading(heading: str) -> str:
    """
    見出しを正規化して比較しやすくする

    Args:
        heading: 正規化する見出し文字列

    Returns:
        正規化された見出し文字列(数字、括弧を除去し小文字に変換)
    """
    normalized = re.sub(r"^[0-9\(\)\[\]（）【】]+", "", heading).strip()
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


def split_sentences(text: str) -> list[str]:
    """
    テキストを文に分割する(「。」は文に含める)

    Args:
        text: 分割するテキスト

    Returns:
        文のリスト
    """
    if not text or not text.strip():
        return []

    sentences = re.findall(r"[^。\n]+。|[^。\n]+", text)
    return [s.strip() for s in sentences if s.strip()]


def extract_headings_and_remove_tables(text: str, threshold: int = 40) -> tuple[str, list[str]]:
    """
    表の除去と見出しの抽出を行う。

    Args:
        text: 表の除去と見出しの抽出をするテキスト
        threshold: 閾値

    Returns:
        表を除去したテキストと見出しのリスト
    """
    if not text:
        return "", []
    result = ""
    headings = []
    lines = text.splitlines()
    for line in lines:
        if not line or re.fullmatch(TABLE_PATTERN, line):
            continue
        if len(line) < threshold and len(line) > 2 and re.match(ANCHOR_PATTERN, line):
            headings.append(line)
        result += line + "\n"
    return result, headings


def find_ordered_matches(old_sentences: list[str], new_sentences: list[str], heading_align: bool = False) -> dict:
    """
    順番を保持したマッチングを見つける

    Args:
        old_sentences: 古い文のリスト
        new_sentences: 新しい文のリスト
        heading_align: 見出しアライメントかどうか

    Returns:
        マッチした文のペアを記録した辞書
    """
    if not old_sentences or not new_sentences:
        return {}

    if heading_align:
        old_sentences = [normalize_heading(heading) for heading in old_sentences]
        new_sentences = [normalize_heading(heading) for heading in new_sentences]
    else:
        old_sentences = [normalize_text(text) for text in old_sentences]
        new_sentences = [normalize_text(text) for text in new_sentences]

    matches = {}
    past_new_index = -1

    for i, old_sent in enumerate(old_sentences):
        for j, new_sent in enumerate(new_sentences):
            if j <= past_new_index:
                continue

            similarity = SequenceMatcher(None, old_sent, new_sent).ratio()

            if similarity > THRESHOLD:
                matches[i] = (j, similarity)
                past_new_index = j
                break  # 閾値を超えた瞬間にマッチング確定

    return matches


def build_alignment_results(old_sentences: list[str], new_sentences: list[str], matches: dict) -> list[AlignedSentence]:
    """
    マッチング結果からアライメント結果を構築する(old_itemを基準に順番を保持)

    Args:
        old_sentences: 古い文のリスト
        new_sentences: 新しい文のリスト
        matches: マッチング結果の辞書

    Returns:
        アライメント結果のリスト
    """
    results = []
    past_new_index = -1

    for i in range(len(old_sentences)):
        if i in matches:
            new_idx, similarity = matches[i]
            new_sent = new_sentences[new_idx]

            if past_new_index < new_idx:
                for j in range(past_new_index + 1, new_idx):
                    results.append(
                        AlignedSentence(
                            old_sentence=None,
                            new_sentence=new_sentences[j],
                            similarity_score=0.0,
                            alignment_type=AlignmentType.ADDED,
                        )
                    )
                past_new_index = new_idx

            results.append(
                AlignedSentence(
                    old_sentence=old_sentences[i],
                    new_sentence=new_sent,
                    similarity_score=float(similarity),
                    alignment_type=AlignmentType.MATCHED,
                )
            )
        else:
            results.append(
                AlignedSentence(
                    old_sentence=old_sentences[i],
                    new_sentence=None,
                    similarity_score=0.0,
                    alignment_type=AlignmentType.DELETED,
                )
            )

    for j in range(past_new_index + 1, len(new_sentences)):
        results.append(
            AlignedSentence(
                old_sentence=None,
                new_sentence=new_sentences[j],
                similarity_score=0.0,
                alignment_type=AlignmentType.ADDED,
            )
        )

    return results


def align_sentences(old_text: str, new_text: str, old_headings: list[str], new_headings: list[str]) -> list[AlignedSentence]:
    """
    文単位でアライメントを実行(old_itemを基準に順番を保持)

    Args:
        old_text: 古いテキスト
        new_text: 新しいテキスト
        old_headings: 古い見出しのリスト
        new_headings: 新しい見出しのリスト

    Returns:
        文のアライメント結果リスト
    """
    headings_match = find_ordered_matches(old_headings, new_headings, heading_align=True)
    headings = build_alignment_results(old_headings, new_headings, headings_match)

    old_sentence_list = []
    new_sentence_list = []
    old_index = 0
    new_index = 0
    for heading in headings:
        if heading.alignment_type == AlignmentType.MATCHED:
            old_sentence_list.append(old_text[old_index : old_text.find(heading.old_sentence)])
            new_sentence_list.append(new_text[new_index : new_text.find(heading.new_sentence)])
            old_index = old_text.find(heading.old_sentence)
            new_index = new_text.find(heading.new_sentence)
    old_sentence_list.append(old_text[old_index:])
    new_sentence_list.append(new_text[new_index:])

    results = []
    for old_sentence, new_sentence in zip(old_sentence_list, new_sentence_list):
        old_sentences = split_sentences(old_sentence)
        new_sentences = split_sentences(new_sentence)

        if not old_sentences and not new_sentences:
            continue

        matches = find_ordered_matches(old_sentences, new_sentences)
        results.extend(build_alignment_results(old_sentences, new_sentences, matches))

    return results


def get_aligned_sentences(section_pairs: list[SectionPair]) -> list[SentencePair]:
    """
    テキストをアライメントし、文単位のアライメントも含める

    Args:
        section_pairs: セクションペアのリスト

    Returns:
        センテンスペアのリスト
    """
    sentence_pairs = []

    def collect_sentence_pair(
        section_pair: SectionPair,
        parent_old_headings: list[str] | None = None,
        parent_new_headings: list[str] | None = None,
    ) -> None:
        """
        テキストをアライメントし、文単位のアライメントも含める
        """
        if parent_old_headings is None:
            parent_old_headings = []
        if parent_new_headings is None:
            parent_new_headings = []

        if section_pair.old_content and section_pair.new_content:
            section_pair.old_content, old_headings = extract_headings_and_remove_tables(section_pair.old_content)
            section_pair.new_content, new_headings = extract_headings_and_remove_tables(section_pair.new_content)
            overall_similarity_score = SequenceMatcher(None, section_pair.old_content, section_pair.new_content).ratio()
            sentence_alignments = align_sentences(section_pair.old_content, section_pair.new_content, old_headings, new_headings)

            old_heading_parts = parent_old_headings.copy()
            new_heading_parts = parent_new_headings.copy()
            if section_pair.old_heading:
                old_heading_parts.append(section_pair.old_heading)
            if section_pair.new_heading:
                new_heading_parts.append(section_pair.new_heading)

            old_heading = " > ".join(old_heading_parts) if old_heading_parts else None
            new_heading = " > ".join(new_heading_parts) if new_heading_parts else None

            if (
                section_pair.old_content != section_pair.new_content
                and not section_pair.old_content.endswith(".htm")
                and not section_pair.new_content.endswith(".htm")
            ):
                sentence_pairs.append(
                    SentencePair(
                        old_heading=old_heading,
                        new_heading=new_heading,
                        old_content=section_pair.old_content,
                        new_content=section_pair.new_content,
                        overall_similarity_score=overall_similarity_score,
                        sentence_alignments=sentence_alignments,
                    )
                )

        if section_pair.subsections:
            current_old_headings = parent_old_headings.copy()
            current_new_headings = parent_new_headings.copy()
            if section_pair.old_heading:
                current_old_headings.append(section_pair.old_heading)
            if section_pair.new_heading:
                current_new_headings.append(section_pair.new_heading)

            for subsection in section_pair.subsections:
                collect_sentence_pair(subsection, current_old_headings, current_new_headings)

    for section_pair in section_pairs:
        collect_sentence_pair(section_pair)
    return sentence_pairs
