import { capitalize, formatFraction } from "@/lib/format";
import type { Filter } from "@/lib/state";
import { DECISION_STYLE } from "@/lib/tokens";
import { DECISIONS, type Claim, type Summary } from "@/lib/types";
import { SciName } from "./SciText";
import { DecisionBadge, GradeBadge, SectionTitle } from "./ui";

const GRID = "grid grid-cols-[0.8fr_1.35fr_1.35fr_0.45fr_0.95fr_0.65fr_1.25fr_1.2fr] gap-2.5";

export function ClaimTable({
  claims,
  summary,
  filter,
  selected,
  region,
  onFilter,
  onSelect,
}: {
  claims: Claim[];
  summary: Summary;
  filter: Filter;
  selected: string;
  region: string;
  onFilter: (f: Filter) => void;
  onSelect: (id: string) => void;
}) {
  const pills: [Filter, string][] = [
    ["semua", `Semua ${summary.jumlah.n}`],
    ...DECISIONS.map((d): [Filter, string] => [d, `${DECISION_STYLE[d].short} ${summary.jumlah[d]}`]),
  ];
  return (
    <section
      aria-labelledby="tabel-klaim"
      className="flex-[999_1_640px] min-w-0 bg-card border border-line rounded-[12px] p-5 sm:p-6 flex flex-col gap-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTitle id="tabel-klaim">Tabel klaim</SectionTitle>
        <div role="group" aria-label="Saring keputusan" className="flex flex-wrap gap-1.5">
          {pills.map(([f, label]) => {
            const on = filter === f;
            return (
              <button
                key={f}
                type="button"
                aria-pressed={on}
                onClick={() => onFilter(f)}
                className={`min-h-9 px-3 rounded-full text-[13px] cursor-pointer border ${
                  on ? "font-semibold text-white bg-ink border-ink" : "font-medium text-ink bg-card border-line-strong"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>
      <div className="overflow-x-auto border border-line-soft rounded-lg">
        <div className="min-w-[760px]">
          <div className={`${GRID} px-3.5 py-2.5 bg-page text-xs font-semibold text-muted`}>
            {["Klaim", "Nama dari lab", "Dilaporkan sebagai", "Nilai", "Penyebab", "Belum di kamus", "Status L3", "Keputusan"].map(
              (h) => (
                <span key={h}>
                  {h}
                </span>
              ),
            )}
          </div>
          {claims.length === 0 && <p className="m-0 px-3.5 py-4 text-sm text-muted">Tidak ada klaim dengan keputusan ini.</p>}
          {claims.map((c) => {
            const on = c.id === selected;
            const unknown = c.tingkat === "tidak dikenal";
            return (
              <button
                key={c.id}
                type="button"
                aria-pressed={on}
                data-claim={c.id}
                onClick={() => onSelect(c.id)}
                className={`${GRID} w-full items-center min-h-[52px] px-3.5 py-2 text-left text-sm text-ink cursor-pointer border-0 border-b border-line-soft`}
                style={{ boxShadow: on ? "inset 3px 0 0 #0F6B63" : "none", background: on ? "#EEF6F4" : "#FFFFFF" }}
              >
                <span className="font-mono text-[13px] flex flex-col">
                  <span>{c.asv}</span>
                  <span className="text-xs text-muted">{c.stasiun}</span>
                </span>
                <span>{c.nama_lab ? <SciName name={c.nama_lab} /> : "—"}</span>
                <span className="flex flex-col">
                  {unknown ? <span className="font-medium">Tidak dikenal</span> : <SciName name={c.dilaporkan} className="font-medium" />}
                  <span className="text-xs text-muted">{capitalize(c.tingkat)}</span>
                </span>
                <span>
                  <GradeBadge grade={c.nilai} />
                </span>
                <span className="text-[13px]">
                  {c.penyebab.length ? c.penyebab.map(capitalize).join(", ") : "—"}
                </span>
                <span className="font-mono text-[13px]">
                  {formatFraction(c.peluang_belum_di_kamus)}
                </span>
                <span className="text-[13px]">
                  {c.label_L3.length ? capitalize(c.label_L3.join(", ")) : "—"}
                </span>
                <span>
                  <DecisionBadge decision={c.keputusan} />
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <p className="m-0 text-[13px] text-muted">
        Belum di kamus = proporsi kerabat satu genus di {region} yang belum punya referensi 12S tervalidasi.
      </p>
    </section>
  );
}
