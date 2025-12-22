import type {
  DiffMetrics,
  DiffRecord,
  DiffSegment,
  ProcessedSentencePair,
  Stage1Item,
  Stage2Cluster
} from "@/app/types";

const editBlockRegex = /<edit\s+(\d+)\s+Desc>\s*([\s\S]*?)<\/edit\s+\1\s+Desc>/g;
const clusterBlockRegex = /<Cluster\s+(\d+)\s+Desc>\s*([\s\S]*?)<\/Cluster\s+\1\s+Desc>/g;
const addDelRegex = /<(add|del)>([\s\S]*?)<\/\1>/g;
const editWrapperRegex = /<edit\s+(\d+)[^>]*>([\s\S]*?)<\/edit\s+\1\s*>/g;

const normalizeWhitespace = (value: string) =>
  value.replace(/\s+/g, " ").trim();

export function parseStage1(raw: string | null | undefined): Stage1Item[] {
  if (!raw) {
    return [];
  }

  const results: Stage1Item[] = [];
  let match: RegExpExecArray | null;

  while ((match = editBlockRegex.exec(raw)) !== null) {
    const index = Number.parseInt(match[1], 10);
    const body = match[2] ?? "";

    const factMatch = body.match(/【Fact】([\s\S]*?)(?=【|$)/);
    const insightMatch = body.match(/【(?:Investor Insight|Implication)】([\s\S]*?)(?=【|$)/);

    results.push({
      index,
      fact: normalizeWhitespace(factMatch?.[1] ?? ""),
      insight: normalizeWhitespace(insightMatch?.[1] ?? "")
    });
  }

  return results;
}

export function parseStage2(raw: string | null | undefined): Stage2Cluster[] {
  if (!raw) {
    return [];
  }

  const clusters: Stage2Cluster[] = [];
  let match: RegExpExecArray | null;

  while ((match = clusterBlockRegex.exec(raw)) !== null) {
    const index = Number.parseInt(match[1], 10);
    const body = match[2] ?? "";
    const themeMatch = body.match(/【Theme】([\s\S]*?)(?=【|$)/);
    const summaryMatch = body.match(/【Summary】([\s\S]*?)(?=【|$)/);
    const insightMatch = body.match(/【Investor Insight】([\s\S]*?)(?=【|$)/);

    const relatedLine = body
      .split(/\n+/)
      .find((line) => line.includes("該当する編集番号"));

    const relatedEdits =
      relatedLine?.match(/\d+/g)?.map((num) => Number.parseInt(num, 10)) ?? [];

    clusters.push({
      index,
      theme: normalizeWhitespace(themeMatch?.[1] ?? ""),
      summary: normalizeWhitespace(summaryMatch?.[1] ?? ""),
      investorInsight: normalizeWhitespace(insightMatch?.[1] ?? ""),
      relatedEdits
    });
  }

  return clusters;
}

export function toDiffSegments(raw: string): DiffSegment[] {
  const cleaned = raw;
  const segments: DiffSegment[] = [];
  let lastIndex = 0;

  let match: RegExpExecArray | null;
  while ((match = addDelRegex.exec(cleaned)) !== null) {
    const [fullMatch, type, content] = match;
    if (match.index > lastIndex) {
      const plainText = cleaned.slice(lastIndex, match.index);
      if (plainText.trim().length > 0) {
        segments.push({ type: "text", content: plainText });
      }
    }
    segments.push({
      type: type === "add" ? "add" : "del",
      content: content ?? ""
    });
    lastIndex = (match.index ?? 0) + (fullMatch?.length ?? 0);
  }

  const trailing = cleaned.slice(lastIndex);
  if (trailing.trim().length > 0) {
    segments.push({ type: "text", content: trailing });
  }

  return segments;
}

export function buildDiffRecords(
  pairs: ProcessedSentencePair[] | null | undefined
): DiffRecord[] {
  if (!pairs || pairs.length === 0) {
    return [];
  }

  const results: DiffRecord[] = [];

  pairs.forEach((pair, pairIndex) => {
    const text = pair.processedSentencePair ?? "";
    let match: RegExpExecArray | null;
    while ((match = editWrapperRegex.exec(text)) !== null) {
      const editIndex = Number.parseInt(match[1], 10);
      const body = match[2] ?? "";
      const segments = toDiffSegments(body);
      results.push({
        editIndex,
        sectionIndex: pairIndex,
        oldHeading: pair.oldHeading,
        newHeading: pair.newHeading,
        segments
      });
    }
  });

  return results.sort((a, b) => a.editIndex - b.editIndex);
}

export function computeDiffMetrics(records: DiffRecord[]): DiffMetrics {
  return records.reduce(
    (acc, record) => {
      for (const segment of record.segments) {
        if (segment.type === "add") {
          acc.adds += 1;
        } else if (segment.type === "del") {
          acc.deletes += 1;
        }
      }
      acc.edits += 1;
      return acc;
    },
    { adds: 0, deletes: 0, edits: 0 }
  );
}
