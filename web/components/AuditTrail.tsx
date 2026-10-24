import { shortHash } from "@/lib/format";
import type { InputFile, MissingInfo } from "@/lib/types";
import { Card, SectionNote, SectionTitle } from "./ui";

export function AuditTrail({ files, missing }: { files: InputFile[]; missing: MissingInfo[] }) {
  const serious = missing.some((m) => m.tingkat === "galat" || m.tingkat === "peringatan");
  const tone = serious ? "bg-warn-bg text-warn-ink" : "bg-[#ECEFF3] text-[#3F4B5C]";
  return (
    <Card className="flex-[1_1_380px]" aria-labelledby="jejak">
      <div>
        <SectionTitle id="jejak">Data masuk dan jejak audit</SectionTitle>
        <SectionNote>Sidik jari SHA-256 setiap berkas; input yang sama selalu menghasilkan laporan yang sama.</SectionNote>
      </div>
      <div className="flex flex-col">
        {files.map((f) => (
          <div
            key={f.nama}
            className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 py-2.5 border-b border-line-soft"
          >
            <span className="flex items-center gap-2 text-sm">
              <svg width="16" height="16" viewBox="0 0 16 16" role="img" aria-label="Terbaca">
                <circle cx="8" cy="8" r="7" fill="none" stroke="#0F6B63" strokeWidth="1.5" />
                <path d="M5 8.2l2 2 4-4.2" fill="none" stroke="#0F6B63" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <strong className="font-medium">{f.nama}</strong>
              <span className="text-muted">{f.deskripsi}</span>
            </span>
            <span className="font-mono text-xs text-muted" title={`sha256:${f.sha256}`}>
              sha256 {shortHash(f.sha256)}
            </span>
          </div>
        ))}
      </div>
      {missing.length > 0 && (
        <div className={`flex gap-2.5 px-3.5 py-3 rounded-lg text-sm ${tone}`}>
          <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" className="flex-none mt-px">
            <path d="M9 2l7.5 13h-15z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M9 7v4M9 13.2v.1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
          <div className="flex flex-col gap-1">
            <strong className="font-semibold">
              {missing.length} informasi yang hilang. Proses tetap berjalan.
            </strong>
            <ul className="m-0 pl-4 flex flex-col gap-0.5">
              {missing.map((m) => (
                <li key={`${m.berkas}-${m.masalah}`}>
                  {m.masalah}
                  {m.dampak ? ` — ${m.dampak}` : ""}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </Card>
  );
}
