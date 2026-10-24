import type { Filter } from "@/lib/state";
import { DECISION_STYLE } from "@/lib/tokens";
import { DECISIONS, type Summary } from "@/lib/types";
import { SectionTitle } from "./ui";

export function DecisionSummary({
  summary,
  filter,
  onFilter,
}: {
  summary: Summary;
  filter: Filter;
  onFilter: (f: Filter) => void;
}) {
  const unknown = summary.tidak_dikenal_ke_barcode;
  return (
    <section aria-labelledby="ringkasan" className="bg-card border border-line rounded-[12px] p-5 sm:p-6 flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <SectionTitle id="ringkasan">Ringkasan keputusan</SectionTitle>
        <p className="m-0 text-2xl leading-[1.3] font-medium tracking-[-0.01em] max-w-[880px]">{summary.kalimat}</p>
        <p className="m-0 text-muted">
          {unknown > 0 ? `${unknown} urutan tidak dikenal masuk daftar prioritas barcode. ` : ""}
          Pilih kartu untuk menyaring tabel klaim.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        {DECISIONS.map((d) => {
          const s = DECISION_STYLE[d];
          const on = filter === d;
          return (
            <button
              key={d}
              type="button"
              aria-pressed={on}
              onClick={() => onFilter(on ? "semua" : d)}
              className="flex-[1_1_220px] min-h-11 text-left flex flex-col gap-2 p-4 rounded-[10px] cursor-pointer"
              style={{ color: s.ink, background: s.bg, border: on ? `2px solid ${s.ink}` : `1px solid ${s.line}` }}
            >
              <span className="flex items-baseline gap-2.5">
                <span className="text-[40px] leading-none font-semibold tracking-[-0.03em]">{summary.jumlah[d]}</span>
                <span className="text-[15px] font-semibold">{s.label}</span>
              </span>
              <span className="text-[13px] leading-[1.4] text-ink-2">{summary.tindak_lanjut[d]}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
