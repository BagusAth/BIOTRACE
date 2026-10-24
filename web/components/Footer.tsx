import { shortHash } from "@/lib/format";
import type { ReportMeta } from "@/lib/types";

export function Footer({ meta, manifestHref }: { meta: ReportMeta; manifestHref: string }) {
  const ref = meta.referensi;
  return (
    <footer className="flex flex-wrap justify-between gap-x-6 gap-y-2 pt-4 border-t border-line text-xs text-muted">
      <span className="font-mono">
        Referensi {ref.nama} {ref.versi} · {ref.wilayah} · Aturan v{meta.aturan.versi} · {meta.aplikasi}
      </span>
      <a className="font-mono !text-muted" href={manifestHref} title={meta.sidik_jari} download>
        Sidik jari laporan {shortHash(meta.sidik_jari)}
      </a>
    </footer>
  );
}
