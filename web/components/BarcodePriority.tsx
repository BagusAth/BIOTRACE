"use client";

import { useState } from "react";
import { capitalize } from "@/lib/format";
import type { PriorityItem } from "@/lib/types";
import { SciName } from "./SciText";
import { SectionNote, SectionTitle, buttonClass } from "./ui";

const INITIAL = 6;

export function BarcodePriority({ items, csvHref }: { items: PriorityItem[]; csvHref: string }) {
  const [all, setAll] = useState(false);
  const shown = all ? items : items.slice(0, INITIAL);
  return (
    <section
      aria-labelledby="prioritas"
      className="flex-[1_1_420px] min-w-0 bg-card border border-line rounded-[12px] p-5 sm:p-6 flex flex-col gap-4"
    >
      <div>
        <SectionTitle id="prioritas">Daftar prioritas barcode</SectionTitle>
        <SectionNote>Diurutkan dari jumlah klaim terdampak; spesies endemik lebih dulu bila sama.</SectionNote>
      </div>
      <ol className="m-0 p-0 list-none flex flex-col">
        {shown.map((q) => (
          <li
            key={`${q.urutan}-${q.target}`}
            className="grid grid-cols-[28px_minmax(0,1fr)_auto] gap-3 items-center py-3 border-b border-line-soft"
          >
            <span className="font-mono text-[13px] text-muted">{q.urutan}</span>
            <span className="flex flex-col">
              <SciName name={q.target} className="font-medium" />
              <span className="text-xs text-muted">
                {capitalize(q.jenis)}
                {q.status_L3 ? ` · ${q.status_L3}` : ""} · {q.danau}
              </span>
            </span>
            <span className="text-[13px] whitespace-nowrap">{q.klaim} klaim</span>
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-2">
        {items.length > INITIAL && (
          <button type="button" className={buttonClass} onClick={() => setAll(!all)} aria-expanded={all}>
            {all ? "Tampilkan lebih sedikit" : `Tampilkan semua (${items.length})`}
          </button>
        )}
        <a className={buttonClass} href={csvHref} download>
          Unduh daftar (CSV)
        </a>
      </div>
    </section>
  );
}
