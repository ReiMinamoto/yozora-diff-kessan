# 決算短信の差分検知 & ローカル要約ビューア

## 概要

旧版・新版の決算短信 PDF/XBRL ZIP を突き合わせ、セクション/文単位の差分取得と2段階要約を行います。  
Next.js 製ローカル UI から PDF をアップロードすると、Python パイプラインが自動実行され、`result/` 配下に生成された JSON を可視化します。

## 準備

- Python 3.13+
- Node.js 18 以上
- (任意) LLM API Key  
  - Google Gemini または OpenAI のどちらか1つで動作します

## 環境変数の設定

本プロジェクトでは `.env` ファイルから環境変数を読み込みます。  
サンプルとして `.env.example` を用意しているので、コピーしてください。

```bash
cp .env.example .env
```

その後 `.env` 内を編集します。

> **補足**  
> - Google GeminiとOpenAI両方のapiキーが存在する場合、Geminiが優先して使用されます。

## 対応ファイル

アップロード時に選択できます。

| 形式       | サポート           |
| -------- | -------------- |
| PDF      | ✔️             |
| XBRL ZIP | ✔️（TDNET 配布形式） |

<XBRL ZIPの構造>
- TDNETから配布されるZIPをそのままアップロード可能です

## ローカル UI の起動

```bash
# 仮想環境の作成（初回のみ）
uv venv

# 仮想環境のactivate
source .venv/bin/activate

# 依存関係のインストール（初回のみ）
uv sync

# 依存インストール＆Next.js 開発サーバ起動
./run_app.sh
```

1. ブラウザで <http://localhost:3000> を開く
2. 「旧PDF/XBRL ZIP」「新PDF/XBRL XIP」を選択 → 「差分生成」を押下
3. Python パイプラインが `src/main.py` 経由で実行され、`result/<ticker>/<ticker>_summary.json` などが生成
4. UIに要約、差分ビューが表示されます

> **補足**  
> - UI 側は内部でランダム ticker (`temp-xxxxx`) を付与します。  
> - 解析後は `result/` に旧/新 JSON, アライメント結果, 要約が残ります。再実行の際は必要に応じて削除してください。
> - LLMのapiキーがない場合は、差分のみ可視化されます。   

## ライセンス

本プロジェクトはMITライセンスの下で公開されています。詳細についてはLICENSE.txtファイルをご確認ください。
