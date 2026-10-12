"use client";

import { FileText, Upload, X } from "lucide-react";
import { useDropzone } from "react-dropzone";
import { cn } from "@/lib/utils";
import { formatBytes } from "@/lib/validation";

export function ResumeDropzone({ file, onFile, error }: { file: File | null; onFile: (f: File | null) => void; error?: string }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    multiple: false,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    onDrop: (accepted, rejected) => onFile(accepted[0] ?? (rejected[0]?.file as File | undefined) ?? null),
  });

  if (file) {
    return (
      <div className={cn("flex min-h-14 items-center gap-3 border px-3", error ? "border-down/60" : "border-rule-control")}>
        <FileText className="size-4 shrink-0 text-gold" aria-hidden />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13.5px] text-ink">{file.name}</div>
          <div className="figure text-[12px] text-ink-3">{formatBytes(file.size)}</div>
        </div>
        <button type="button" onClick={() => onFile(null)} aria-label="Remove file" className="grid size-10 place-items-center text-ink-3 hover:text-ink">
          <X className="size-4" aria-hidden />
        </button>
      </div>
    );
  }
  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex min-h-24 cursor-pointer flex-col items-center justify-center gap-1.5 border border-dashed px-4 text-center transition-colors duration-200",
        isDragActive ? "border-gold bg-gold/5" : error ? "border-down/60" : "border-rule-control hover:border-gold/60",
      )}
    >
      <input {...getInputProps()} aria-label="Upload resume" />
      <Upload className="size-4 text-gold" aria-hidden />
      <div className="text-[13.5px] text-ink">Drop your resume, or browse</div>
      <div className="text-[12px] text-ink-3">PDF or DOCX · up to 5 MB · 5 pages</div>
    </div>
  );
}
