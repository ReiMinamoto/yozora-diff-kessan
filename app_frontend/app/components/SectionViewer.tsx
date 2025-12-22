'use client';

import type {
  DiffRecord,
  DiffSegment,
  ProcessedSentencePair,
  SectionContentRecord
} from "@/app/types";
import { toDiffSegments } from "@/app/utils/parseTags";

interface SectionViewerProps {
  sections: SectionContentRecord[];
  diffRecords?: DiffRecord[];
  processedPairs?: ProcessedSentencePair[];
}

const isChapterOneHeading = (heading?: string | null) =>
  typeof heading === "string" && heading.startsWith("1");

const toRenderableSegments = (text: string): DiffSegment[] => {
  const segments: DiffSegment[] = [];
  const editWrapperRegex = /<edit\s+(\d+)[^>]*>([\s\S]*?)<\/edit\s+\1\s*>/g;
  let lastIndex = 0;

  let match: RegExpExecArray | null;
  while ((match = editWrapperRegex.exec(text)) !== null) {
    const [fullMatch, , body] = match;
    if (match.index > lastIndex) {
      const plainText = text.slice(lastIndex, match.index);
      if (plainText.trim().length > 0) {
        segments.push({ type: "text", content: plainText });
      }
    }
    segments.push(...toDiffSegments(body ?? ""));
    lastIndex = (match.index ?? 0) + (fullMatch?.length ?? 0);
  }

  const trailing = text.slice(lastIndex);
  if (trailing.trim().length > 0) {
    segments.push({ type: "text", content: trailing });
  }

  return segments;
};

export function SectionViewer({ sections, diffRecords, processedPairs }: SectionViewerProps) {
  const sectionMap = new Map<number, SectionContentRecord>();
  sections.forEach((section) => sectionMap.set(section.index, section));

  const processedMap = new Map<number, string>();
  processedPairs?.forEach((pair, index) => {
    if (pair.processedSentencePair) {
      processedMap.set(index, pair.processedSentencePair);
    }
  });

  const visibleSections = sections.filter(
    (section) =>
      isChapterOneHeading(section.oldHeading) && isChapterOneHeading(section.newHeading)
  );

  const filteredDiffRecords =
    diffRecords?.filter((record) => {
      const section = sectionMap.get(record.sectionIndex);
      const oldHeading = record.oldHeading ?? section?.oldHeading;
      const newHeading = record.newHeading ?? section?.newHeading;
      return isChapterOneHeading(oldHeading) && isChapterOneHeading(newHeading);
    }) ?? [];

  if (visibleSections.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft">
        <h3 className="text-lg font-semibold text-slate-700">セクション全文</h3>
        <p className="mt-4 text-sm text-slate-500">
          セクションの本文データが見つかりませんでした。
        </p>
      </div>
    );
  }

  const renderSegments = (segments: DiffSegment[], keyPrefix: string) => {
    if (segments.length === 0) {
      return null;
    }

    return (
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
        {segments.map((segment, segIdx) => {
          const lines = segment.content.split(/\n+/);
          const content = lines.map((line, idx) => (
            <span key={`${keyPrefix}-${segIdx}-${idx}`}>
              {line}
              {idx < lines.length - 1 ? <br /> : null}
            </span>
          ));

          if (segment.type === "add") {
            return (
              <span key={`${keyPrefix}-add-${segIdx}`} className="tag-add inline-block">
                {content}
              </span>
            );
          }

          if (segment.type === "del") {
            return (
              <span key={`${keyPrefix}-del-${segIdx}`} className="tag-del inline-block">
                {content}
              </span>
            );
          }

          return (
            <span key={`${keyPrefix}-text-${segIdx}`} className="inline">
              {content}
            </span>
          );
        })}
      </p>
    );
  };

  return (
    <div className="space-y-6">
      {visibleSections.map((section) => {
        const relatedRecords =
          filteredDiffRecords.filter((record) => record.sectionIndex === section.index) ?? [];
        const fallbackContent =
          section.newContent && section.newContent.length > 0
            ? section.newContent
            : section.oldContent || "—";

        const processedText = processedMap.get(section.index);
        const combinedSegments = processedText
          ? toRenderableSegments(processedText)
          : relatedRecords.flatMap((record) => record.segments);
        const hasRenderableSegments = combinedSegments.length > 0;

        return (
          <div
            key={section.index}
            id={`section-${section.index}`}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
          >
          <div className="flex flex-col gap-1 border-b border-slate-100 pb-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              セクション {section.index + 1}
            </p>
            <h3 className="text-lg font-semibold text-slate-800">
              {section.newHeading || section.oldHeading || "見出しなし"}
            </h3>
            {(section.newHeading && section.oldHeading && section.newHeading !== section.oldHeading) && (
              <p className="text-xs text-slate-500">
                旧見出し: {section.oldHeading}
              </p>
            )}
          </div>

          {hasRenderableSegments ? (
            <div className="mt-4 space-y-4">
              {renderSegments(combinedSegments, `section-${section.index}`)}
            </div>
          ) : (
            <div className="mt-4">
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {fallbackContent}
              </p>
            </div>
          )}
        </div>
        );
      })}
    </div>
  );
}
