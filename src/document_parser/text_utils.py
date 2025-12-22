"""
ドキュメントパーサー共通のテキスト処理ユーティリティ。
"""

import re

ANCHOR_PATTERN = re.compile(
    r"^(?!\(注\))"
    r"(?![\(\[\{\<〔][^\)\]\}〕>][\)\]\}〕>]\s*$)"
    r"(?:[IV]|[\(\[\{\<〔][^\)\]\}〕>]+[\)\]\}〕>]|[0-9](?![0-9.,十百千万億兆]))"
)
TABLE_PATTERN = re.compile(r"<table\d+>")


def normalize_newlines(text: str, threshold: int = 40) -> str:
    """
    本文中の意味がない改行を除去する。pdfの横幅は50文字前後なので40文字以上離れた改行は段落区切りと考えられる。
    XBRLでも一部無駄な改行が残っているので、それも除去する。

    Args:
        text: 改行を除去するテキスト
        threshold: 閾値

    Returns:
        改行を除去したテキスト
    """
    if not text:
        return ""
    result = ""
    lines = text.splitlines()
    for line in lines:
        if not line:
            continue
        elif re.fullmatch(TABLE_PATTERN, line):
            result += line + "\n"
        elif line.endswith("。"):
            result += line + "\n"
        elif len(line) < threshold and len(line) > 2 and re.match(ANCHOR_PATTERN, line):
            result += line + "\n"
        else:
            result += line
    return result
