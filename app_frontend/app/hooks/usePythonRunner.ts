'use client';

import { useCallback, useMemo, useState } from "react";
import type { RunApiResponse, SummaryPayload } from "@/app/types";

export type RunnerStatus = "idle" | "running" | "success" | "error";

interface RunOptions {
  ticker?: string;
}

export function usePythonRunner() {
  const [status, setStatus] = useState<RunnerStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SummaryPayload | null>(null);

  const run = useCallback(
    async (oldFile: File, newFile: File, options?: RunOptions) => {
      setStatus("running");
      setError(null);

      try {
        const formData = new FormData();
        formData.append("oldDoc", oldFile);
        formData.append("newDoc", newFile);
        if (options?.ticker) {
          formData.append("ticker", options.ticker);
        }

        const response = await fetch("/api/run", {
          method: "POST",
          body: formData
        });

        if (!response.ok) {
          throw new Error(
            `Pythonスクリプトの呼び出しに失敗しました (HTTP ${response.status})`
          );
        }

        const data = (await response.json()) as RunApiResponse;
        if (!data.success || !data.payload) {
          throw new Error(data.message ?? "解析結果の取得に失敗しました");
        }

        setResult(data.payload);
        setStatus("success");
        return data.payload;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "不明なエラーが発生しました";
        setStatus("error");
        setError(message);
        throw err;
      }
    },
    []
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setStatus("idle");
  }, []);

  return useMemo(
    () => ({
      status,
      error,
      result,
      run,
      reset
    }),
    [status, error, result, run, reset]
  );
}
