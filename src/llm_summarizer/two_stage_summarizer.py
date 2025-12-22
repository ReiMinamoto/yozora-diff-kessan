"""二段階LLM要約を実行するモジュール。

Google GeminiまたはOpenAI APIを使用して、財務文書の差分を二段階で要約します。
Stage 1では各編集の説明を生成し、Stage 2ではテーマ別の要約を生成します。
"""

import os

from dotenv import load_dotenv
from google import genai
import openai

from src.llm_summarizer.prompts import (
    STAGE1_SYSTEM_PROMPT_TEMPLATE,
    STAGE1_USER_PROMPT_TEMPLATE,
    STAGE2_SYSTEM_PROMPT_TEMPLATE,
    STAGE2_USER_PROMPT_TEMPLATE,
)

GOOGLE_API_MODEL = "gemini-2.5-pro"
OPENAI_API_MODEL = "gpt-5"


def create_client() -> genai.Client | openai.OpenAI | None:
    """
    LLM APIクライアントを作成する。
    GOOGLE_API_KEYが設定されている場合はGoogle Geminiを優先し、それがない場合はOPENAI_API_KEYが設定されていればOpenAIを使用します。

    Returns:
        Google GeminiまたはOpenAIのクライアントインスタンス。APIキーが設定されていない、またはクライアント作成に失敗した場合はNone。
    """
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if google_api_key:
        try:
            return genai.Client(api_key=google_api_key)
        except Exception:
            return None
    elif openai_api_key:
        try:
            return openai.OpenAI(api_key=openai_api_key)
        except Exception:
            return None
    else:
        return None


CLIENT = create_client()


def ensure_client() -> genai.Client | openai.OpenAI:
    """
    利用可能なLLMクライアントを取得する。

    Returns:
        利用可能なLLMクライアントインスタンス。

    Raises:
        RuntimeError: クライアントが利用できない場合。
    """
    if CLIENT is None:
        raise RuntimeError("Client is not available.")
    return CLIENT


def generate_response(client: genai.Client | openai.OpenAI, prompt: str) -> str:
    """
    LLMクライアントを使用してプロンプトに対する応答を生成する。

    Args:
        client: LLMクライアントインスタンス(Google GeminiまたはOpenAI)。
        prompt: LLMに送信するプロンプト文字列。

    Returns:
        LLMが生成した応答テキスト(前後の空白を除去したもの)。

    Raises:
        RuntimeError: クライアントの種類が不明な場合。
    """
    if isinstance(client, genai.Client):
        google_api_model = os.getenv("GOOGLE_API_MODEL")
        if not google_api_model:
            google_api_model = GOOGLE_API_MODEL
        return client.models.generate_content(model=google_api_model, contents=prompt).text.strip()
    elif isinstance(client, openai.OpenAI):
        openai_api_model = os.getenv("OPENAI_API_MODEL")
        if not openai_api_model:
            openai_api_model = OPENAI_API_MODEL
        return client.responses.create(model=openai_api_model, input=prompt).output_text.strip()
    else:
        raise RuntimeError("Client is not available.")


def generate_edit_descriptions(diff_text: str) -> str:
    """
    diffフォーマット入力からedit説明を生成する(Stage 1)。

    Args:
        diff_text: 差分テキスト(旧版と新版の対応箇所を示すdiff形式の文字列)。

    Returns:
        各編集について【Fact】と【Investor Insight】を含む説明テキスト。
    """
    client = ensure_client()
    user_prompt = STAGE1_USER_PROMPT_TEMPLATE.format(diff_text=diff_text)
    prompt = f"{STAGE1_SYSTEM_PROMPT_TEMPLATE}\n\n{user_prompt}"
    response = generate_response(client, prompt)
    return response


def generate_thematic_summary(edit_descriptions: str) -> str:
    """
    edit説明リストをもとにテーマ要約を生成する(Stage 2)。

    Args:
        edit_descriptions: Stage 1で生成された編集説明のテキスト。

    Returns:
        テーマ別にクラスタリングされた要約テキスト。
    """
    client = ensure_client()
    user_prompt = STAGE2_USER_PROMPT_TEMPLATE.format(edit_descriptions=edit_descriptions)
    prompt = f"{STAGE2_SYSTEM_PROMPT_TEMPLATE}\n\n{user_prompt}"
    response = generate_response(client, prompt)
    return response


def _fallback_stage1(processed: list[dict]) -> str:
    """
    Stage 1のフォールバック処理を実行する。

    Args:
        processed: 処理済みの文ペアデータのリスト。

    Returns:
        フォールバック用の編集説明テキスト。
    """
    if not processed:
        return "<edit 0 Desc>\n【Fact】差分データがありません。\n【Investor Insight】入力を確認してください。\n</edit 0 Desc>"
    return "<edit 0 Desc>\n【Fact】詳細は差分ビューで確認してください。（オフライン要約）\n【Investor Insight】\n</edit 0 Desc>"


def _fallback_stage2(processed: list[dict]) -> str:
    """
    Stage 2のフォールバック処理を実行する。

    Args:
        processed: 処理済みの文ペアデータのリスト。

    Returns:
        フォールバック用のテーマ要約テキスト。
    """
    return (
        "<Cluster 0 Desc>\n"
        "【Theme】ローカル要約のみ\n"
        "【Summary】API キーが設定されていない、またはアクセスできないため、"
        "自動要約は実行されていません。差分ビューを参照してください。\n"
        "【Investor Insight】重要な変更点は差分ビューから直接確認してください。\n"
        "</Cluster 0 Desc>"
    )


def two_stage_summarize(processed: list[dict]) -> dict[str, str]:
    """
    処理済みデータから二段階処理を通して最終要約を生成する。

    Stage 1で各編集の説明を生成し、Stage 2でテーマ別の要約を生成します。
    LLM APIが利用できない場合は、フォールバック処理を実行します。

    Args:
        processed: 処理済みの文ペアデータのリスト。
                  各要素は"old_heading"、"new_heading"、"processed_sentence_pair"を含む辞書。

    Returns:
        "stage1"と"stage2"をキーとする要約結果の辞書。
    """
    if CLIENT is None:
        stage1_output = _fallback_stage1(processed)
        stage2_output = _fallback_stage2(processed)
        return {"stage1": stage1_output, "stage2": stage2_output}

    diff_text = ""
    for p in processed:
        if p["old_heading"].startswith("1") and p["new_heading"].startswith("1"):
            # 差分の要約対象は1章目の定性的情報のみに限定する。財務諸表や注記の差分は要約しない。
            diff_text += p["old_heading"] + " -> " + p["new_heading"] + "\n" + p["processed_sentence_pair"] + "\n\n"
    try:
        stage1_output = generate_edit_descriptions(diff_text)
        stage2_output = generate_thematic_summary(stage1_output)
        return {"stage1": stage1_output, "stage2": stage2_output}
    except Exception:
        stage1_output = _fallback_stage1(processed)
        stage2_output = _fallback_stage2(processed)
        return {"stage1": stage1_output, "stage2": stage2_output}
