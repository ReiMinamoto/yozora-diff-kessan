'use client';

import { useCallback, useMemo } from "react";
import type {
  DiffRecord,
  SectionContentRecord,
  Stage1Item
} from "@/app/types";
import { Lightbulb, NotebookPen } from "lucide-react";

interface Stage1ViewerProps {
  items: Stage1Item[];
  diffRecords?: DiffRecord[];
  sectionContents?: SectionContentRecord[];
}

export function Stage1Viewer({
  items,
  diffRecords,
  sectionContents
}: Stage1ViewerProps) {
  const recordMap = useMemo(() => {
    const map = new Map<number, DiffRecord[]>();
    (diffRecords ?? []).forEach((record) => {
      const current = map.get(record.editIndex) ?? [];
      current.push(record);
      map.set(record.editIndex, current);
    });
    return map;
  }, [diffRecords]);

  const handleSectionJump = useCallback((sectionIndex: number) => {
    const target = document.getElementById(`section-${sectionIndex}`);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  const hasSections = (sectionContents?.length ?? 0) > 0;

  if (!items || items.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-lg font-semibold text-slate-700">Stage1 要約</h3>
        <p className="mt-4 text-sm text-slate-500">
          Stage1の要約データが見つかりませんでした。
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item) => {
        const records = recordMap.get(item.index) ?? [];
        const primarySectionIndex =
          records[0]?.sectionIndex ?? sectionContents?.[0]?.index ?? 0;
        return (
          <div
            id={`edit-${item.index}`}
            key={item.index}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
          >
            <div className="flex items-baseline justify-between gap-4 border-b border-slate-100 pb-3">
              <h3 className="text-base font-semibold text-slate-800">
                編集 {item.index}
              </h3>
              <button
                type="button"
                onClick={() => handleSectionJump(primarySectionIndex)}
                disabled={!hasSections}
                className="text-xs font-semibold text-blue-600 transition hover:text-blue-500 disabled:cursor-not-allowed disabled:text-slate-400"
              >
                セクションにジャンプ
              </button>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-fact-border bg-fact-bg/60 p-4">
                <div className="flex items-center gap-2 text-fact-text">
                  <NotebookPen className="h-4 w-4" />
                  <span className="text-sm font-semibold">Fact</span>
                </div>
                <p className="mt-2 text-sm text-slate-700">{item.fact}</p>
              </div>

              <div className="rounded-xl border border-insight-border bg-insight-bg/70 p-4">
                <div className="flex items-center gap-2 text-insight-text">
                  <Lightbulb className="h-4 w-4" />
                  <span className="text-sm font-semibold">
                    Investor Insight
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-700">{item.insight}</p>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 p-4 text-sm leading-relaxed text-slate-700">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                対応する差分
              </p>
              <div
                id={`diff-${item.index}`}
                className="mt-2 space-y-2"
              >
                {records.length > 0 ? (
                  records.flatMap((record, recordIdx) =>
                    record.segments.map((segment, segIdx) => {
                      const lines = segment.content.split(/\n+/);
                      const content = lines.map((line, lineIdx) => (
                        <span key={lineIdx}>
                          {line}
                          {lineIdx < lines.length - 1 ? <br /> : null}
                        </span>
                      ));

                      if (segment.type === "add") {
                        return (
                          <span
                            key={`stage1-${item.index}-add-${recordIdx}-${segIdx}`}
                            className="tag-add inline-block"
                          >
                            {content}
                          </span>
                        );
                      }

                      if (segment.type === "del") {
                        return (
                          <span
                            key={`stage1-${item.index}-del-${recordIdx}-${segIdx}`}
                            className="tag-del inline-block"
                          >
                            {content}
                          </span>
                        );
                      }

                      return (
                        <span
                          key={`stage1-${item.index}-text-${recordIdx}-${segIdx}`}
                          className="inline"
                        >
                          {content}
                        </span>
                      );
                    })
                  )
                ) : (
                  <p className="text-xs text-slate-500">
                    差分データが見つかりません。Python の処理結果を確認してください。
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
