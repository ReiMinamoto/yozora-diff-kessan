from dataclasses import dataclass, field
from enum import Enum


class AlignmentType(Enum):
    """アライメント種別の定数クラス"""

    MATCHED = "matched"
    DELETED = "deleted"
    ADDED = "added"


@dataclass
class Section:
    """
    セクションを表すクラス

    Attributes:
        level (int): 階層レベル
        heading_text (str): 見出しテキスト
        content (str): コンテンツ(文字列)
        subsections (list['Section']): 子セクションのリスト
    """

    level: int
    heading_text: str
    content: str = ""
    subsections: list["Section"] = field(default_factory=list)

    def add_subsection(self, subsection: "Section") -> None:
        """サブセクションを追加"""
        self.subsections.append(subsection)

    def to_dict(self) -> dict[str, str | list[dict]]:
        """辞書形式に変換"""
        return {
            "level": self.level,
            "heading_text": self.heading_text,
            "content": self.content,
            "subsections": [subsection.to_dict() for subsection in self.subsections],
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | list[dict]]) -> "Section":
        """辞書形式から作成"""
        content = data.get("content", "")
        subsections = data.get("subsections", [])

        # 再帰的にSectionオブジェクトに変換
        if isinstance(subsections, list) and subsections and isinstance(subsections[0], dict):
            subsections = [cls.from_dict(subsection) for subsection in subsections]

        return cls(level=data["level"], heading_text=data["heading_text"], content=content, subsections=subsections)


@dataclass
class SectionPair:
    """
    セクションペアを表すクラス

    Attributes:
        level (int): 階層レベル(0が最上位)
        old_heading (str | None): 古い見出し(Noneの場合は追加されたセクション)
        new_heading (str | None): 新しい見出し(Noneの場合は削除されたセクション)
        old_content (str | None): 古いコンテンツ(Noneの場合は追加されたセクション)
        new_content (str | None): 新しいコンテンツ(Noneの場合は削除されたセクション)
        alignment_type (AlignmentType): アライメント種別
        similarity_score (float): 使用する類似度スコア(0.0-1.0)
        heading_similarity_score (float): 見出しの類似度スコア(0.0-1.0)
        subsection_similarity_score (float): サブセクションの見出しリストの類似度スコア(0.0-1.0)
        content_similarity_score (float): コンテンツの類似度スコア(0.0-1.0)
        subsections (list['SectionPair']): サブセクションのリスト(再帰的構造)
    """

    level: int
    old_heading: str | None
    new_heading: str | None
    old_content: str | None
    new_content: str | None
    alignment_type: AlignmentType
    similarity_score: float
    heading_similarity_score: float
    subsection_similarity_score: float
    content_similarity_score: float
    subsections: list["SectionPair"] = field(default_factory=list)

    def to_dict(self) -> dict[str, int | str | float | list[dict]]:
        """辞書形式に変換"""
        return {
            "level": self.level,
            "old_heading": self.old_heading,
            "new_heading": self.new_heading,
            "old_content": self.old_content,
            "new_content": self.new_content,
            "alignment_type": self.alignment_type.value,
            "similarity_score": self.similarity_score,
            "heading_similarity_score": self.heading_similarity_score,
            "subsection_similarity_score": self.subsection_similarity_score,
            "content_similarity_score": self.content_similarity_score,
            "subsections": [subsection.to_dict() for subsection in self.subsections],
        }

    @classmethod
    def from_dict(cls, data: dict[str, int | str | float | list[dict]]) -> "SectionPair":
        """辞書形式から作成"""
        subsections = data.get("subsections", [])

        # 再帰的にSectionPairオブジェクトに変換
        if isinstance(subsections, list) and subsections and isinstance(subsections[0], dict):
            subsections = [cls.from_dict(subsection) for subsection in subsections]

        return cls(
            level=data["level"],
            old_heading=data.get("old_heading"),
            new_heading=data.get("new_heading"),
            old_content=data.get("old_content"),
            new_content=data.get("new_content"),
            alignment_type=AlignmentType(data["alignment_type"]),
            similarity_score=data["similarity_score"],
            heading_similarity_score=data["heading_similarity_score"],
            subsection_similarity_score=data["subsection_similarity_score"],
            content_similarity_score=data["content_similarity_score"],
            subsections=subsections,
        )


@dataclass
class AlignedSentence:
    """
    アライメント結果を表すクラス

    Attributes:
        old_sentence: 古い文
        new_sentence: 新しい文
        similarity_score: 類似度スコア
        alignment_type: アライメント種別
    """

    old_sentence: str | None
    new_sentence: str | None
    similarity_score: float
    alignment_type: AlignmentType

    def to_dict(self) -> dict[str, str | float]:
        """辞書形式に変換"""
        return {
            "old_sentence": self.old_sentence,
            "new_sentence": self.new_sentence,
            "similarity_score": self.similarity_score,
            "alignment_type": self.alignment_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | float]) -> "AlignedSentence":
        """辞書形式から作成"""
        return cls(
            old_sentence=data.get("old_sentence"),
            new_sentence=data.get("new_sentence"),
            similarity_score=data["similarity_score"],
            alignment_type=AlignmentType(data["alignment_type"]),
        )


@dataclass
class SentencePair:
    """
    文ペアを表すクラス

    Attributes:
        old_heading: 古い見出し
        new_heading: 新しい見出し
        old_content: 古いコンテンツ
        new_content: 新しいコンテンツ
        overall_similarity_score: 全体の類似度スコア
        sentence_alignments: 文のアライメント結果
    """

    old_heading: str
    new_heading: str
    old_content: str
    new_content: str
    overall_similarity_score: float
    sentence_alignments: list["AlignedSentence"] = field(default_factory=list)

    def to_dict(self) -> dict[str, str | float | list[dict]]:
        """辞書形式に変換"""
        return {
            "old_heading": self.old_heading,
            "new_heading": self.new_heading,
            "old_content": self.old_content,
            "new_content": self.new_content,
            "overall_similarity_score": self.overall_similarity_score,
            "sentence_alignments": [sentence.to_dict() for sentence in self.sentence_alignments],
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | float | list[dict]]) -> "SentencePair":
        """辞書形式から作成"""
        sentence_alignments = data.get("sentence_alignments", [])
        if isinstance(sentence_alignments, list) and sentence_alignments and isinstance(sentence_alignments[0], dict):
            sentence_alignments = [AlignedSentence.from_dict(sentence) for sentence in sentence_alignments]
        return cls(
            old_heading=data["old_heading"],
            new_heading=data["new_heading"],
            old_content=data["old_content"],
            new_content=data["new_content"],
            overall_similarity_score=data["overall_similarity_score"],
            sentence_alignments=sentence_alignments,
        )
