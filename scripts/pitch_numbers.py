"""Tahap 7: kumpulkan angka yang harus siap untuk pitch ke docs/angka_pitch.md.

Setiap angka membawa sumber berkasnya. Label di slide: data demo sintetis; angka simulasi
diberi keterangan referensi yang dipakai.

    python scripts/pitch_numbers.py            # termasuk uji kinerja 200 sampel x 2.000 ASV
    python scripts/pitch_numbers.py --no-benchmark
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import ROOT  # noqa: E402
from biotrace.pipeline import run  # noqa: E402
from biotrace.taxonomy import genus_of  # noqa: E402

REF = ROOT / "data" / "ref" / "v0.1"
RES = ROOT / "data" / "test" / "results"
DEMO = ROOT / "data" / "demo" / "matano"
OUT = ROOT / "docs" / "angka_pitch.md"


def metric(results: pd.DataFrame, uji: str, referensi_prefix: str, aturan_prefix: str, name: str):
    r = results[(results["uji"] == uji) & results["referensi"].str.startswith(referensi_prefix) &
                results["aturan"].str.startswith(aturan_prefix) & (results["metrik"] == name)]
    return None if r.empty or pd.isna(r["nilai"].iloc[0]) else float(r["nilai"].iloc[0])


def dec(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def pct(x) -> str:
    return "-" if x is None else f"{x:.1f}%".replace(".", ",")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-benchmark", action="store_true")
    args = ap.parse_args()

    cov = pd.read_csv(REF / "kelengkapan_spesies.csv")
    endemic = cov[cov["status_di_malili"] == "endemik"]
    tel = endemic[endemic["spesies"].map(genus_of).isin(["Telmatherina", "Paratherina", "Tominanga"])]
    n_end, n_end_ref = len(endemic), int((endemic["ada_referensi"] == "ya").sum())
    n_end_val = int((endemic["ada_referensi_tervalidasi"] == "ya").sum())
    n_tel, n_tel_noref = len(tel), int((tel["ada_referensi"] == "tidak").sum())

    res = pd.read_csv(RES / "results_v0.1.csv", dtype={"uji": str, "referensi": str, "aturan": str, "metrik": str})
    malili97 = metric(res, "6.1", "kandidat Malili v0.1 (", "penuh", "ambang97_nama_keliru_lolos_pct")
    malili_bt = metric(res, "6.1", "kandidat Malili v0.1 (", "penuh", "biotrace_nama_keliru_lolos_pct")
    malili_logic = metric(res, "6.1", "kandidat Malili v0.1 (", "logika", "biotrace_nama_keliru_lolos_pct")
    imf97 = metric(res, "6.1", "I-MarFish", "logika", "ambang97_nama_keliru_lolos_pct")
    imf_bt = metric(res, "6.1", "I-MarFish", "logika", "biotrace_nama_keliru_lolos_pct")
    lsp_drop = metric(res, "6.2", "Kanada", "penuh", "biotrace_turun_genus_atau_tidak_dikenal_pct")
    lsp97 = metric(res, "6.2", "Kanada", "penuh", "ambang97_nama_keliru_lolos_pct")
    lsp = json.loads((RES / "lake_st_pierre.json").read_text(encoding="utf-8"))
    ef = lsp["electrofishing"]

    demo = run(DEMO / "bacaan.csv", DEMO / "metadata.csv", DEMO / "taksonomi.csv", DEMO / "asv.fasta")
    timing = f"{dec(demo.seconds)} detik (skenario Matano, {len(demo.claims)} klaim)"
    if not args.no_benchmark:
        sys.path.insert(0, str(ROOT / "scripts"))
        from benchmark import benchmark
        b = benchmark(200, 2000)
        n_claims = f"{len(b.claims):,}".replace(",", ".")
        timing = f"{dec(b.seconds)} detik untuk 200 sampel x 2.000 ASV ({n_claims} klaim, termasuk BLAST); " + timing
    s = demo.summary

    rows = [
        (f"{n_end_ref} dari {n_end} endemik Malili punya referensi 12S; {n_tel_noref} dari {n_tel} telmatherinid tidak",
         "Audit Dataset, dibangun ulang di `data/ref/v0.1/kelengkapan_spesies.csv`", "Masalah, referensi"),
        (f"{n_end_val} dari {n_end} endemik punya 12S tervalidasi (sekuens *T. celebensis* tanpa voucher)",
         "`data/ref/v0.1/ref12S_taksonomi.csv` (GenBank specimen_voucher)", "Masalah, referensi"),
        (f"Nama keliru lolos, kandidat Malili: ambang 97% {pct(malili97)} vs aturan BioTrace {pct(malili_bt)} "
         f"(logika tanpa syarat voucher {pct(malili_logic)})",
         "Tahap 6.1, `data/test/results/results_v0.1.csv`, referensi kandidat Malili v0.1", "Bukti"),
        (f"Nama keliru lolos, I-MarFish (ikan laut): ambang 97% {pct(imf97)} vs BioTrace {pct(imf_bt)}",
         "Tahap 6.1, I-MarFish LocalDB (DBP UNDIP)", "Bukti"),
        (f"Spesies terhapus yang tidak diberi nama lain: {pct(lsp_drop)} (ambang 97% memberi nama keliru {pct(lsp97)})",
         "Tahap 6.2, referensi Kanada untuk Lake St. Pierre", "Bukti"),
        ("Presisi A-B vs electrofishing: tidak bisa dihitung (1 replikat per lokasi, tanpa kontrol); "
         f"pelengkap {ef['cocok_electrofishing_semua_nilai']} dari {ef['klaim_spesies_semua_nilai']} klaim spesies "
         f"({pct(ef['presisi_spesies_semua_nilai_pct'])}) cocok, batas bawah",
         "Tahap 6.2, `data/test/results/lake_st_pierre.json`", "Bukti"),
        (f"Waktu unggah sampai ringkasan: {timing}", "Log aplikasi (`Report.seconds`), `scripts/benchmark.py`", "Demo"),
        (f"Skenario Matano (SIMULASI): {s['n']} klaim — {s['aman dilaporkan']} aman dilaporkan, "
         f"{s['dengan catatan']} dengan catatan, {s['wajib verifikasi']} wajib verifikasi, "
         f"{s['jangan dipakai']} jangan dipakai; {s['tidak dikenal']} tidak dikenal",
         "Hasil demo, `data/demo/matano/hasil/ringkasan.json`", "Demo"),
    ]
    lines = ["# Angka untuk pitch — BioTrace Indonesia v0.1", "",
             "Dibuat oleh `scripts/pitch_numbers.py`. **Label di slide: data demo sintetis; angka simulasi "
             "diberi keterangan referensi yang dipakai.** Angka uji adalah uji logika mesin pada data publik, "
             "bukan validasi lapangan di Malili.", "",
             "| Angka | Sumber | Dipakai di slide |", "|---|---|---|"]
    lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    lines += ["", "Galat per nilai (F19, simulasi tanpa-satu-spesies ref Malili; L2/L4 diasumsikan maksimal):", ""]
    eg = pd.read_csv(RES / "galat_per_nilai.csv", dtype=str, keep_default_na=False)
    lines += [f"- Nilai {r['nilai']}: {r['galat']}" for r in eg.to_dict("records")]
    lines += ["", "`tag_jump_fraction` belum dikalibrasi: tabel Li dkk. 2019 belum ada di repo.", ""]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
