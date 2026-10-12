import { createParser } from "eventsource-parser";
import type { StreamEvent } from "@/lib/types";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public retryable = false,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Reads a JSON `{error:{code,message,retryable}}` body into an ApiError (falls back to HTTP_<status>). */
export async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as { error?: { code?: string; message?: string; retryable?: boolean } };
    const e = body.error ?? {};
    return new ApiError(e.code ?? `HTTP_${res.status}`, e.message ?? res.statusText, res.status, Boolean(e.retryable));
  } catch {
    return new ApiError(`HTTP_${res.status}`, res.statusText, res.status, res.status >= 500);
  }
}

/** POSTs and consumes a text/event-stream response, calling onEvent with parsed JSON data per event. */
export async function postSSE(
  url: string,
  body: BodyInit,
  onEvent: (e: StreamEvent) => void,
  signal?: AbortSignal,
  headers?: HeadersInit,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(url, { method: "POST", body, signal, headers: { Accept: "text/event-stream", ...headers } });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new ApiError("NETWORK", "Could not reach the analysis server.", 0, true);
  }
  if (!res.ok || !res.body) throw await toApiError(res);

  const parser = createParser({
    onEvent: (m) => onEvent({ event: m.event ?? "message", data: m.data ? JSON.parse(m.data) : null }),
  });
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    parser.feed(value);
  }
}
