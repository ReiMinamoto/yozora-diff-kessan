"""財務文書(PDF/XBRL)の差分解析を行うエンドツーエンドパイプライン。"""

import argparse
from collections.abc import Sequence
import json
import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_models import Section  # noqa: E402
from src.document_parser.pdf_parser import parse_document as parse_pdf_document  # noqa: E402
from src.document_parser.xbrl_parser.document import parse_document as parse_xbrl_document  # noqa: E402
from src.llm_summarizer.edit_tagger import preprocess_sentence_pairs  # noqa: E402
from src.llm_summarizer.two_stage_summarizer import two_stage_summarize  # noqa: E402
from src.text_aligner.section_aligner import align_sections  # noqa: E402
from src.text_aligner.sentence_aligner import get_aligned_sentences  # noqa: E402


def save_json(path: Path, data: object) -> None:
    """
    JSONデータをファイルに保存する。

    Args:
        path: 保存先のファイルパス
        data: 保存するデータオブジェクト
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def is_xbrl(path: Path) -> bool:
    """
    パスがXBRLディレクトリかどうかを判定する。

    Args:
        path: チェックするパス

    Returns:
        XBRLディレクトリの場合True、それ以外はFalse
    """
    if not path.exists():
        return False
    if path.is_file():
        return False
    xbrl_data_dir = path / "XBRLData"
    return xbrl_data_dir.exists() and xbrl_data_dir.is_dir()


def parse_document(doc_path: Path) -> list[Section]:
    """
    ドキュメント(PDFまたはXBRLディレクトリ)をパースする。

    Args:
        doc_path: ドキュメントのパス(PDFファイルまたはXBRLディレクトリ)

    Returns:
        パースされたセクションのリスト
    """
    if is_xbrl(doc_path):
        logging.info("Parsing XBRL: %s", doc_path)
        return parse_xbrl_document(str(doc_path))
    elif doc_path.suffix.lower() == ".pdf":
        logging.info("Parsing PDF: %s", doc_path)
        return parse_pdf_document(str(doc_path))
    else:
        raise ValueError(f"Unsupported document format: {doc_path}. Expected PDF file or XBRL directory.")


def run_pipeline(old_doc: Path, new_doc: Path, ticker: str, result_dir: Path) -> dict[str, object]:
    """
    財務文書の差分解析パイプラインを実行する。

    パース、セクションアライメント、文アライメント、編集単位の生成、LLM要約の各ステップを実行し、
    中間結果と最終要約をJSONファイルとして保存する。

    Args:
        old_doc: 古いバージョンのドキュメントパス(PDFファイルまたはXBRLディレクトリ)
        new_doc: 新しいバージョンのドキュメントパス(PDFファイルまたはXBRLディレクトリ)
        ticker: ティッカーコード(出力ファイル名に使用)
        result_dir: 結果を保存するベースディレクトリ

    Returns:
        生成された要約の辞書
    """
    logging.info("Starting pipeline for ticker '%s'", ticker)
    ticker_result_dir = result_dir / ticker
    ticker_result_dir.mkdir(parents=True, exist_ok=True)

    old_sections = parse_document(old_doc)
    new_sections = parse_document(new_doc)
    save_json(ticker_result_dir / f"{ticker}_old.json", [section.to_dict() for section in old_sections])
    save_json(ticker_result_dir / f"{ticker}_new.json", [section.to_dict() for section in new_sections])

    logging.info("Aligning sections")
    section_pairs = align_sections(old_sections, new_sections)
    save_json(ticker_result_dir / f"{ticker}_section_pairs.json", [pair.to_dict() for pair in section_pairs])

    logging.info("Aligning sentences")
    sentence_pairs = get_aligned_sentences(section_pairs)
    save_json(ticker_result_dir / f"{ticker}_aligned_sentences.json", [pair.to_dict() for pair in sentence_pairs])

    logging.info("Generating edit units")
    processed = preprocess_sentence_pairs(sentence_pairs)
    save_json(ticker_result_dir / f"{ticker}_processed_aligned_sentences.json", processed)

    logging.info("Summarising with LLM")
    summary = two_stage_summarize(processed)
    save_json(ticker_result_dir / f"{ticker}_summary.json", summary)

    logging.info("Pipeline completed")
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    コマンドライン引数をパースする。

    Args:
        argv: パースするコマンドライン引数のリスト。Noneの場合はsys.argvを使用。

    Returns:
        パースされた引数のNamespaceオブジェクト
    """
    parser = argparse.ArgumentParser(description="End-to-end pipeline for financial document diffing (PDF/XBRL).")
    parser.add_argument("old_doc", type=Path, help="Path to the old version document (PDF file or XBRL directory).")
    parser.add_argument("new_doc", type=Path, help="Path to the new version document (PDF file or XBRL directory).")
    parser.add_argument("--ticker", required=True, help="Ticker code used for output filenames.")
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=Path("result"),
        help="Base directory where intermediate artifacts and summary JSON are written. Output will be saved to result-dir/ticker.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """
    メインエントリーポイント。

    コマンドライン引数をパースし、ロギングを設定してからパイプラインを実行する。

    Args:
        argv: コマンドライン引数のリスト。Noneの場合はsys.argvを使用。
    """
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")
    run_pipeline(args.old_doc, args.new_doc, args.ticker, args.result_dir)


if __name__ == "__main__":
    main()
