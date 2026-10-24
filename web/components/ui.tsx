import type { ReactNode } from "react";
import { GRADE_STYLE, NEUTRAL_STYLE, decisionStyle } from "@/lib/tokens";

// Potongan gaya bersama dari mockup: kartu, judul seksi, tombol, lencana.

export function Card({ children, className = "", ...rest }: { children: ReactNode; className?: string } & React.HTMLAttributes<HTMLElement>) {
  return (
    <section className={`min-w-0 bg-card border border-line rounded-[12px] p-5 sm:p-6 flex flex-col gap-4 ${className}`} {...rest}>
      {children}
    </section>
  );
}

export function SectionTitle({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <h2 id={id} className="m-0 text-[13px] font-semibold tracking-[0.06em] text-muted uppercase">
      {children}
    </h2>
  );
}

export function SectionNote({ children }: { children: ReactNode }) {
  return <p className="mt-1.5 mb-0 text-muted text-sm">{children}</p>;
}

export const buttonClass =
  "inline-flex items-center min-h-11 px-4 rounded-lg border border-line-strong bg-card !text-ink text-sm font-medium no-underline cursor-pointer hover:bg-page";

export const primaryButtonClass =
  "inline-flex items-center min-h-11 px-4 rounded-lg border border-accent bg-accent !text-white text-sm font-semibold no-underline cursor-pointer hover:bg-accent-hover";

export function DecisionBadge({ decision }: { decision: string }) {
  const s = decisionStyle(decision);
  return (
    <span
      className="inline-block px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap border"
      style={{ color: s.ink, background: s.bg, borderColor: s.line }}
    >
      {s.label}
    </span>
  );
}

export function GradeBadge({ grade }: { grade: string }) {
  const s = GRADE_STYLE[grade] ?? NEUTRAL_STYLE;
  return (
    <span
      className="inline-flex items-center justify-center min-w-[30px] h-[26px] px-1.5 rounded-md font-semibold"
      style={{ color: s.ink, background: s.bg }}
    >
      {grade}
    </span>
  );
}

export function Chip({ children }: { children: ReactNode }) {
  return <span className="px-2.5 py-1.5 rounded-full bg-card border border-line">{children}</span>;
}

export function Bar({ percent, color, background = "#EDF1F0" }: { percent: number; color: string; background?: string }) {
  return (
    <div className="h-2.5 rounded-[5px]" style={{ background }}>
      <div className="h-2.5 rounded-[5px]" style={{ width: `${Math.max(0, Math.min(100, percent))}%`, background: color }} />
    </div>
  );
}
