"""
HTML/CSSヘルパー。
"""

from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup
from bs4.element import Tag

from src.document_parser.xbrl_parser.constants import (
    AUTHOR_PRONEXUS,
    AUTHOR_TAKARA_PRINTING,
    CSS_CLASS_PATTERN,
    CSS_MARGIN_LEFT,
    CSS_PADDING_LEFT,
    FULL_WIDTH_SPACE_OFFSET,
    HALF_WIDTH_SPACE_OFFSET,
    MARGIN_LEFT_CHAR,
    PADDING_LEFT_CHAR,
)


def normalize_text(text: str) -> str:
    """
    テキストを正規化する関数。
    Unicode正規化(NFKC)と空白除去を行う。

    Args:
        text: 正規化対象の文字列。

    Returns:
        正規化され、連続した空白が除去された文字列。
    """
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", "", text)
    return text


def parse_css_classes(soup: BeautifulSoup) -> dict[str, dict[str, str]]:
    """
    <style>タグ内のCSSクラス定義を辞書に展開する。

    Args:
        soup: 解析対象のBeautifulSoupオブジェクト。

    Returns:
        クラス名をキー、プロパティ辞書を値とする辞書。
    """
    css_classes: dict[str, dict[str, str]] = {}
    style_tags = soup.find_all("style")

    for style_tag in style_tags:
        css_content = style_tag.string
        if not css_content:
            continue

        matches = CSS_CLASS_PATTERN.findall(css_content)

        for class_name, properties in matches:
            prop_dict: dict[str, str] = {}
            for prop in properties.split(";"):
                if ":" in prop:
                    key, value = prop.split(":", 1)
                    prop_dict[key.strip()] = value.strip()
            css_classes[class_name] = prop_dict

    return css_classes


def calculate_text_leading_spaces_offset(text: str) -> float:
    """
    先頭に含まれる半角/全角スペースからオフセット(px)を計算。

    Args:
        text: オフセット計算対象の文字列。

    Returns:
        先頭スペースから算出したオフセット値(px)。
    """
    if not text:
        return 0.0

    leading_spaces = 0.0
    for char in text:
        if char == "　":
            leading_spaces += FULL_WIDTH_SPACE_OFFSET
        elif char == " ":
            leading_spaces += HALF_WIDTH_SPACE_OFFSET
        else:
            break

    return leading_spaces


def extract_element_left_offset(element: Tag, css_classes: dict[str, dict[str, str]], author: str) -> tuple[float, float]:
    """
    インラインスタイル、CSSクラス定義、テキストの先頭スペースから左側のオフセット値を抽出。
    優先順位:
    1. インラインスタイルのmargin-left(プロネクサス)/padding-left(宝印刷)
    2. CSSクラス定義のmargin-left(プロネクサス)/padding-left(宝印刷)
    3. テキストの先頭スペース

    Args:
        element: オフセットを取得する対象のタグ。
        css_classes: クラス名とプロパティ辞書のマッピング。
        author: 作成者情報。

    Returns:
        tuple: (CSSやインラインスタイルから得た左オフセット, テキスト先頭スペース由来のオフセット)。
    """
    text_content = element.get_text()
    text_offset = calculate_text_leading_spaces_offset(text_content)

    style = element.get("style", "")

    if author == AUTHOR_PRONEXUS:
        match = MARGIN_LEFT_CHAR.search(style)
        if match:
            css_offset = float(match.group(1))
            return css_offset, text_offset
    elif author == AUTHOR_TAKARA_PRINTING:
        match = PADDING_LEFT_CHAR.search(style)
        if match:
            css_offset = float(match.group(1))
            return css_offset, text_offset

    class_names = element.get("class", [])
    if isinstance(class_names, str):
        class_names = [class_names]

    for class_name in class_names:
        if class_name not in css_classes:
            continue

        class_props = css_classes[class_name]
        if author == AUTHOR_PRONEXUS:
            if CSS_MARGIN_LEFT in class_props:
                value = class_props[CSS_MARGIN_LEFT]
                num_match = re.search(r"([0-9\.]+)", value)
                if num_match:
                    css_offset = float(num_match.group(1))
                    return css_offset, text_offset
        elif author == AUTHOR_TAKARA_PRINTING:
            if CSS_PADDING_LEFT in class_props:
                value = class_props[CSS_PADDING_LEFT]
                num_match = re.search(r"([0-9\.]+)", value)
                if num_match:
                    css_offset = float(num_match.group(1))
                    return css_offset, text_offset

    return 0.0, text_offset
