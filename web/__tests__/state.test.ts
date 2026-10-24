import { describe, expect, it } from "vitest";
import demo from "../public/demo/report.json";
import { formatFraction, formatProcessed, shortHash } from "@/lib/format";
import { defaultState, parseState, serializeState, visibleClaims } from "@/lib/state";
import type { Report } from "@/lib/types";

// Penugasan ini membuat `tsc --noEmit` memeriksa report.json terhadap kontrak tipe.
const report: Report = demo;

describe("kontrak data demo", () => {
  it("berskema biotrace.report.v1 dan konsisten dengan ringkasan", () => {
    expect(report.schema).toBe("biotrace.report.v1");
    expect(report.klaim).toHaveLength(report.meta.jumlah_klaim);
    const total = ["aman dilaporkan", "dengan catatan", "wajib verifikasi", "jangan dipakai"]
      .map((d) => report.klaim.filter((c) => c.keputusan === d).length)
      .reduce((a, b) => a + b, 0);
    expect(total).toBe(report.ringkasan.jumlah.n);
    for (const c of report.klaim) expect(report.kartu[c.id]).toBeDefined();
  });
});

describe("state URL", () => {
  it("bawaan memilih klaim wajib verifikasi pertama", () => {
    const s = defaultState(report);
    expect(s.filter).toBe("semua");
    expect(report.klaim.find((c) => c.id === s.selected)?.keputusan).toBe("wajib verifikasi");
  });

  it("membaca dan menulis ulang parameter yang sama", () => {
    const s = parseState("?keputusan=jangan+dipakai&klaim=asv10%40MTN-ST2&bahasa=en", report);
    expect(s).toEqual({ filter: "jangan dipakai", selected: "asv10@MTN-ST2", lang: "en" });
    expect(parseState(serializeState(s, report), report)).toEqual(s);
    expect(serializeState(defaultState(report), report)).toBe("");
  });

  it("mengabaikan nilai yang tidak dikenal", () => {
    expect(parseState("?keputusan=hapus&klaim=tidak-ada&bahasa=fr", report)).toEqual(defaultState(report));
  });

  it("menyaring klaim per keputusan", () => {
    expect(visibleClaims(report, "jangan dipakai").map((c) => c.id)).toEqual(["asv10@MTN-ST2"]);
    expect(visibleClaims(report, "semua")).toHaveLength(report.klaim.length);
  });
});

describe("format", () => {
  it("tanggal tanpa konversi zona waktu, hash pendek, pecahan berkoma", () => {
    expect(formatProcessed("2026-10-24T22:39:05+07:00")).toBe("24 Okt 2026, 22.39");
    expect(formatProcessed(null)).toBe("-");
    expect(shortHash("sha256:10325c7c8571accc4fa8af7edd2fdd586ee209eb52005db1579fe5643eb4dd39")).toBe("1032…dd39");
    expect(formatFraction(1)).toBe("1,00");
    expect(formatFraction(null)).toBe("—");
  });
});
