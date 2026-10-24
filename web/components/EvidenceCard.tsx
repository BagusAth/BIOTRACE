import { capitalize, claimLabel } from "@/lib/format";
import type { Claim, EvidenceCardData, Lang, Reason } from "@/lib/types";
import { SciName, SciText } from "./SciText";
import { DecisionBadge, SectionTitle } from "./ui";

function layerLabel(r: Reason, lang: Lang) {
  if (r.lapisan === "penamaan") return lang === "id" ? "Penamaan" : "Naming";
  if (r.skor === null) return `${r.lapisan} · ${lang === "id" ? "tidak dinilai" : "not assessed"}`;
  return `${r.lapisan} · ${r.skor}/${r.maks}`;
}

function Output({ label, value, note, mono = false }: { label: string; value: string; note?: string; mono?: boolean }) {
  return (
    <div className="p-3 rounded-lg bg-page flex flex-col gap-1">
      <span className="text-xs text-muted">{label}</span>
      <strong className={`font-semibold ${mono ? "font-mono" : ""}`}>{value}</strong>
      {note && <span className="text-xs text-muted">{note}</span>}
    </div>
  );
}

export function EvidenceCard({
  claim,
  card,
  lang,
  simulation,
  limit,
  onLang,
}: {
  claim: Claim;
  card: EvidenceCardData;
  lang: Lang;
  simulation: boolean;
  limit: Record<Lang, string>;
  onLang: (l: Lang) => void;
}) {
  const unknown = claim.tingkat === "tidak dikenal";
  const out = card.keluaran;
  const toggle = (on: boolean) =>
    `min-w-11 min-h-9 px-3 border-0 text-[13px] font-semibold cursor-pointer ${on ? "text-white bg-ink" : "text-ink bg-card"}`;
  const origin = card.asal_usul;
  return (
    <aside
      aria-labelledby="evidence"
      className="flex-[1_1_380px] min-w-0 bg-card border border-line rounded-[12px] p-5 sm:p-6 flex flex-col gap-[18px]"
    >
      <div className="flex items-center justify-between gap-3">
        <SectionTitle id="evidence">{simulation ? "SIMULASI · Evidence Card" : "Evidence Card"}</SectionTitle>
        <div role="group" aria-label="Bahasa alasan" className="flex border border-line-strong rounded-lg overflow-hidden">
          <button type="button" aria-pressed={lang === "id"} onClick={() => onLang("id")} className={toggle(lang === "id")}>
            ID
          </button>
          <button type="button" aria-pressed={lang === "en"} onClick={() => onLang("en")} className={toggle(lang === "en")}>
            EN
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[13px] text-muted">
          {claimLabel(claim.id)} · nama dari lab {claim.nama_lab ? <SciName name={claim.nama_lab} /> : "—"}
        </span>
        <div className="flex flex-wrap items-center gap-2.5">
          {unknown ? (
            <span className="text-[26px] leading-[1.2] font-semibold tracking-[-0.01em]">Tidak dikenal</span>
          ) : (
            <SciName name={claim.dilaporkan} className="text-[26px] leading-[1.2] font-semibold tracking-[-0.01em]" />
          )}
          <DecisionBadge decision={claim.keputusan} />
        </div>
        {claim.label_L3.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {claim.label_L3.map((l) => (
              <span key={l} className="px-2 py-0.5 rounded-full text-xs border border-line text-ink-2">
                {capitalize(l)}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <Output label="Tingkat aman dilaporkan" value={capitalize(out.tingkat)} />
        <Output label="Nilai bukti" value={`${out.nilai} · skor ${out.skor}`} note={`Galat per nilai: ${out.galat_nilai}`} />
        <Output label="Peluang belum di kamus" value={out.peluang} note={out.catatan_peluang} mono />
        <Output label="Penyebab" value={out.penyebab.length ? out.penyebab.map(capitalize).join(", ") : "Tidak ada"} />
      </div>

      {card.batas_D && (
        <div className="px-3.5 py-3 rounded-lg bg-warn-bg text-warn-ink text-sm">
          <strong className="font-semibold">Batas D diterapkan:</strong> {card.batas_D}
        </div>
      )}

      <div className="flex flex-col gap-2.5">
        <h3 className="m-0 text-sm font-semibold">{lang === "id" ? "Alasan per lapisan" : "Reasons by layer"}</h3>
        {card.alasan.map((r) => (
          <div key={r.lapisan} className="grid grid-cols-[96px_minmax(0,1fr)] gap-2.5 text-sm" data-layer={r.lapisan}>
            <span className="font-mono text-xs text-muted pt-0.5">{layerLabel(r, lang)}</span>
            <span>
              <SciText text={lang === "id" ? r.id : r.en} />
            </span>
          </div>
        ))}
      </div>

      <div className="p-3.5 rounded-lg border border-accent flex flex-col gap-1">
        <span className="text-xs font-semibold text-accent-ink">Tindak lanjut</span>
        <span className="text-sm">
          <SciText text={card.tindak_lanjut} />
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        <h3 className="m-0 text-sm font-semibold">Kemungkinan asal-usul</h3>
        {origin ? (
          [origin.status, origin.jalur, origin.sumber_dna, origin.fasilitas]
            .filter(Boolean)
            .map((t) => (
              <span key={t} className="text-sm text-ink-2">
                · <SciText text={t} />
              </span>
            ))
        ) : (
          <span className="text-sm text-muted">Tidak ada jalur masuk tercatat untuk takson ini.</span>
        )}
      </div>

      {card["kecocokan_dalam_0,5%"].length > 1 && (
        <p className="m-0 text-[13px] text-muted">
          Kecocokan dalam selisih 0,5%: <SciText text={card["kecocokan_dalam_0,5%"].join(", ")} />
        </p>
      )}

      <p className="m-0 pt-3 border-t border-line-soft text-[13px] text-muted">
        {limit.id}
        {lang === "en" && <span className="block">{limit.en}</span>}
      </p>
    </aside>
  );
}
