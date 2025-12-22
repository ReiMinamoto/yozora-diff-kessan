'use client';

import { Loader2 } from "lucide-react";

interface ProgressIndicatorProps {
  label?: string;
}

export function ProgressIndicator({ label = "分析中..." }: ProgressIndicatorProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-soft">
      <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      <p className="mt-3 text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-2 text-xs text-slate-400">（2分〜4分ほどかかります）</p>
    </div>
  );
}
