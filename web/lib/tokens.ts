import type { Decision } from "./types";

// Warna per keputusan dan nilai, sama dengan mockup (tinta, latar, garis).
export const DECISION_STYLE: Record<Decision, { label: string; short: string; ink: string; bg: string; line: string }> = {
  "aman dilaporkan": { label: "Aman dilaporkan", short: "Aman", ink: "#0F5E57", bg: "#E3F1EE", line: "#A9D3CC" },
  "dengan catatan": { label: "Dengan catatan", short: "Catatan", ink: "#3F4B5C", bg: "#ECEFF3", line: "#C7CED8" },
  "wajib verifikasi": { label: "Wajib verifikasi", short: "Verifikasi", ink: "#8A4100", bg: "#FCEBD9", line: "#F0C18F" },
  "jangan dipakai": { label: "Jangan dipakai", short: "Jangan dipakai", ink: "#8E1B3A", bg: "#F8E4EA", line: "#E7AFC0" },
};

export const GRADE_STYLE: Record<string, { ink: string; bg: string }> = {
  A: { ink: "#0F5E57", bg: "#E3F1EE" },
  B: { ink: "#0F5E57", bg: "#E3F1EE" },
  C: { ink: "#8A4100", bg: "#FCEBD9" },
  D: { ink: "#8E1B3A", bg: "#F8E4EA" },
};

export const NEUTRAL_STYLE = { ink: "#3F4B5C", bg: "#ECEFF3", line: "#C7CED8" };

export function decisionStyle(decision: string) {
  return DECISION_STYLE[decision as Decision] ?? { label: decision, short: decision, ...NEUTRAL_STYLE };
}
