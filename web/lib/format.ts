const MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

/** "2026-10-24T22:39:05+07:00" -> "24 Okt 2026, 22.39" tanpa konversi zona waktu,
 *  supaya HTML hasil build dan hasil hidrasi di browser selalu sama. */
export function formatProcessed(iso: string | null): string {
  const m = iso?.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!m) return "-";
  const [, y, mo, d, h, mi] = m;
  return `${Number(d)} ${MONTHS[Number(mo) - 1]} ${y}, ${h}.${mi}`;
}

/** "sha256:10325c7c…" atau heksa polos -> "1032…dd39". */
export function shortHash(hash: string, head = 4, tail = 4): string {
  const hex = hash.replace(/^sha256:/, "");
  return hex.length > head + tail ? `${hex.slice(0, head)}…${hex.slice(-tail)}` : hex;
}

/** Peluang belum di kamus dengan koma desimal; "—" bila tidak dihitung. */
export function formatFraction(x: number | null): string {
  return x === null ? "—" : x.toFixed(2).replace(".", ",");
}

export function capitalize(text: string): string {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}

/** Klaim "asv07@MTN-ST2" ditampilkan sebagai "asv07 · MTN-ST2". */
export function claimLabel(id: string): string {
  return id.replace("@", " · ");
}
