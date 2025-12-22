'use client';

import type { Stage2Cluster } from "@/app/types";
import { ArrowUpRight } from "lucide-react";
import { useCallback } from "react";

interface Stage2ViewerProps {
  clusters: Stage2Cluster[];
}

export function Stage2Viewer({ clusters }: Stage2ViewerProps) {
  const handleDiffJump = useCallback((editIndex: number) => {
    const diffTarget = document.getElementById(`diff-${editIndex}`);
    if (diffTarget) {
      diffTarget.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    const fallbackTarget = document.getElementById(`edit-${editIndex}`);
    if (fallbackTarget) {
      fallbackTarget.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, []);

  if (!clusters || clusters.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-lg font-semibold text-slate-700">Stage2 要約</h3>
        <p className="mt-4 text-sm text-slate-500">
          Stage2のクラスターデータが見つかりませんでした。
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {clusters.map((cluster) => (
        <div
          key={cluster.index}
          className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:shadow-md"
        >
          <div>
            <div className="flex items-start gap-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Cluster {cluster.index}
              </p>
              <h3 className="mt-1 text-base font-semibold text-slate-800">
                {cluster.theme || "テーマ未設定"}
              </h3>
            </div>
          </div>

          <div className="mt-4 flex flex-1 flex-col gap-3 text-sm text-slate-700">
            {cluster.summary && (
              <div>
                <p className="font-semibold text-slate-600">Summary</p>
                <p className="mt-1 leading-relaxed">{cluster.summary}</p>
              </div>
            )}

            {cluster.investorInsight && (
              <div>
                <p className="flex items-center gap-1 font-semibold text-emerald-600">
                  Investor Insight
                  <ArrowUpRight className="h-3 w-3" />
                </p>
                <p className="mt-1 leading-relaxed text-slate-700">
                  {cluster.investorInsight}
                </p>
              </div>
            )}
          </div>

          {cluster.relatedEdits.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {cluster.relatedEdits.map((edit) => (
                <button
                  key={edit}
                  type="button"
                  onClick={() => handleDiffJump(edit)}
                  className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:bg-blue-100 hover:text-blue-600"
                >
                  編集 {edit}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
