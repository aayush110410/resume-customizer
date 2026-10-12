import { toast } from "sonner";
import { analyze, coverLetter, tailor } from "@/lib/api";
import { messageFor } from "@/lib/errors";
import { loadSession, saveSession } from "@/lib/history";
import { ApiError } from "@/lib/sse";
import { useAppStore } from "@/lib/store";
import type { Analysis, StreamEvent, TailoredVersion, TailorSettings, Tone } from "@/lib/types";

let controller: AbortController | null = null;
const store = () => useAppStore.getState();

/** Every run cancels the previous one, so a stale stream can never write into newer results. */
function begin(): AbortSignal {
  controller?.abort();
  controller = new AbortController();
  return controller.signal;
}

function report(err: unknown, signal: AbortSignal) {
  if (signal.aborted) return;
  const e = err instanceof ApiError ? { code: err.code, retryable: err.retryable } : { code: "INTERNAL", retryable: true };
  const info = { ...e, message: messageFor(e.code) };
  store().setError(info);
  toast.error(info.message);
}

function surfaceStreamError() {
  const err = store().error;
  if (err) toast.error(messageFor(err.code));
}

async function persist() {
  const s = store();
  if (!s.analysis || !s.sessionId) return;
  try {
    await saveSession({
      id: s.sessionId, created_at: s.sessionStartedAt ?? new Date().toISOString(), jd_title: s.analysis.jd.title,
      region: s.analysis.region, analysis: s.analysis, versions: s.versions, cover_letter: s.coverLetter,
    });
  } catch {
    /* private mode / storage blocked: history is a convenience */
  }
}

async function tailorInto(run: number, analysis: Analysis, settings: TailorSettings, signal: AbortSignal) {
  store().setBusy("tailoring");
  let version: TailoredVersion | undefined;
  await tailor(analysis, settings, (e: StreamEvent) => {
    store().applyEvent(run, e);
    if (e.event === "done") version = (e.data as { version: TailoredVersion }).version;
  }, signal);
  if (version && !signal.aborted) {
    store().addVersion(version);
    await persist();
  } else surfaceStreamError();
}

export async function runAnalyzeAndTailor() {
  const signal = begin();
  const { jd, file, region, sections, tone, model } = store().inputs;
  if (!file) return;
  store().resetSession();
  const run = store().startRun();
  store().setBusy("analyzing");
  try {
    let analysis: Analysis | undefined;
    await analyze(file, jd.trim(), region, (e) => {
      store().applyEvent(run, e);
      if (e.event === "done") analysis = (e.data as { analysis: Analysis }).analysis;
    }, signal);
    if (!analysis) return surfaceStreamError();
    store().setAnalysis(analysis);
    await persist();
    await tailorInto(run, analysis, { sections, tone, model }, signal);
  } catch (err) {
    report(err, signal);
  } finally {
    if (!signal.aborted) store().setBusy("idle");
  }
}

export async function runNewVersion(settings: TailorSettings) {
  const analysis = store().analysis;
  if (!analysis) return;
  const signal = begin();
  const run = store().startRun();
  try {
    await tailorInto(run, analysis, settings, signal);
  } catch (err) {
    report(err, signal);
  } finally {
    if (!signal.aborted) store().setBusy("idle");
  }
}

export async function runCoverLetter(opts: { tone: Tone; notice_period: string | null; work_authorization: string | null }) {
  const s = store();
  const analysis = s.analysis;
  if (!analysis) return;
  const resume = s.versions.find((v) => v.id === s.activeVersionId)?.resume ?? analysis.resume;
  const signal = begin();
  const run = s.startRun();
  s.setCoverLetter("");
  s.setBusy("letter");
  try {
    let text: string | undefined;
    await coverLetter({ analysis, resume, model: s.inputs.model, ...opts }, (e) => {
      store().applyEvent(run, e);
      if (e.event === "done") text = (e.data as { text: string }).text;
    }, signal);
    if (text !== undefined) {
      store().setCoverLetter(text);
      await persist();
    } else surfaceStreamError();
  } catch (err) {
    report(err, signal);
  } finally {
    if (!signal.aborted) store().setBusy("idle");
  }
}

export async function restoreSession(id: string) {
  const record = await loadSession(id);
  if (record) {
    begin();
    store().hydrate(record);
  }
}

export const saveCoverLetterEdit = persist;
