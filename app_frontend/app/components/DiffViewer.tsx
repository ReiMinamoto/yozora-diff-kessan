'use client';

import type { DiffRecord } from "@/app/types";

interface DiffViewerProps {
  records: DiffRecord[];
}

export function DiffViewer({ records }: DiffViewerProps) {
  if (!records || records.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-lg font-semibold text-slate-700">差分ビュー</h3>
        <p className="mt-4 text-sm text-slate-500">
          差分情報が取得できませんでした。
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {records.map((record) => (
        <div
          key={record.editIndex}
          id={`edit-${record.editIndex}`}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
        >
          <div className="flex items-baseline justify-between gap-4 border-b border-slate-100 pb-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                編集 {record.editIndex}
              </p>
              <h3 className="text-base font-semibold text-slate-800">
                {record.newHeading || record.oldHeading || "セクション"}
              </h3>
            </div>
          </div>

          <div className="mt-4 space-y-2 text-sm leading-relaxed text-slate-700">
            {record.segments.map((segment, index) => {
              const lines = segment.content.split(/\n+/);
              const content = lines.map((line, idx) => (
                <span key={idx}>
                  {line}
                  {idx < lines.length - 1 ? <br /> : null}
                </span>
              ));

              if (segment.type === "add") {
                return (
                  <span
                    key={`${record.editIndex}-add-${index}`}
                    className="tag-add inline-block"
                  >
                    {content}
                  </span>
                );
              }

              if (segment.type === "del") {
                return (
                  <span
                    key={`${record.editIndex}-del-${index}`}
                    className="tag-del inline-block"
                  >
                    {content}
                  </span>
                );
              }

              return (
                <span
                  key={`${record.editIndex}-text-${index}`}
                  className="inline"
                >
                  {content}
                </span>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
