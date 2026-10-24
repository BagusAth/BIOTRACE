import type { CauseCount } from "@/lib/types";
import { Bar, Card, SectionNote, SectionTitle } from "./ui";

export function CauseBars({ causes }: { causes: CauseCount[] }) {
  const max = Math.max(1, ...causes.map((c) => c.jumlah));
  return (
    <Card className="flex-[1_1_380px]" aria-labelledby="penyebab">
      <div>
        <SectionTitle id="penyebab">Penyebab ketidakpastian</SectionTitle>
        <SectionNote>Jumlah klaim per penyebab; satu klaim bisa punya lebih dari satu penyebab.</SectionNote>
      </div>
      <div className="flex flex-col gap-3.5">
        {causes.map((c) => (
          <div key={c.kode} className="flex flex-col gap-1.5">
            <div className="flex justify-between gap-3 text-sm">
              <span>
                <strong className="font-semibold">{c.label}</strong> <span className="text-muted">· {c.petunjuk}</span>
              </span>
              <span className="font-mono">{c.jumlah}</span>
            </div>
            <Bar percent={Math.round((c.jumlah / max) * 100)} color={c.kode === "referensi" ? "#B45309" : "#5B6B7F"} />
          </div>
        ))}
      </div>
    </Card>
  );
}
