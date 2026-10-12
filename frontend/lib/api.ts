import { ApiError, postSSE, toApiError } from "@/lib/sse";
import type { Analysis, CoverLetterRequest, ExportRequest, Meta, Region, StreamEvent, TailorSettings } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
type OnEvent = (e: StreamEvent) => void;
const JSON_HEADERS = { "Content-Type": "application/json" };

export async function getMeta(): Promise<Meta> {
  const res = await fetch(`${API_URL}/api/meta`);
  if (!res.ok) throw await toApiError(res);
  return res.json();
}

/** Round-trip time to /health in ms; throws when the server is unreachable. */
export async function ping(signal?: AbortSignal): Promise<number> {
  const t0 = performance.now();
  const res = await fetch(`${API_URL}/health`, { signal, cache: "no-store" });
  if (!res.ok) throw new ApiError(`HTTP_${res.status}`, "Health check failed", res.status, true);
  return performance.now() - t0;
}

export function analyze(file: File, jd: string, region: Region, onEvent: OnEvent, signal?: AbortSignal) {
  const form = new FormData();
  form.append("file", file);
  form.append("jd", jd);
  form.append("region", region);
  return postSSE(`${API_URL}/api/analyze`, form, onEvent, signal);
}

export function tailor(analysis: Analysis, settings: TailorSettings, onEvent: OnEvent, signal?: AbortSignal) {
  return postSSE(`${API_URL}/api/tailor`, JSON.stringify({ analysis, settings }), onEvent, signal, JSON_HEADERS);
}

export function coverLetter(req: CoverLetterRequest, onEvent: OnEvent, signal?: AbortSignal) {
  return postSSE(`${API_URL}/api/cover-letter`, JSON.stringify(req), onEvent, signal, JSON_HEADERS);
}

export async function exportFile(req: ExportRequest): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`${API_URL}/api/export`, { method: "POST", body: JSON.stringify(req), headers: JSON_HEADERS });
  if (!res.ok) throw await toApiError(res);
  const disposition = res.headers.get("content-disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? `export.${req.format}`;
  return { blob: await res.blob(), filename };
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
