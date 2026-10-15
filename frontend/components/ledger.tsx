"use client";

import { useRef, type ButtonHTMLAttributes, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { MatchStatus } from "@/lib/types";

/** Shared Meridian-ledger primitives: hairline controls, outline chips, tracked labels. */

export function Label({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("eyebrow", className)}>{children}</div>;
}

export function CardTitle({ children, meta }: { children: ReactNode; meta?: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <h3 className="text-[21px] font-medium tracking-[-0.018em] text-ink">{children}</h3>
      {meta && <span className="text-[12.5px] text-ink-3">{meta}</span>}
    </div>
  );
}

const PILL = "min-h-10 rounded-full px-4 text-[13.5px] font-medium whitespace-nowrap transition-[color,background-color,border-color,box-shadow] duration-300";
const PILL_ON = "bg-[image:var(--cta-buy)] text-on-gold shadow-[0_10px_26px_-12px_rgba(217,189,139,0.6)]";
const PILL_OFF = "border border-rule-control text-ink-3 hover:border-[rgba(217,189,139,0.3)] hover:text-ink";

export function OutlineButton({ className, tone = "plain", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "plain" | "gold" }) {
  return (
    <button
      type="button"
      {...props}
      className={cn(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-full border px-4 text-[13.5px] font-medium transition-colors duration-300",
        "disabled:pointer-events-none disabled:opacity-40",
        tone === "gold"
          ? "border-gold-deep bg-[var(--tint-gold)] text-gold hover:border-gold hover:text-gold-hi"
          : "border-rule-control text-ink-2 hover:border-gold hover:text-ink",
        className,
      )}
    />
  );
}

export function Segmented<T extends string>({
  value, options, onChange, label,
}: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn(PILL, value === o.value ? PILL_ON : PILL_OFF)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function ToggleChip({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "min-h-9 rounded-full border px-3.5 text-[13px] font-medium transition-colors duration-300",
        on
          ? "border-[rgba(217,189,139,0.28)] bg-[rgba(217,189,139,0.14)] text-gold"
          : "border-rule-control text-ink-3 hover:border-[rgba(217,189,139,0.3)] hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

const STATUS: Record<MatchStatus, { code: string; word: string; cls: string }> = {
  strong: { code: "STRONG", word: "Evidenced", cls: "border-up/40 text-up" },
  partial: { code: "PARTIAL", word: "Listed, thin", cls: "border-gold-dim/50 text-gold-dim" },
  transferable: { code: "TRANSFER", word: "Adjacent", cls: "border-slate/40 text-slate" },
  missing: { code: "MISSING", word: "No evidence", cls: "border-down/40 text-down" },
};

export function StatusChip({ status }: { status: MatchStatus }) {
  const s = STATUS[status];
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-[0.1em]", s.cls)} title={s.word}>
      {s.code}
    </span>
  );
}

export function Chip({ children, tone = "neutral", title }: { children: ReactNode; tone?: "neutral" | "gold" | "up" | "down"; title?: string }) {
  const cls = { neutral: "border-rule-control text-ink-2", gold: "border-gold-dim/60 text-gold", up: "border-up/40 text-up", down: "border-down/40 text-down" }[tone];
  return <span title={title} className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[12px]", cls)}>{children}</span>;
}

export function Delta({ value }: { value: number }) {
  if (!value) return <span className="figure text-[12px] text-ink-3">±0</span>;
  return <span className={cn("figure text-[12px] font-medium", value > 0 ? "text-up" : "text-down")}>{value > 0 ? `+${value}` : value}</span>;
}

/** Tracked-caps tabs with a 1px gold underline; roving focus with arrow keys, Home/End. */
export function LedgerTabs<T extends string>({
  value, tabs, onChange, label,
}: { value: T; tabs: { value: T; label: string; badge?: ReactNode }[]; onChange: (v: T) => void; label: string }) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent, i: number) => {
    const n = tabs.length;
    const next = e.key === "ArrowRight" ? (i + 1) % n : e.key === "ArrowLeft" ? (i - 1 + n) % n : e.key === "Home" ? 0 : e.key === "End" ? n - 1 : -1;
    if (next < 0) return;
    e.preventDefault();
    onChange(tabs[next].value);
    refs.current[next]?.focus();
  };
  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-2">
      {tabs.map((t, i) => (
        <button
          key={t.value}
          ref={(el) => { refs.current[i] = el; }}
          role="tab"
          id={`tab-${t.value}`}
          aria-selected={value === t.value}
          aria-controls={`panel-${t.value}`}
          tabIndex={value === t.value ? 0 : -1}
          onClick={() => onChange(t.value)}
          onKeyDown={(e) => onKey(e, i)}
          className={cn(PILL, "flex shrink-0 items-center gap-2", value === t.value ? PILL_ON : PILL_OFF)}
        >
          {t.label}
          {t.badge}
        </button>
      ))}
    </div>
  );
}
