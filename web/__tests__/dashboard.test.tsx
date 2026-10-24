import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import demo from "../public/demo/report.json";
import Dashboard from "@/components/Dashboard";
import { buildNamePattern, italicizeNames } from "@/components/SciText";
import type { Report } from "@/lib/types";

const report: Report = demo;

function renderDashboard() {
  return render(<Dashboard report={report} dataBase="/demo" />);
}

const card = () => screen.getByRole("complementary");
const rows = () => document.querySelectorAll("[data-claim]");
const summarySection = () => screen.getByRole("region", { name: /ringkasan keputusan/i });

beforeEach(() => window.history.replaceState(null, "", "/"));
afterEach(cleanup);

describe("Dashboard", () => {
  it("menampilkan ringkasan dari report.json dan label SIMULASI", () => {
    renderDashboard();
    expect(screen.getByText(report.ringkasan.kalimat)).toBeTruthy();
    expect(screen.getByRole("note").textContent).toContain("SIMULASI");
    expect(rows()).toHaveLength(report.klaim.length);
  });

  it("kartu keputusan menampilkan jumlah yang sama dengan ringkasan", () => {
    renderDashboard();
    const tile = within(summarySection()).getByRole("button", { name: /wajib verifikasi/i });
    expect(tile.textContent).toContain(String(report.ringkasan.jumlah["wajib verifikasi"]));
  });

  it("kartu penyaring menyaring tabel dan menulis URL", () => {
    renderDashboard();
    const tile = within(summarySection()).getByRole("button", { name: /wajib verifikasi/i });
    fireEvent.click(tile);
    expect(tile.getAttribute("aria-pressed")).toBe("true");
    expect(rows()).toHaveLength(report.ringkasan.jumlah["wajib verifikasi"]);
    expect(window.location.search).toBe("?keputusan=wajib+verifikasi");
    fireEvent.click(tile); // klik lagi = kembali ke semua
    expect(rows()).toHaveLength(report.klaim.length);
  });

  it("memilih baris mengganti Evidence Card", () => {
    renderDashboard();
    fireEvent.click(document.querySelector('[data-claim="asv10@MTN-ST2"]')!);
    expect(within(card()).getByText("Anguilla marmorata", { selector: "span.text-\\[26px\\]" })).toBeTruthy();
    expect(card().textContent).toContain("Batas D diterapkan");
    expect(card().textContent).toContain(report.meta.batas_interpretasi.id);
  });

  it("tombol EN mengganti teks alasan ke Bahasa Inggris", () => {
    renderDashboard();
    const selected = report.kartu[report.klaim.find((c) => c.keputusan === "wajib verifikasi")!.id];
    const l1 = () => card().querySelector('[data-layer="L1"]')!.textContent!;
    expect(l1()).toContain(selected.alasan[1].id.slice(0, 20));
    fireEvent.click(within(card()).getByRole("button", { name: "EN" }));
    expect(l1()).toContain(selected.alasan[1].en.slice(0, 20));
    expect(window.location.search).toContain("bahasa=en");
  });

  it("memulihkan state dari URL yang dibagikan", () => {
    window.history.replaceState(null, "", "/?keputusan=jangan+dipakai&klaim=asv10%40MTN-ST2&bahasa=en");
    renderDashboard();
    act(() => {}); // biarkan useSyncExternalStore membaca URL
    expect(rows()).toHaveLength(1);
    expect(within(card()).getByRole("button", { name: "EN" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("tautan ekspor menunjuk berkas demo", () => {
    renderDashboard();
    expect(screen.getByRole("link", { name: "Ekspor CSV" }).getAttribute("href")).toBe(`/demo/${report.ekspor.csv}`);
    expect(screen.getByRole("link", { name: "Ekspor PDF" }).getAttribute("href")).toBe(`/demo/${report.ekspor.pdf}`);
  });
});

describe("nama ilmiah", () => {
  it("memiringkan nama terpanjang lebih dulu", () => {
    const pattern = buildNamePattern(["Oreochromis", "Oreochromis niloticus"]);
    const { container } = render(<p>{italicizeNames("Kemiripan 100% dengan Oreochromis niloticus.", pattern)}</p>);
    expect([...container.querySelectorAll("i")].map((i) => i.textContent)).toEqual(["Oreochromis niloticus"]);
  });
});
