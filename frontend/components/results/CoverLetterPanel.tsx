"use client";

import { useState } from "react";
import { Copy, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { OutlineButton, Segmented } from "@/components/ledger";
import { TONES } from "@/components/input/InputPanel";
import { DownloadMenu } from "@/components/results/DownloadMenu";
import { runCoverLetter, saveCoverLetterEdit } from "@/lib/flow";
import { useAppStore } from "@/lib/store";
import type { Tone } from "@/lib/types";

export function CoverLetterPanel() {
  const { analysis, coverLetter, setCoverLetter, busy, versions, activeVersionId } = useAppStore();
  const [tone, setTone] = useState<Tone>("balanced");
  const [notice, setNotice] = useState("");
  const [auth, setAuth] = useState("");
  if (!analysis) return null;
  const intl = analysis.region === "international";
  const contact = (versions.find((v) => v.id === activeVersionId)?.resume ?? analysis.resume).contact;
  const field = "min-h-10 rounded-full border border-rule-control bg-[rgba(0,0,0,0.22)] px-4 text-[13.5px] text-ink placeholder:text-ink-3/70 focus:border-gold/60 focus:outline-none";

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-2 text-[13px] text-ink-3">
          Notice period / availability (optional)
          <input className={field} value={notice} onChange={(e) => setNotice(e.target.value)} placeholder={intl ? "e.g. Available from March 2027" : "e.g. 30 days, can be bought out"} />
        </label>
        <label className="flex flex-col gap-2 text-[13px] text-ink-3">
          Work authorisation {intl ? "(recommended abroad)" : "(optional)"}
          <input className={field} value={auth} onChange={(e) => setAuth(e.target.value)} placeholder={intl ? "e.g. Requires H-1B sponsorship" : "e.g. Indian citizen"} />
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="w-full max-w-sm"><Segmented label="Letter tone" value={tone} options={TONES} onChange={setTone} /></div>
        <OutlineButton
          className="border-gold/60 text-gold"
          disabled={busy !== "idle"}
          onClick={() => runCoverLetter({ tone, notice_period: notice.trim() || null, work_authorization: auth.trim() || null })}
        >
          {busy === "letter" && <Loader2 className="size-3.5 animate-spin" aria-hidden />}
          {coverLetter ? "Rewrite letter" : "Write cover letter"}
        </OutlineButton>
      </div>
      {(coverLetter || busy === "letter") && (
        <>
          <textarea
            aria-label="Cover letter"
            value={coverLetter}
            onChange={(e) => setCoverLetter(e.target.value)}
            onBlur={() => void saveCoverLetterEdit()}
            className="min-h-[420px] w-full resize-y rounded-[14px] border border-rule-control bg-[rgba(0,0,0,0.22)] px-5 py-4 text-[14px] leading-[1.75] text-ink-2 focus:border-gold/60 focus:outline-none"
          />
          <div className="flex flex-wrap items-center gap-2">
            <OutlineButton onClick={() => navigator.clipboard.writeText(coverLetter).then(() => toast.success("Copied"))}>
              <Copy className="size-3.5" aria-hidden />Copy
            </OutlineButton>
            <DownloadMenu label="Download letter" request={{ kind: "cover_letter", region: analysis.region, cover_letter: coverLetter, contact }} />
          </div>
        </>
      )}
    </div>
  );
}
