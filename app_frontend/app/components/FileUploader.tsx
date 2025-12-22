'use client';

import { useCallback, useMemo, useState } from "react";
import { UploadCloud } from "lucide-react";

interface FileUploaderProps {
  onSubmit: (oldFile: File, newFile: File) => Promise<void> | void;
  isLoading?: boolean;
}

export function FileUploader({ onSubmit, isLoading }: FileUploaderProps) {
  const [oldFile, setOldFile] = useState<File | null>(null);
  const [newFile, setNewFile] = useState<File | null>(null);

  const isReady = useMemo(() => Boolean(oldFile && newFile && !isLoading), [oldFile, newFile, isLoading]);

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!oldFile || !newFile) {
        return;
      }
      await onSubmit(oldFile, newFile);
    },
    [oldFile, newFile, onSubmit]
  );

  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>, kind: "old" | "new") => {
      const file = event.target.files?.[0];
      if (kind === "old") {
        setOldFile(file ?? null);
      } else {
        setNewFile(file ?? null);
      }
    },
    []
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-soft"
    >
      <div>
        <h2 className="text-lg font-semibold text-slate-800">
          新旧PDF / XBRL ZIP をアップロード
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          PDFに加え、TDNETで配布されるXBRLのZIPファイルもアップロードできます。
          2つのファイルを選択すると差分生成ボタンが有効になります。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex h-32 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 transition hover:border-blue-400 hover:bg-blue-50">
          <UploadCloud className="mb-2 h-6 w-6 text-blue-500" />
          <span className="text-sm font-medium text-slate-600">旧PDF / XBRL</span>
          <span className="mt-1 text-xs text-slate-400">
            {oldFile ? oldFile.name : "ファイルを選択"}
          </span>
          <input
            type="file"
            accept=".pdf,.zip"
            className="hidden"
            onChange={(event) => handleFileChange(event, "old")}
          />
        </label>

        <label className="flex h-32 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 transition hover:border-blue-400 hover:bg-blue-50">
          <UploadCloud className="mb-2 h-6 w-6 text-emerald-500" />
          <span className="text-sm font-medium text-slate-600">新PDF / XBRL</span>
          <span className="mt-1 text-xs text-slate-400">
            {newFile ? newFile.name : "ファイルを選択"}
          </span>
          <input
            type="file"
            accept=".pdf,.zip"
            className="hidden"
            onChange={(event) => handleFileChange(event, "new")}
          />
        </label>
      </div>

      <button
        type="submit"
        disabled={!isReady}
        className="inline-flex w-full items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {isLoading ? "解析中..." : "差分生成"}
      </button>
    </form>
  );
}
