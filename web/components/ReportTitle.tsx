import { formatProcessed } from "@/lib/format";
import type { ReportMeta } from "@/lib/types";
import { Chip } from "./ui";

export function ReportTitle({ meta }: { meta: ReportMeta }) {
  return (
    <section className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div>
        <div className="text-[13px] text-muted tracking-[0.02em]">Laporan verifikasi eDNA</div>
        <h1 className="mt-1 mb-0 text-[26px] sm:text-[32px] leading-[1.15] font-semibold tracking-[-0.02em]">
          {meta.judul.split(", ").map((part, i) => (
            <span key={part}>
              {i > 0 && ", "}
              <span className="whitespace-nowrap">{part}</span>
            </span>
          ))}
        </h1>
      </div>
      <div className="flex flex-wrap gap-2 text-[13px]">
        {meta.marker.length > 0 && <Chip>Marker {meta.marker.join(", ")}</Chip>}
        <Chip>
          {meta.jumlah_stasiun} stasiun × {meta.replikat_per_stasiun} replikat
        </Chip>
        <Chip>
          {meta.jumlah_klaim} klaim dari {meta.jumlah_asv} ASV
        </Chip>
        <Chip>Diproses {formatProcessed(meta.diproses)}</Chip>
      </div>
    </section>
  );
}
