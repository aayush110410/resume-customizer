"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { OutlineButton } from "@/components/ledger";
import { downloadBlob, exportFile } from "@/lib/api";
import { messageFor } from "@/lib/errors";
import { ApiError } from "@/lib/sse";
import type { ExportRequest } from "@/lib/types";

export function DownloadMenu({ request, label = "Download" }: { request: Omit<ExportRequest, "format">; label?: string }) {
  const [busy, setBusy] = useState<string | null>(null);
  const go = async (format: ExportRequest["format"]) => {
    setBusy(format);
    try {
      const { blob, filename } = await exportFile({ ...request, format });
      downloadBlob(blob, filename);
    } catch (e) {
      toast.error(messageFor(e instanceof ApiError ? e.code : "INTERNAL"));
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label={label}>
      {(["pdf", "docx", "txt"] as const).map((f) => (
        <OutlineButton key={f} onClick={() => go(f)} disabled={busy !== null} aria-label={`${label} as ${f.toUpperCase()}`}>
          {busy === f ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <Download className="size-3.5" aria-hidden />}
          {f.toUpperCase()}
        </OutlineButton>
      ))}
    </div>
  );
}
