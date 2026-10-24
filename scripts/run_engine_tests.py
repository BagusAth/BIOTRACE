"""Tahap 6: uji mesin dan validasi.

6.1 Uji tanpa-satu-spesies (F26) pada referensi kandidat Malili dan I-MarFish:
    ambang 97% (nama teratas) vs aturan BioTrace.
6.2 Mode uji Lake St. Pierre (F27), jalur kedua karena edna_lg_clean.csv hanya berisi
    deteksi per spesies: uji tanpa-satu-spesies pada referensi Kanada, lalu tabel deteksi
    dan electrofishing untuk menguji L2, L4, dan sebaran keputusan.
6.3 Uji sinyal lab dengan Li dkk. 2019 bila tabelnya ada di data/test/li2019/.

Hasil: data/test/results/results_v0.1.csv (format panjang), tabel per kueri, galat per
nilai untuk F19, dan ringkasan Lake St. Pierre.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import RAW_DIR, ROOT, load_rules  # noqa: E402
from biotrace.pipeline import run  # noqa: E402
from biotrace.reference import load_reference, read_fasta  # noqa: E402
from biotrace.simulate import (RefRecord, all_vs_all, detection_project, error_by_grade,  # noqa: E402
                               as_amplicon, leave_one_out, precision_vs_electrofishing, summarize_loo)
from biotrace.taxonomy import species_key  # noqa: E402

OUT = ROOT / "data" / "test" / "results"
LSP = ROOT / "data" / "test" / "lake_st_pierre"
IMARFISH = RAW_DIR / "dbp" / "Curated-Metabarcoding-Database-for-Marine-Fish-in-Indonesia" / "database_local"
FOCUS_GENERA = ("Oryzias", "Channa", "Oreochromis")


def reference_records(ref) -> dict[str, RefRecord]:
    return {r["aksesi"]: RefRecord(r["aksesi"], r["spesies"], r["genus"], r["famili"],
                                   r["status_validasi"] == "tervalidasi", r["tercatat_di_indonesia"])
            for r in ref.taxonomy.to_dict("records")}


def mifish_queries(seqs: dict[str, str], records: dict[str, RefRecord],
                   species_filter: set[str] | None = None) -> tuple[dict[str, str], dict[str, str]]:
    """Amplikon MiFish per sekuens bernama spesies, satu per pasangan (spesies, urutan)."""
    queries, species, seen = {}, {}, set()
    for acc in sorted(seqs):
        rec = records.get(acc)
        if rec is None:
            continue
        key, resolved = rec.key
        if not resolved or (species_filter is not None and key not in species_filter):
            continue
        amp = as_amplicon(seqs[acc])
        if amp is None or (key, amp) in seen:
            continue
        seen.add((key, amp))
        queries[acc] = amp
        species[acc] = key
    return queries, species


def metric_rows(summary: dict, uji: str, target: dict[str, str] | None = None, note: str = "") -> list[dict]:
    target = target or {}
    rows = []
    for k, v in summary.items():
        if k in ("referensi", "aturan_biotrace"):
            continue
        rows.append({"uji": uji, "referensi": summary["referensi"], "aturan": summary.get("aturan_biotrace", ""),
                     "metrik": k, "nilai": v, "target": target.get(k, ""), "catatan": note})
    return rows


def loo_malili(rules, threads) -> tuple[list[dict], pd.DataFrame]:
    ref = load_reference()
    seqs = read_fasta(ref.root / "ref12S.fasta")
    records = reference_records(ref)
    queries, species = mifish_queries(seqs, records)
    hits = all_vs_all(queries, seqs, rules, threads)
    rows = []
    full = leave_one_out(queries, species, hits, records, rules)
    logic = leave_one_out(queries, species, hits, records, rules, logic_only=True)
    full.to_csv(OUT / "loo_malili_aturan_penuh.csv", index=False, lineterminator="\n")
    logic.to_csv(OUT / "loo_malili_logika.csv", index=False, lineterminator="\n")
    target = {"biotrace_nama_keliru_lolos_pct": "< 16"}
    note = "amplikon MiFish dari kandidat Malili v0.1; L1 tanpa potongan kelengkapan; L2=1, L4=2 diasumsikan"
    rows += metric_rows(summarize_loo(full, "kandidat Malili v0.1 (226 nama)", "penuh: validasi + tercatat"), "6.1", target, note)
    rows += metric_rows(summarize_loo(logic, "kandidat Malili v0.1 (226 nama)", "logika: semua sekuens dianggap tervalidasi"), "6.1", target, note)
    for genus in FOCUS_GENERA:
        sub = logic[logic["genus_asli"] == genus]
        if len(sub):
            rows += metric_rows(summarize_loo(sub, f"kandidat Malili v0.1, genus {genus}", "logika"), "6.1", target, note)
    return rows, full


def loo_imarfish(rules, threads) -> list[dict]:
    seqs = read_fasta(IMARFISH / "Sequence_mifish_indo_derep_clean.fasta")
    seqs = {a.split(".")[0]: s for a, s in seqs.items()}
    tax = pd.read_csv(IMARFISH / "Sequence_mifish_indo_derep_clean_taxon.txt", sep=" ", quotechar='"', dtype=str)
    records = {}
    for acc, taxon in zip(tax.iloc[:, 0], tax.iloc[:, 1]):
        parts = [p.strip() for p in str(taxon).split(";")]
        if len(parts) < 7:
            continue
        records[acc.split(".")[0]] = RefRecord(acc.split(".")[0], parts[6], parts[5], parts[4])
    queries, species, seen = {}, {}, set()
    for acc in sorted(seqs):
        rec = records.get(acc)
        if rec is None or not rec.key[1] or (rec.key[0], seqs[acc]) in seen:
            continue
        seen.add((rec.key[0], seqs[acc]))
        queries[acc] = seqs[acc]
        species[acc] = rec.key[0]
    hits = all_vs_all(queries, seqs, rules, threads)
    df = leave_one_out(queries, species, hits, records, rules, logic_only=True)
    df.to_csv(OUT / "loo_imarfish.csv", index=False, lineterminator="\n")
    note = "I-MarFish LocalDB (DBP UNDIP, ikan laut), pembanding simulasi lama; tanpa info voucher"
    return metric_rows(summarize_loo(df, "I-MarFish LocalDB (8.370 urutan)", "logika"), "6.1",
                       {"biotrace_nama_keliru_lolos_pct": "< 16"}, note)


def lake_st_pierre(rules, threads) -> tuple[list[dict], dict]:
    ref = load_reference(LSP / "ref")
    seqs = read_fasta(ref.root / "ref12S.fasta")
    records = reference_records(ref)
    region = set(ref.checklist["spesies"])
    queries, species = mifish_queries(seqs, records, region)
    hits = all_vs_all(queries, seqs, rules, threads)
    loo = leave_one_out(queries, species, hits, records, rules)
    loo.to_csv(OUT / "loo_lake_st_pierre.csv", index=False, lineterminator="\n")
    summ = summarize_loo(loo, "Kanada (mitohelper, spesies Lake St. Pierre + kerabat)", "penuh: tercatat di wilayah uji")
    rows = metric_rows(summ, "6.2", {"biotrace_turun_genus_atau_tidak_dikenal_pct": ">= 90"},
                       "uji tanpa-satu-spesies pada referensi Kanada (jalur kedua)")

    # tabel deteksi -> proyek uji; ASV semu = amplikon referensi spesies yang terdeteksi
    amplicons = {}
    for acc in sorted(queries):
        amplicons.setdefault(species[acc], queries[acc])
    edna = pd.read_csv(LSP / "edna_lg_clean.csv")
    codes = pd.read_csv(LSP / "fish_codes.csv", dtype=str).dropna(subset=["Genus", "Species"])
    files = detection_project(edna, codes, amplicons, OUT / "lsp_proyek_uji")
    report = run(files["reads"], files["metadata"], fasta=files["fasta"], rules=rules, reference=ref,
                 mode="uji", threads=threads)
    report.claims.to_csv(OUT / "lsp_klaim.csv", index=False, lineterminator="\n")
    prec = precision_vs_electrofishing(report.claims, codes, pd.read_csv(LSP / "elec_long.csv"),
                                       pd.read_csv(LSP / "elec_env.csv"), edna)
    c = report.claims
    detail = {
        "uji_tanpa_satu_spesies": summ,
        "proyek_deteksi": {
            "klaim": len(c),
            "sebaran_nilai": c["nilai"].value_counts().sort_index().to_dict(),
            "sebaran_keputusan": c["keputusan"].value_counts().to_dict(),
            "sebaran_tingkat": c["tingkat"].value_counts().to_dict(),
            "skor_L2": c["skor_L2"].value_counts().sort_index().to_dict(),
            "skor_L4": c["skor_L4"].value_counts().sort_index().to_dict(),
            "deteksi_tanpa_amplikon_referensi": sorted(set(edna.loc[edna["count"] > 0, "CODE_BDRSI"]) -
                                                       {a.removeprefix("lsp_") for a in c["asv_id"]}),
            "informasi_hilang": report.project.missing_info,
        },
        "electrofishing": prec,
        "catatan": "Electrofishing juga melewatkan spesies; presisi terhadapnya adalah batas bawah. "
                   "Ronde sampling dipakai sebagai replikat (1-2), jadi L4 maksimal 1; tabel tanpa kontrol negatif.",
    }
    ab_note = (f"{prec['cocok_electrofishing']} dari {prec['klaim_AB_spesies_di_sektor_electrofishing']} klaim A-B; "
               "batas bawah" if prec["klaim_AB_spesies_di_sektor_electrofishing"] else
               "tidak bisa dihitung: 0 klaim A-B karena tiap lokasi hanya 1 replikat (L4 = 0) dan tanpa kontrol")
    rows.append({"uji": "6.2", "referensi": summ["referensi"], "aturan": "mesin penuh, mode uji",
                 "metrik": "presisi_klaim_AB_vs_electrofishing_pct", "nilai": prec["presisi_AB_pct"],
                 "target": ">= 90", "catatan": ab_note})
    rows.append({"uji": "6.2", "referensi": summ["referensi"], "aturan": "mesin penuh, mode uji",
                 "metrik": "presisi_klaim_spesies_semua_nilai_vs_electrofishing_pct",
                 "nilai": prec["presisi_spesies_semua_nilai_pct"], "target": "",
                 "catatan": f"{prec['cocok_electrofishing_semua_nilai']} dari {prec['klaim_spesies_semua_nilai']} "
                            "klaim tingkat spesies di sektor electrofishing; pelengkap, batas bawah"})
    return rows, detail


def li2019_rows(rules) -> list[dict]:
    files = [p for p in (ROOT / "data" / "test" / "li2019").glob("*") if p.suffix in (".csv", ".tsv", ".txt")]
    if not files:
        return [{"uji": "6.3", "referensi": "Li dkk. 2019", "aturan": "L4", "metrik": "tag_jump_fraction",
                 "nilai": rules["l4"]["tag_jump_fraction"], "target": "disetel dari kontrol",
                 "catatan": "tabel Li dkk. 2019 belum ada di repo; ditandai belum dikalibrasi"}]
    return [{"uji": "6.3", "referensi": "Li dkk. 2019", "aturan": "L4", "metrik": "berkas_tersedia",
             "nilai": ", ".join(p.name for p in files), "target": "",
             "catatan": "jalankan kalibrasi L4 setelah format tabel dipastikan"}]


def write_error_by_grade(full: pd.DataFrame) -> None:
    eg = error_by_grade(full)
    eg["galat"] = [
        f"{str(r.galat_pct).replace('.', ',')}% (n={r.n}; uji tanpa-satu-spesies ref Malili v0.1)" if r.n
        else "belum dikalibrasi (n=0)" for r in eg.itertuples()]
    eg.to_csv(OUT / "galat_per_nilai.csv", index=False, lineterminator="\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--skip-imarfish", action="store_true")
    args = ap.parse_args()
    rules = load_rules()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    rows, full = loo_malili(rules, args.threads)
    print(f"6.1 Malili selesai ({time.perf_counter() - t0:.0f} dtk)")
    write_error_by_grade(full)
    if not args.skip_imarfish:
        rows += loo_imarfish(rules, args.threads)
        print(f"6.1 I-MarFish selesai ({time.perf_counter() - t0:.0f} dtk)")
    lsp_rows, detail = lake_st_pierre(rules, args.threads)
    rows += lsp_rows
    print(f"6.2 Lake St. Pierre selesai ({time.perf_counter() - t0:.0f} dtk)")
    rows += li2019_rows(rules)
    pd.DataFrame(rows).to_csv(OUT / "results_v0.1.csv", index=False, lineterminator="\n")
    (OUT / "lake_st_pierre.json").write_text(json.dumps(detail, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    show = pd.DataFrame(rows)
    show = show[show["metrik"].isin(["n_kueri", "ambang97_nama_keliru_lolos_pct", "biotrace_nama_keliru_lolos_pct",
                                     "biotrace_nama_keliru_nilai_A_pct", "biotrace_turun_genus_atau_tidak_dikenal_pct",
                                     "presisi_klaim_AB_vs_electrofishing_pct",
                                     "presisi_klaim_spesies_semua_nilai_vs_electrofishing_pct"])]
    print(show[["uji", "referensi", "aturan", "metrik", "nilai", "target"]].to_string(index=False))


if __name__ == "__main__":
    main()
