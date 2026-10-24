"use client";

import { visibleClaims } from "@/lib/state";
import type { Report } from "@/lib/types";
import { useDashboardState } from "@/lib/useDashboardState";
import { AuditTrail } from "./AuditTrail";
import { BarcodePriority } from "./BarcodePriority";
import { CauseBars } from "./CauseBars";
import { ClaimTable } from "./ClaimTable";
import { DecisionSummary } from "./DecisionSummary";
import { EvidenceCard } from "./EvidenceCard";
import { Footer } from "./Footer";
import { GapMap } from "./GapMap";
import { Header } from "./Header";
import { ReportTitle } from "./ReportTitle";
import { ScientificNames } from "./SciText";
import { SimulationBanner } from "./SimulationBanner";

/** Dashboard satu halaman. Semua angka berasal dari report (kontrak biotrace.report.v1). */
export default function Dashboard({ report, dataBase }: { report: Report; dataBase: string }) {
  const [state, update] = useDashboardState(report);
  const { meta } = report;
  const claims = visibleClaims(report, state.filter);
  const selected = report.klaim.find((c) => c.id === state.selected) ?? report.klaim[0];
  const href = (file: string) => `${dataBase}/${file}`;
  const area = meta.judul.split(",")[0];

  return (
    <ScientificNames names={report.nama_ilmiah}>
      <div className="min-h-full bg-page text-ink">
        <Header meta={meta} csvHref={href(report.ekspor.csv)} pdfHref={href(report.ekspor.pdf)} />
        <main className="max-w-[1280px] mx-auto px-4 sm:px-6 pt-6 pb-14 flex flex-col gap-6">
          {meta.simulasi && <SimulationBanner area={area} />}
          <ReportTitle meta={meta} />
          <DecisionSummary summary={report.ringkasan} filter={state.filter} onFilter={(filter) => update({ filter })} />

          <div className="flex flex-wrap gap-6">
            <CauseBars causes={report.penyebab} />
            <AuditTrail files={report.berkas} missing={report.informasi_hilang} />
          </div>

          <div className="flex flex-wrap gap-6 items-start">
            <ClaimTable
              claims={claims}
              summary={report.ringkasan}
              filter={state.filter}
              selected={selected?.id ?? ""}
              region={meta.referensi.wilayah}
              onFilter={(filter) => update({ filter })}
              onSelect={(id) => update({ selected: id })}
            />
            {selected && (
              <EvidenceCard
                claim={selected}
                card={report.kartu[selected.id]}
                lang={state.lang}
                simulation={meta.simulasi}
                limit={meta.batas_interpretasi}
                onLang={(lang) => update({ lang })}
              />
            )}
          </div>

          <div className="flex flex-wrap gap-6">
            <GapMap
              title={report.celah.judul}
              region={meta.referensi.wilayah}
              groups={report.celah.kelompok}
              perGenus={report.celah.per_genus}
              source={report.celah.sumber}
            />
            <BarcodePriority items={report.prioritas_barcode} csvHref={href(report.ekspor.barcode)} />
          </div>

          <Footer meta={meta} manifestHref={href(report.ekspor.manifest)} />
        </main>
      </div>
    </ScientificNames>
  );
}
