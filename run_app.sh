#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONT_DIR="$ROOT_DIR/app_frontend"

if [ ! -d "$FRONT_DIR" ]; then
  echo "app_frontend ディレクトリが見つかりません。"
  exit 1
fi

cd "$FRONT_DIR"

if [ ! -d "node_modules" ]; then
  echo "依存関係をインストールします..."
  npm install
fi

echo "Next.js 開発サーバーを起動します (http://localhost:3000)"
npm run dev
