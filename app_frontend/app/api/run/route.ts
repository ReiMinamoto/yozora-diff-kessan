import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { access, mkdtemp, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import type {
  ProcessedSentencePair,
  RunApiResponse,
  SectionContentRecord,
  SummaryPayload
} from "@/app/types";
import { buildDiffRecords, computeDiffMetrics } from "@/app/utils/parseTags";

async function saveUploadedFile(file: File, targetDir: string, name: string) {
  const arrayBuffer = await file.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);
  const targetPath = join(targetDir, name);
  await writeFile(targetPath, buffer);
  return targetPath;
}

async function unzipFile(zipPath: string, targetDir: string) {
  await mkdir(targetDir, { recursive: true });
  return new Promise<void>((resolveRun, rejectRun) => {
    const child = spawn("unzip", ["-oq", zipPath, "-d", targetDir]);

    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("close", (code) => {
      if (code !== 0) {
        rejectRun(new Error(stderr || `unzip exited with code ${code}`));
      } else {
        resolveRun();
      }
    });

    child.on("error", (error) => {
      rejectRun(error);
    });
  });
}

async function runPythonScript(
  pythonExecutable: string,
  scriptPath: string,
  args: string[],
  cwd: string
) {
  return new Promise<void>((resolveRun, rejectRun) => {
    const child = spawn(pythonExecutable, [scriptPath, ...args], {
      cwd,
      stdio: ["ignore", "pipe", "pipe"]
    });

    child.stdout.on("data", (chunk) => {
      process.stdout.write(chunk);
    });

    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
      process.stderr.write(chunk);
    });

    child.on("close", (code) => {
      if (code !== 0) {
        rejectRun(new Error(stderr || `Python script exited with code ${code}`));
      } else {
        resolveRun();
      }
    });

    child.on("error", (error) => {
      rejectRun(error);
    });
  });
}

async function readJsonFile<T>(path: string): Promise<T | null> {
  try {
    const content = await readFile(path, "utf8");
    return JSON.parse(content) as T;
  } catch (error) {
    console.warn(`[run/api] JSON read failed at ${path}:`, error);
    return null;
  }
}

function normalizeProcessedPairs(
  raw: Array<Record<string, unknown>>
): ProcessedSentencePair[] {
  return raw.map((pair) => ({
    oldHeading:
      (pair.oldHeading as string | undefined) ??
      (pair.old_heading as string | undefined) ??
      null,
    newHeading:
      (pair.newHeading as string | undefined) ??
      (pair.new_heading as string | undefined) ??
      null,
    processedSentencePair:
      (pair.processedSentencePair as string | undefined) ??
      (pair.processed_sentence_pair as string | undefined) ??
      ""
  }));
}

function normalizeSentencePairs(
  raw: Array<Record<string, unknown>>
): SectionContentRecord[] {
  return raw.map((pair, index) => ({
    index,
    oldHeading:
      (pair.oldHeading as string | undefined) ??
      (pair.old_heading as string | undefined) ??
      null,
    newHeading:
      (pair.newHeading as string | undefined) ??
      (pair.new_heading as string | undefined) ??
      null,
    oldContent:
      (pair.oldContent as string | undefined) ??
      (pair.old_content as string | undefined) ??
      null,
    newContent:
      (pair.newContent as string | undefined) ??
      (pair.new_content as string | undefined) ??
      null
  }));
}

async function pathExists(path: string): Promise<boolean> {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function findXbrlRoot(dir: string): Promise<string | null> {
  const queue: string[] = [dir];
  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) break;

    const xbrlDataDir = join(current, "XBRLData");
    if (await pathExists(xbrlDataDir)) {
      return current;
    }

    const entries = await readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory()) {
        queue.push(join(current, entry.name));
      }
    }
  }
  return null;
}

async function prepareDocument(file: File, tempDir: string, label: "old" | "new") {
  const lowerName = file.name.toLowerCase();
  const mime = (file.type ?? "").toLowerCase();
  const isPdf = lowerName.endsWith(".pdf") || mime === "application/pdf";
  const isZip =
    lowerName.endsWith(".zip") ||
    mime === "application/zip" ||
    mime === "application/x-zip-compressed";

  if (isPdf) {
    const filePath = await saveUploadedFile(file, tempDir, `${label}.pdf`);
    return { path: filePath, kind: "pdf" as const };
  }

  if (isZip) {
    const zipPath = await saveUploadedFile(file, tempDir, `${label}.zip`);
    const extractDir = join(tempDir, `${label}_xbrl`);
    await unzipFile(zipPath, extractDir);
    const xbrlDir = await findXbrlRoot(extractDir);
    if (!xbrlDir) {
      throw new Error("アップロードZIP内に XBRLData ディレクトリが見つかりませんでした。");
    }
    return { path: xbrlDir, kind: "xbrl" as const };
  }

  throw new Error("PDF または XBRL ZIP をアップロードしてください。");
}

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const oldDoc = (formData.get("oldDoc") ?? formData.get("oldPdf")) as File | null;
  const newDoc = (formData.get("newDoc") ?? formData.get("newPdf")) as File | null;

  if (!(oldDoc instanceof File) || !(newDoc instanceof File)) {
    return NextResponse.json<RunApiResponse>(
      {
        success: false,
        message: "oldDoc と newDoc（PDF または XBRL ZIP）の双方が必要です。"
      },
      { status: 400 }
    );
  }

  const ticker =
    (formData.get("ticker") as string | null) ??
    `temp-${new Date().toISOString().replace(/[-:TZ.]/g, "")}-${randomUUID().slice(0, 6)}`;

  try {
    const tempDir = await mkdtemp(join(tmpdir(), "yozora-diff-kessan-"));
    const oldPrepared = await prepareDocument(oldDoc, tempDir, "old");
    const newPrepared = await prepareDocument(newDoc, tempDir, "new");

    const projectRoot = resolve(process.cwd(), "..");
    const pythonExecutable = process.env.PYTHON_PATH ?? "python3";
    const scriptPath =
      process.env.SUMMARIZE_SCRIPT ??
      resolve(projectRoot, "src", "main.py");
    const resultDir = process.env.RESULT_DIR ?? resolve(projectRoot, "result");
    const tickerResultDir = join(resultDir, ticker);

    await runPythonScript(
      pythonExecutable,
      scriptPath,
      [oldPrepared.path, newPrepared.path, "--ticker", ticker, "--result-dir", resultDir],
      projectRoot
    );

    const summaryPathCandidates = [
      join(tickerResultDir, `${ticker}_summary.json`),
      join(resultDir, `${ticker}_summary.json`)
    ];
    let summaryPath = summaryPathCandidates[0];
    let summaryJson: Record<string, unknown> | null = null;
    for (const candidate of summaryPathCandidates) {
      summaryJson = await readJsonFile<Record<string, unknown>>(candidate);
      if (summaryJson) {
        summaryPath = candidate;
        break;
      }
    }

    if (!summaryJson) {
      throw new Error("Pythonスクリプトが summary JSON を生成しませんでした。");
    }

    const stage1 = (summaryJson.stage1 as string | undefined) ?? "";
    const stage2 = (summaryJson.stage2 as string | undefined) ?? "";

    const candidateDiffFiles = [
      `${ticker}_processed_aligned_sentences.json`,
      `${ticker}_aligned_sentences.json`,
      `${ticker}_processed_sentence_pairs.json`
    ];

    let processedPairs: ProcessedSentencePair[] | undefined;
    for (const filename of candidateDiffFiles) {
      const locations = [join(tickerResultDir, filename), join(resultDir, filename)];
      for (const location of locations) {
        const json = await readJsonFile<Array<Record<string, unknown>>>(location);
        if (json) {
          processedPairs = normalizeProcessedPairs(json);
          break;
        }
      }
      if (processedPairs) break;
    }

    const alignedSentencesCandidates = [
      join(tickerResultDir, `${ticker}_aligned_sentences.json`),
      join(resultDir, `${ticker}_aligned_sentences.json`)
    ];
    let alignedSentencesJson: Array<Record<string, unknown>> | null = null;
    for (const candidate of alignedSentencesCandidates) {
      alignedSentencesJson = await readJsonFile<Array<Record<string, unknown>>>(candidate);
      if (alignedSentencesJson) {
        break;
      }
    }
    const sectionContents = alignedSentencesJson
      ? normalizeSentencePairs(alignedSentencesJson)
      : undefined;

    const payload: SummaryPayload = {
      ticker,
      stage1,
      stage2,
      processedSentencePairs: processedPairs,
      resultPath: summaryPath,
      sectionContents
    };

    if (processedPairs) {
      const diffRecords = buildDiffRecords(processedPairs);
      payload.metrics = computeDiffMetrics(diffRecords);
    }

    return NextResponse.json<RunApiResponse>({
      success: true,
      payload
    });
  } catch (error) {
    console.error("[run/api] failed:", error);
    return NextResponse.json<RunApiResponse>(
      {
        success: false,
        message:
          error instanceof Error
            ? error.message
            : "Pythonスクリプトの実行に失敗しました"
      },
      { status: 500 }
    );
  }
}
