"""文の差分を検出し、編集単位にタグ付けするモジュール。"""

from collections import deque
import difflib
import re

from src.data_models import AlignedSentence, AlignmentType, SentencePair

COMMON_TEXT_MIN_LENGTH = 5


def replace_numbers(text: str):
    """
    数値を <NUM> に置換し、元の数値リストも返す関数。

    Args:
        text: 数値を置換するテキスト

    Returns:
        数値を<NUM>に置換したテキストと、抽出された数値リストのタプル
    """
    nums = re.findall(r"[0-9][0-9,\.]*", text)
    replaced = re.sub(r"[0-9][0-9,\.]*", "<NUM>", text)
    return replaced, nums


def restore_numbers(parts: list[str], old_nums: list[str], new_nums: list[str]) -> list[str]:
    """
    数値を復元し、編集単位に分解する関数。

    Args:
        parts: <NUM>を含む部分文字列のリスト
        old_nums: 旧バージョンの数値リスト
        new_nums: 新バージョンの数値リスト

    Returns:
        数値が復元され、編集単位に分解された部分文字列のリスト
    """
    old_nums = deque(old_nums)
    new_nums = deque(new_nums)
    decomposed_parts = []

    for part in parts:

        def repl(match):
            if part.startswith("<del>"):  # noqa: B023
                return old_nums.popleft() if old_nums else "<NUM>"
            elif part.startswith("<add>"):  # noqa: B023
                return new_nums.popleft() if new_nums else "<NUM>"
            else:
                if old_nums and new_nums:
                    old_val = old_nums.popleft()
                    new_val = new_nums.popleft()
                    if old_val == new_val:
                        return old_val
                    else:
                        return f"<del>{old_val}</del><add>{new_val}</add>"
                else:
                    return "<NUM>"

        restored_part = re.sub(r"<NUM>", repl, part)
        pattern = r"(<add>.*?</add>|<del>.*?</del>)"
        decomposed_parts.extend([part for part in re.split(pattern, restored_part) if part])

    restored = []
    i = 0
    while i < len(decomposed_parts):
        decomposed_part = decomposed_parts[i]
        if decomposed_part.startswith("<del>"):
            if (
                len(restored) > 1
                and restored[-2].startswith("<del>")
                and restored[-1].startswith("<add>")
                and i + 1 < len(decomposed_parts)
                and decomposed_parts[i + 1].startswith("<add>")
            ):
                restored[-2] = restored[-2][: -len("</del>")] + decomposed_part[len("<del>") :]
                restored[-1] = restored[-1][: -len("</add>")] + decomposed_parts[i + 1][len("<add>") :]
                i += 1
            else:
                restored.append(decomposed_part)
        elif decomposed_part.startswith("<add>"):
            restored.append(decomposed_part)
        else:
            if len(decomposed_part) > COMMON_TEXT_MIN_LENGTH:
                restored.append(decomposed_part)
            else:
                if len(restored) > 1 and restored[-2].startswith("<del>") and restored[-1].startswith("<add>"):
                    restored[-2] = restored[-2][: -len("</del>")] + decomposed_part + "</del>"
                    restored[-1] = restored[-1][: -len("</add>")] + decomposed_part + "</add>"
                else:
                    restored.append(decomposed_part)
        i += 1

    return restored


def make_diff(old: str, new: str) -> str:
    """
    新旧のテキストから差分を生成し、<del>と<add>タグでマークアップする関数。

    Args:
        old: 旧バージョンのテキスト
        new: 新バージョンのテキスト

    Returns:
        <del>と<add>タグでマークアップされた差分テキスト
    """
    old, old_nums = replace_numbers(old)
    new, new_nums = replace_numbers(new)
    sm = difflib.SequenceMatcher(None, old, new)
    parts = []
    old_index = 0
    new_index = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            if i2 - i1 > COMMON_TEXT_MIN_LENGTH:
                parts.append(f"<del>{old[old_index:i1]}</del>")
                parts.append(f"<add>{new[new_index:j1]}</add>")
                parts.append(old[i1:i2])
                old_index = i2
                new_index = j2
    del_text = old[old_index:]
    add_text = new[new_index:]
    parts.append(f"<del>{del_text}</del>")
    parts.append(f"<add>{add_text}</add>")
    parts = restore_numbers(parts, old_nums, new_nums)
    # <del>と<add>をセットで扱えるよう空文字でも保持していたが、出力では削除
    diff = "".join([p for p in parts if p not in ("<del></del>", "<add></add>")])
    return diff


def make_edit_unit(alignment: AlignedSentence, edit_id: int) -> tuple[str, int]:
    """
    アライメント結果から編集単位を作成する関数。

    Args:
        alignment: アライメントされた文のペア
        edit_id: 編集ID(次の編集IDを返すために使用)

    Returns:
        編集単位の文字列と次の編集IDのタプル
    """
    old, new, typ = alignment.old_sentence, alignment.new_sentence, alignment.alignment_type
    if typ == AlignmentType.ADDED:
        return f"<edit {edit_id}><add>{new}</add></edit {edit_id}>", edit_id + 1
    elif typ == AlignmentType.DELETED:
        return f"<edit {edit_id}><del>{old}</del></edit {edit_id}>", edit_id + 1
    elif typ == AlignmentType.MATCHED:
        if old != new:
            diff = make_diff(old, new)
            return f"<edit {edit_id}>{diff}</edit {edit_id}>", edit_id + 1
        else:
            return old, edit_id
    else:
        return old, edit_id


def preprocess_sentence_pairs(sentence_pairs: list[SentencePair]) -> list[dict[str, str | list[str]]]:
    """
    文ペアを前処理し、編集単位にタグ付けする関数。

    Args:
        sentence_pairs: 文ペアのリスト

    Returns:
        処理済みの文ペアのリスト。各要素は以下のキーを持つ辞書:
        - old_heading: 旧バージョンの見出し
        - new_heading: 新バージョンの見出し
        - processed_sentence_pair: 編集タグが付与された処理済みテキスト
        - edit_units: 編集単位のリスト
    """
    processed = []
    edit_id = 0
    for sentence_pair in sentence_pairs:
        processed_sentence_pair = ""
        edit_units = []
        for aligned_sentence in sentence_pair.sentence_alignments:
            edit_unit, edit_id = make_edit_unit(aligned_sentence, edit_id)
            processed_sentence_pair += edit_unit
            if edit_unit.startswith("<edit"):
                edit_units.append(edit_unit)
        processed.append(
            {
                "old_heading": sentence_pair.old_heading,
                "new_heading": sentence_pair.new_heading,
                "processed_sentence_pair": processed_sentence_pair,
                "edit_units": edit_units,
            }
        )
    return processed
