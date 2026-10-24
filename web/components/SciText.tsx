"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

// Nama ilmiah ditulis miring (NFR PRD). Daftar nama datang dari report.nama_ilmiah;
// regex dibangun sekali per laporan, nama terpanjang dicocokkan lebih dulu.
const NamesContext = createContext<RegExp | null>(null);

function escapeRegExp(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function buildNamePattern(names: string[]): RegExp | null {
  const sorted = [...new Set(names)].filter(Boolean).sort((a, b) => b.length - a.length);
  if (!sorted.length) return null;
  return new RegExp(`(?<![\\p{L}])(${sorted.map(escapeRegExp).join("|")})(?![\\p{L}])`, "gu");
}

export function ScientificNames({ names, children }: { names: string[]; children: ReactNode }) {
  const pattern = useMemo(() => buildNamePattern(names), [names]);
  return <NamesContext.Provider value={pattern}>{children}</NamesContext.Provider>;
}

export function italicizeNames(text: string, pattern: RegExp | null): ReactNode[] {
  if (!pattern || !text) return [text];
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(pattern)) {
    const start = m.index ?? 0;
    if (start > last) out.push(text.slice(last, start));
    out.push(<i key={start}>{m[0]}</i>);
    last = start + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/** Teks bebas (alasan, tindak lanjut) dengan nama ilmiah dimiringkan. */
export function SciText({ text }: { text: string }) {
  const pattern = useContext(NamesContext);
  return <>{italicizeNames(text, pattern)}</>;
}

/** Satu nama takson: miring bila nama ilmiah (huruf kapital di depan), tegak bila bukan. */
export function SciName({ name, className = "" }: { name: string; className?: string }) {
  const scientific = /^[A-Z]/.test(name) && !name.startsWith("ASV");
  return <span className={`${scientific ? "italic" : ""} ${className}`.trim()}>{name}</span>;
}
