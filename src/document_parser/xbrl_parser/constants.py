"""
XBRLパーサーで共有する定数と正規表現。
"""

from __future__ import annotations

import re

XBRL_DATA_DIR = "XBRLData"
ATTACHMENT_DIR = "Attachment"
QUALITATIVE_HTML = "qualitative.htm"
MANIFEST_XML = "manifest.xml"

TOC_CHARS = ["添", "付", "資", "料", "目", "次"]
TOC_CHARS_MINI = ["目", "次"]
PAGE_NUMBER_SEPARATOR = "..."
TOC_PATTERN = re.compile(r"(.+?)\s*[\.・]+\s*([0-9]+)")
HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]

AUTHOR_PRONEXUS = "PRONEXUS INC."
MARGIN_LEFT_CHAR = re.compile(r"margin-left:\s*([0-9\.]+)px")
CSS_MARGIN_LEFT = "margin-left"
AUTHOR_TAKARA_PRINTING = "TAKARA PRINTING CO.,LTD."
PADDING_LEFT_CHAR = re.compile(r"padding-left:\s*([0-9\.]+)pt")
CSS_PADDING_LEFT = "padding-left"
CSS_CLASS_PATTERN = re.compile(r"\.([a-zA-Z0-9_-]+)\{([^}]+)\}")
FULL_WIDTH_SPACE_OFFSET = 12.0
HALF_WIDTH_SPACE_OFFSET = 6.0

REVIEW_REPORT_PATTERN = re.compile(r"期中レビュー報告書")
REVIEW_REPORT_TITLE = "独立監査人の四半期連結財務諸表に対する期中レビュー報告書"
SPLIT_KEYWORD = "及び"
INCOME_STATEMENT_KEYWORD = "連結損益計算書"
COMPREHENSIVE_INCOME_KEYWORD = "包括利益計算書"
PERIOD_KEYWORD = "連結累計期間"
TABLE_PLACEHOLDER_FORMAT = "<table{}>"

MIN_SECTIONS_FOR_ADJUSTMENT = 5
PATTERN_LAYER1 = re.compile(r"^\d+\.")
PATTERN_LAYER2 = re.compile(r"^\(\d+\)")
