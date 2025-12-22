'use client';

import { useCallback, useMemo, useState } from "react";
import { AlertCircle, FileText, PieChart } from "lucide-react";
import { FileUploader } from "@/app/components/FileUploader";
import { ProgressIndicator } from "@/app/components/ProgressIndicator";
import { Stage1Viewer } from "@/app/components/Stage1Viewer";
import { Stage2Viewer } from "@/app/components/Stage2Viewer";
import { SectionViewer } from "@/app/components/SectionViewer";
import { usePythonRunner } from "@/app/hooks/usePythonRunner";
import {
  buildDiffRecords,
  parseStage1,
  parseStage2
} from "@/app/utils/parseTags";

export default function HomePage() {
  const [ticker, setTicker] = useState<string | null>(null);
  const { run, result, status, error, reset } = usePythonRunner();

  const stage1Items = useMemo(() => parseStage1(result?.stage1), [result]);
  const stage2Clusters = useMemo(() => parseStage2(result?.stage2), [result]);
  const diffRecords = useMemo(
    () => buildDiffRecords(result?.processedSentencePairs),
    [result]
  );
  const sectionRecords = useMemo(
    () => result?.sectionContents ?? [],
    [result]
  );

  const isRunning = status === "running";

  const handleSubmit = useCallback(
    async (oldFile: File, newFile: File) => {
      const generatedTicker = `temp-${Date.now().toString(36)}`;
      try {
        const payload = await run(oldFile, newFile, { ticker: generatedTicker });
        setTicker(payload?.ticker ?? generatedTicker);
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch {
        // エラーは usePythonRunner が管理
      }
    },
    [run]
  );

  const handleReset = useCallback(() => {
    reset();
    setTicker(null);
  }, [reset]);

  return (
    <main className="mx-auto max-w-6xl space-y-10 px-4 py-12">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-soft">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">
              決算短信差分要約ビューア
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-500">
              新旧2つの決算短信PDFまたはXBRL ZIPをアップロードすると、Pythonスクリプトが差分検出と要約生成を行い、結果を表示します。
            </p>
          </div>
          {result && (
            <div className="flex flex-col items-start gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-700">
              <span className="font-semibold uppercase tracking-wide">
                最新実行
              </span>
              <span>ticker: {ticker}</span>
              <button
                type="button"
                onClick={handleReset}
                className="rounded-lg border border-emerald-200 bg-white px-3 py-1 font-semibold text-emerald-600 transition hover:bg-emerald-100"
              >
                リセット
              </button>
            </div>
          )}
        </div>

        <div className="mt-8">
          <FileUploader onSubmit={handleSubmit} isLoading={isRunning} />
        </div>
      </section>

      {isRunning && (
        <section>
          <ProgressIndicator />
        </section>
      )}

      {error && (
        <section className="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-soft">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-1 h-5 w-5 text-rose-600" />
            <div>
              <h3 className="text-sm font-semibold text-rose-700">
                解析に失敗しました
              </h3>
              <p className="mt-1 text-sm text-rose-600">{error}</p>
            </div>
          </div>
        </section>
      )}

      {result && (
        <section className="space-y-8">
          <div className="grid gap-6 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="flex items-center gap-2 text-slate-600">
                <FileText className="h-5 w-5 text-blue-500" />
                <h2 className="text-base font-semibold">Stage1</h2>
              </div>
              <p className="mt-2 text-sm text-slate-500">
                個別編集ごとのFact・Investor Insightの把握
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
              <div className="flex items-center gap-2 text-slate-600">
                <PieChart className="h-5 w-5 text-emerald-500" />
                <h2 className="text-base font-semibold">Stage2</h2>
              </div>
              <p className="mt-2 text-sm text-slate-500">
                編集をテーマ別に俯瞰し、重要トピックを把握
              </p>
            </div>
            {result.metrics && (
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
                <p className="text-base font-semibold text-slate-700">
                  差分メトリクス
                </p>
                <dl className="mt-4 grid grid-cols-3 gap-2 text-center text-xs font-semibold">
                  <div className="rounded-lg bg-emerald-50 py-3 text-emerald-600">
                    <dt>Add</dt>
                    <dd className="mt-1 text-lg">{result.metrics.adds}</dd>
                  </div>
                  <div className="rounded-lg bg-rose-50 py-3 text-rose-600">
                    <dt>Del</dt>
                    <dd className="mt-1 text-lg">{result.metrics.deletes}</dd>
                  </div>
                  <div className="rounded-lg bg-slate-100 py-3 text-slate-600">
                    <dt>Edits</dt>
                    <dd className="mt-1 text-lg">{result.metrics.edits}</dd>
                  </div>
                </dl>
              </div>
            )}
          </div>

          <Stage1Viewer
            items={stage1Items}
            diffRecords={diffRecords}
            sectionContents={sectionRecords}
          />

          <Stage2Viewer clusters={stage2Clusters} />

          <div>
            <h2 className="text-lg font-semibold text-slate-800">セクション全文</h2>
            <p className="mt-1 text-sm text-slate-500">
              旧版と新版の本文を並べて比較できます。
            </p>
            <div className="mt-4">
              <SectionViewer
                sections={sectionRecords}
                diffRecords={diffRecords}
                processedPairs={result?.processedSentencePairs}
              />
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
