import type { ReportMeta } from "@/lib/types";
import { buttonClass, primaryButtonClass } from "./ui";

export function Header({ meta, csvHref, pdfHref }: { meta: ReportMeta; csvHref: string; pdfHref: string }) {
  return (
    <header className="bg-card border-b border-line">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-3.5 flex flex-wrap items-center gap-x-6 gap-y-4">
        <div className="flex items-center gap-2.5">
          <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">
            <rect x="1" y="1" width="30" height="30" rx="8" fill="none" stroke="#0F6B63" strokeWidth="2" />
            <path d="M7 19c3-4 6-4 9 0s6 4 9 0" fill="none" stroke="#0F6B63" strokeWidth="2" strokeLinecap="round" />
            <path d="M7 13c3-4 6-4 9 0s6 4 9 0" fill="none" stroke="#0F6B63" strokeWidth="2" strokeLinecap="round" opacity="0.45" />
          </svg>
          <div className="flex flex-col">
            <span className="font-semibold text-[17px] tracking-[-0.01em]">BioTrace</span>
            <span className="text-xs text-muted">Verifikasi klaim eDNA ikan air tawar</span>
          </div>
        </div>
        <div className="flex-[1_1_260px] flex flex-wrap gap-x-5 gap-y-1.5 text-[13px] text-muted">
          <span>
            Proyek: <strong className="text-ink font-medium">{meta.proyek}</strong>
          </span>
          <span>
            Referensi:{" "}
            <strong className="text-ink font-medium">
              {meta.referensi.nama} {meta.referensi.wilayah} {meta.referensi.versi}
            </strong>
          </span>
          <span>
            Aturan: <strong className="text-ink font-medium">v{meta.aturan.versi}</strong>
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled
            title="Mode statis: unggah data lewat aplikasi Streamlit atau baris perintah"
            className={`${buttonClass} disabled:opacity-55 disabled:cursor-not-allowed disabled:hover:bg-card`}
          >
            Unggah data
          </button>
          <a className={buttonClass} href={csvHref} download>
            Ekspor CSV
          </a>
          <a className={primaryButtonClass} href={pdfHref} download>
            Ekspor PDF
          </a>
        </div>
      </div>
    </header>
  );
}
