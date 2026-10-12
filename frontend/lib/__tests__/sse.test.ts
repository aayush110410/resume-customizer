import { afterEach, describe, expect, it, vi } from "vitest";
import { postSSE } from "@/lib/sse";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(c) {
      chunks.forEach((x) => c.enqueue(enc.encode(x)));
      c.close();
    },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("postSSE", () => {
  it("parses events split across chunks, in order, with JSON data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          streamOf(['event: stage\ndata: {"id":"pars', 'ing","status":"done"}\n\nevent: done\ndata: {}\n\n']),
          { status: 200, headers: { "content-type": "text/event-stream" } },
        ),
      ),
    );
    const seen: { event: string; data: unknown }[] = [];
    await postSSE("/x", "{}", (e) => seen.push(e));
    expect(seen).toEqual([
      { event: "stage", data: { id: "parsing", status: "done" } },
      { event: "done", data: {} },
    ]);
  });

  it("throws ApiError carrying the server's error code on a 4xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ error: { code: "FILE_TOO_LARGE", message: "Too big", retryable: false } }, { status: 413 }),
      ),
    );
    await expect(postSSE("/x", "{}", () => {})).rejects.toMatchObject({ code: "FILE_TOO_LARGE", status: 413 });
  });

  it("maps a network failure to a retryable NETWORK error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    await expect(postSSE("/x", "{}", () => {})).rejects.toMatchObject({ code: "NETWORK", retryable: true });
  });
});

describe("postSSE truncation", () => {
  it("throws a retryable NETWORK error when the stream closes without done or error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(streamOf(['event: stage\ndata: {"id":"parsing","status":"done"}\n\n']), { status: 200 })));
    await expect(postSSE("/x", "{}", () => {})).rejects.toMatchObject({ code: "NETWORK", retryable: true });
  });
});
