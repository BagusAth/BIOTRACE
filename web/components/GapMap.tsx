import type { GapGenus, GapGroup } from "@/lib/types";
import { formatFraction } from "@/lib/format";
import { SciName } from "./SciText";
import { SectionTitle } from "./ui";

export function GapMap({
  title,
  region,
  groups,
  perGenus,
  source,
}: {
  title: string;
  region: string;
  groups: GapGroup[];
  perGenus: GapGenus[];
  source: string;
}) {
  const regionRows = perGenus.filter((g) => g.wilayah === region);
  return (
    <section
      aria-labelledby="celah"
      className="flex-[1_1_420px] min-w-0 bg-card border border-line rounded-[12px] p-5 sm:p-6 flex flex-col gap-4"
    >
      <div>
        <SectionTitle id="celah">Peta celah kamus · {region}</SectionTitle>
        <p className="mt-1.5 mb-0 text-[22px] leading-[1.3] font-medium tracking-[-0.01em]">{title}</p>
      </div>
      <div className="flex flex-col gap-4">
        {groups.map((g) => {
          const endemic = g.label.toLowerCase().includes("endemik");
          const strong = endemic ? "#B45309" : "#0F6B63";
          const light = endemic ? "#F3D2AE" : "#A9D3CC";
          const pct = (n: number) => (g.total ? (n / g.total) * 100 : 0);
          return (
            <div key={g.label} className="flex flex-col gap-1.5">
              <div className="flex justify-between gap-3 text-sm">
                <span>
                  <strong className="font-semibold">{g.label}</strong> <span className="text-muted">· {g.petunjuk}</span>
                </span>
                <span className="font-mono whitespace-nowrap" title="ada sekuens 12S / total; tervalidasi">
                  {g.ada_sekuens}/{g.total} · {g.tervalidasi} tervalidasi
                </span>
              </div>
              <div className="relative h-2.5 rounded-[5px] bg-line-soft">
                <div className="absolute inset-y-0 left-0 rounded-[5px]" style={{ width: `${Math.max(pct(g.ada_sekuens), 1)}%`, background: light }} />
                <div className="absolute inset-y-0 left-0 rounded-[5px]" style={{ width: `${pct(g.tervalidasi)}%`, background: strong }} />
              </div>
            </div>
          );
        })}
      </div>
      <p className="m-0 text-xs text-muted">Batang muda: ada sekuens 12S. Batang tua: sekuens tervalidasi (punya specimen voucher).</p>
      {regionRows.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer font-medium">Rincian per genus ({regionRows.length})</summary>
          <div className="mt-2 flex flex-col">
            {regionRows.map((g) => (
              <div key={g.genus} className="grid grid-cols-[minmax(0,1fr)_auto_auto] gap-3 py-1.5 border-b border-line-soft">
                <SciName name={g.genus} />
                <span className="font-mono text-muted">
                  {g.r}/{g.n} tervalidasi
                </span>
                <span className="font-mono">P {formatFraction(g.p)}</span>
              </div>
            ))}
          </div>
        </details>
      )}
      <p className="m-0 text-[13px] text-muted">Sumber: {source}</p>
    </section>
  );
}
