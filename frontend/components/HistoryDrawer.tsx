"use client";

import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { restoreSession } from "@/lib/flow";
import { deleteSession, listSessions, type SessionSummary } from "@/lib/history";

export function HistoryDrawer({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [items, setItems] = useState<SessionSummary[]>([]);
  useEffect(() => {
    if (open) listSessions().then(setItems).catch(() => setItems([]));
  }, [open]);
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-sm border-l border-rule bg-shell p-7">
        <SheetHeader className="p-0">
          <SheetTitle className="text-[22px] font-medium tracking-[-0.018em]">History</SheetTitle>
          <SheetDescription className="text-[13px] text-ink-3">Saved only in this browser. No account, nothing on our servers.</SheetDescription>
        </SheetHeader>
        {items.length === 0 ? (
          <p className="mt-6 text-[13.5px] text-ink-3">No past analyses yet.</p>
        ) : (
          <ul className="mt-5">
            {items.map((s) => (
              <li key={s.id} className="ledger-row flex items-center gap-3 border-t border-rule-list py-3">
                <button type="button" className="flex-1 text-left" onClick={() => { void restoreSession(s.id); onOpenChange(false); }}>
                  <div className="text-[14px] text-ink">{s.jd_title}</div>
                  <div className="figure text-[12px] text-ink-3">
                    {new Date(s.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })} · {s.region === "india" ? "India" : "International"} · best {s.best_overall}
                  </div>
                </button>
                <button type="button" aria-label={`Delete ${s.jd_title}`} className="grid size-10 place-items-center text-ink-3 hover:text-down"
                  onClick={async () => { await deleteSession(s.id); setItems((x) => x.filter((i) => i.id !== s.id)); }}>
                  <Trash2 className="size-4" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        )}
      </SheetContent>
    </Sheet>
  );
}
