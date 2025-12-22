export interface ProcessedSentencePair {
  oldHeading: string | null;
  newHeading: string | null;
  processedSentencePair: string;
}

export interface SummaryPayload {
  ticker: string;
  stage1: string;
  stage2: string;
  processedSentencePairs?: ProcessedSentencePair[];
  resultPath?: string;
  metrics?: DiffMetrics;
  sectionContents?: SectionContentRecord[];
}

export interface DiffMetrics {
  adds: number;
  deletes: number;
  edits: number;
}

export interface Stage1Item {
  index: number;
  fact: string;
  insight: string;
}

export interface Stage2Cluster {
  index: number;
  theme: string;
  summary: string;
  investorInsight?: string;
  relatedEdits: number[];
}

export interface DiffSegment {
  type: "text" | "add" | "del";
  content: string;
}

export interface DiffRecord {
  editIndex: number;
  sectionIndex: number;
  oldHeading?: string | null;
  newHeading?: string | null;
  segments: DiffSegment[];
}

export interface SectionContentRecord {
  index: number;
  oldHeading?: string | null;
  newHeading?: string | null;
  oldContent?: string | null;
  newContent?: string | null;
}

export interface RunRequestBody {
  ticker?: string;
}

export interface RunApiResponse {
  success: boolean;
  message?: string;
  payload?: SummaryPayload;
}
