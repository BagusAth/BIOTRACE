import { DECISIONS, type Decision, type Lang, type Report } from "./types";

// State interaksi dashboard. Disimpan di parameter URL agar tampilan bisa dibagikan:
// ?keputusan=wajib+verifikasi&klaim=asv07@MTN-ST2&bahasa=en
export type Filter = Decision | "semua";

export interface DashboardState {
  filter: Filter;
  selected: string;
  lang: Lang;
}

export function defaultState(report: Report): DashboardState {
  const firstToVerify = report.klaim.find((c) => c.keputusan === "wajib verifikasi");
  return { filter: "semua", selected: (firstToVerify ?? report.klaim[0])?.id ?? "", lang: "id" };
}

/** Baca state dari query string; nilai yang tidak dikenal diabaikan. */
export function parseState(search: string, report: Report): DashboardState {
  const base = defaultState(report);
  const params = new URLSearchParams(search);
  const filter = params.get("keputusan");
  const selected = params.get("klaim");
  const lang = params.get("bahasa");
  return {
    filter: filter && (DECISIONS as readonly string[]).includes(filter) ? (filter as Decision) : base.filter,
    selected: selected && selected in report.kartu ? selected : base.selected,
    lang: lang === "en" ? "en" : base.lang,
  };
}

/** Tulis hanya nilai yang berbeda dari bawaan supaya URL tetap pendek. */
export function serializeState(state: DashboardState, report: Report): string {
  const base = defaultState(report);
  const params = new URLSearchParams();
  if (state.filter !== base.filter) params.set("keputusan", state.filter);
  if (state.selected !== base.selected) params.set("klaim", state.selected);
  if (state.lang !== base.lang) params.set("bahasa", state.lang);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function visibleClaims(report: Report, filter: Filter) {
  return report.klaim.filter((c) => filter === "semua" || c.keputusan === filter);
}
