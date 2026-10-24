"""Tahap 1: bangun referensi BioTrace v0.1 untuk Malili.

Langkah (Rencana Implementasi 1.1-1.6):
  1.1 muat kandidat 12S (arsip Audit Dataset, atau buat ulang dari mitohelper --from-mitohelper)
  1.2 tandai tercatat_di_indonesia (checklist Malili, daftar introduksi, GBIF country=ID)
  1.3 tetapkan status validasi dari GenBank (specimen_voucher)
  1.4 susun status.csv dari IUCN (lewat GBIF) dan daftar invasif bersumber
  1.5 hitung peta kelengkapan per genus dan wilayah
  1.6 bangun database BLAST dan catat SHA-256 semua berkas referensi

Jalankan setelah scripts/fetch_raw.py, scripts/fetch_voucher.py, dan scripts/fetch_gbif.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import RAW_DIR, find_blast_tool, sha256_file  # noqa: E402
from biotrace.manifest import relpath, upsert  # noqa: E402
from biotrace.reference import (  # noqa: E402
    REFERENCE_FILES, build_blast_db, compute_completeness, read_csv, read_fasta,
    read_qza_sequences, read_qza_taxonomy, write_fasta,
)
from biotrace.taxonomy import genus_of, same_species_name, species_key  # noqa: E402

REF_DIR = Path(__file__).resolve().parent.parent / "data" / "ref" / "v0.1"
CAND_DIR = RAW_DIR / "biotrace_ref_malili_v0.1"
REGION = "Kompleks Malili"
LAKES = ["Matano", "Mahalona", "Towuti"]
ENTRY_DATE = "2026-10-24"
MITOHELPER_SOURCE = "mitohelper 12S Jul2026 (GenBank+MitoFish)"


def load_candidates(from_mitohelper: bool) -> tuple[pd.DataFrame, dict[str, str]]:
    cand = read_csv(CAND_DIR / "ref12S_malili_kandidat_taksonomi.csv")
    if not from_mitohelper:
        return cand, read_fasta(CAND_DIR / "ref12S_malili_kandidat.fasta")
    # buat ulang: saring mitohelper per genus kandidat, peran diwarisi per genus
    qdir = RAW_DIR / "mitohelper" / "QIIME-compatible"
    tax = read_qza_taxonomy(qdir / "12S-tax-derep-uniq.qza")
    seqs = read_qza_sequences(qdir / "12S-seqs-derep-uniq.qza")
    role = cand.groupby("genus")["peran_di_malili"].agg(lambda s: s.mode().iloc[0]).to_dict()
    tax = tax[tax["genus"].isin(role)]
    rebuilt = pd.DataFrame({
        "aksesi": tax["aksesi"], "famili": tax["famili"], "genus": tax["genus"],
        "spesies": tax["spesies"], "panjang_bp": tax["aksesi"].map(lambda a: str(len(seqs[a]))),
        "peran_di_malili": tax["genus"].map(role), "sumber": MITOHELPER_SOURCE,
        "status_validasi": "belum tervalidasi",
    })
    return rebuilt.reset_index(drop=True), {a: seqs[a] for a in rebuilt["aksesi"]}


def recorded_status(species: str, resolved: bool, checklist: pd.DataFrame, introduced: set[str],
                    gbif: dict[str, dict]) -> tuple[str, str]:
    if not resolved:
        return "belum dicek", "nama belum sampai spesies"
    if any(same_species_name(species, s) for s in checklist["spesies"]):
        return "ya", "checklist Malili"
    if species in introduced:
        return "ya", "daftar introduksi Malili"
    g = gbif.get(species)
    if not g or g.get("jumlah_kemunculan_id") is None:
        return "belum dicek", "tidak cocok di GBIF"
    n = int(g["jumlah_kemunculan_id"])
    return ("ya", f"GBIF {n} kemunculan country=ID") if n > 0 else ("tidak", "GBIF 0 kemunculan country=ID")


def validation(row: pd.Series) -> tuple[str, str, str]:
    """Aturan v0.1: tervalidasi bila ada specimen_voucher dan nama GenBank sama."""
    voucher = row.get("specimen_voucher", "")
    status_voucher = "ada" if voucher else "tidak ada"
    if row["terselesaikan"] != "ya":
        return status_voucher, "belum tervalidasi", "nama belum sampai spesies"
    gb = row.get("organisme_genbank", "")
    if gb and not same_species_name(gb, row["spesies"]):
        return status_voucher, "belum tervalidasi", f"nama GenBank berbeda: {gb}"
    if voucher:
        return status_voucher, "tervalidasi", f"specimen_voucher {voucher}"
    return status_voucher, "belum tervalidasi", "tanpa specimen_voucher"


def build_status(checklist: pd.DataFrame, invasif: pd.DataFrame, gbif: dict[str, dict]) -> pd.DataFrame:
    names = sorted(set(checklist["spesies"]) | set(invasif["spesies"]))
    rows = []
    for name in names:
        key, resolved = species_key(name)
        iucn = (gbif.get(key) or {}).get("iucn") or {}
        inv = invasif[invasif["spesies"] == name]
        rows.append({
            "spesies": name,
            "kategori_iucn": iucn.get("code", "") if resolved else "",
            "sumber_iucn": "IUCN Red List lewat GBIF species API" if iucn else "belum dinilai/tidak ditemukan",
            "permen_kp_19_2020": "belum dicek",
            "invasif": inv["invasif"].iloc[0] if len(inv) else "tidak tercatat",
            "sumber_invasif": inv["sumber"].iloc[0] if len(inv) else "",
        })
    return pd.DataFrame(rows)


def species_coverage(checklist: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """Ketersediaan 12S per spesies checklist (mereproduksi temuan Audit Dataset)."""
    rows = []
    for name, grp in checklist.groupby("spesies", sort=True):
        key, resolved = species_key(name)
        seqs = ref[ref["spesies_kunci"] == key] if resolved else ref.iloc[0:0]
        rows.append({
            "spesies": name, "status_di_malili": grp["status"].iloc[0],
            "danau": "; ".join(sorted(grp["danau"])),
            "jumlah_sekuens_12S": len(seqs),
            "jumlah_tervalidasi": int((seqs["status_validasi"] == "tervalidasi").sum()),
            "ada_referensi": "ya" if len(seqs) else "tidak",
            "ada_referensi_tervalidasi": "ya" if (seqs["status_validasi"] == "tervalidasi").any() else "tidak",
        })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-mitohelper", action="store_true", help="buat ulang kandidat dari berkas .qza")
    args = ap.parse_args()

    cand, seqs = load_candidates(args.from_mitohelper)
    checklist = read_csv(REF_DIR / "checklist_malili.csv")
    invasif = read_csv(REF_DIR / "sumber" / "invasif.csv")
    voucher = read_csv(RAW_DIR / "genbank" / "voucher.csv")
    gbif = json.loads((RAW_DIR / "gbif" / "gbif_species_indonesia.json").read_text(encoding="utf-8"))
    introduced = {species_key(s)[0] for s in checklist.loc[checklist["status"] == "introduksi", "spesies"]}

    # 1.1-1.3: satu baris per sekuens dengan spesies, tercatat_di_indonesia, status validasi
    ref = cand.merge(voucher, on="aksesi", how="left").fillna("")
    keys = ref["spesies"].map(species_key)
    ref["spesies_kunci"] = keys.map(lambda k: k[0])
    ref["terselesaikan"] = keys.map(lambda k: "ya" if k[1] else "tidak")
    rec = [recorded_status(k, r == "ya", checklist, introduced, gbif)
           for k, r in zip(ref["spesies_kunci"], ref["terselesaikan"])]
    ref["tercatat_di_indonesia"] = [r[0] for r in rec]
    ref["sumber_tercatat"] = [r[1] for r in rec]
    val = ref.apply(validation, axis=1, result_type="expand")
    ref["status_voucher"], ref["status_validasi"], ref["alasan_validasi"] = val[0], val[1], val[2]
    ref["tanggal_masuk"] = ENTRY_DATE
    cols = ["aksesi", "famili", "genus", "spesies", "spesies_kunci", "terselesaikan", "panjang_bp",
            "peran_di_malili", "sumber", "aksesi_versi", "organisme_genbank", "specimen_voucher", "country",
            "isolate", "status_voucher", "status_validasi", "alasan_validasi", "tercatat_di_indonesia",
            "sumber_tercatat", "tanggal_masuk"]
    ref = ref[cols].sort_values("aksesi").reset_index(drop=True)
    missing_seq = [a for a in ref["aksesi"] if a not in seqs]
    if missing_seq:
        raise SystemExit(f"{len(missing_seq)} aksesi tanpa sekuens, mis. {missing_seq[:3]}")

    REF_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta({a: seqs[a].upper() for a in ref["aksesi"]}, REF_DIR / "ref12S.fasta")
    ref.to_csv(REF_DIR / "ref12S_taksonomi.csv", index=False, lineterminator="\n")
    voucher[voucher["aksesi"].isin(ref["aksesi"])].sort_values("aksesi").to_csv(
        REF_DIR / "aksesi_dicek.csv", index=False, lineterminator="\n")

    # 1.4 status, 1.5 kelengkapan
    build_status(checklist, invasif, gbif).to_csv(REF_DIR / "status.csv", index=False, lineterminator="\n")
    comp = compute_completeness(checklist, ref, REGION, LAKES)
    comp.to_csv(REF_DIR / "kelengkapan.csv", index=False, lineterminator="\n")
    cov = species_coverage(checklist, ref)
    cov.to_csv(REF_DIR / "kelengkapan_spesies.csv", index=False, lineterminator="\n")

    meta = {
        "nama": "ref12S", "version": "v0.1", "jenis": "indonesia", "wilayah": REGION, "danau": LAKES,
        "marker": "12S rRNA", "blast_db": "ref12S", "aturan_validasi": "specimen_voucher GenBank",
        "dibuat": ENTRY_DATE,
        "kandidat": "mitohelper (dibuat ulang)" if args.from_mitohelper else "biotrace_ref_malili_v0.1.zip",
        "sumber": ["mitohelper 12S Juli 2026 (Lim & Thompson 2021)", "NCBI GenBank esummary",
                   "GBIF species API", "IUCN Red List lewat GBIF", "Kottelat 1990, 1991",
                   "Herder dkk. 2006", "Hedianto & Sentosa 2019", "Mongabay 2018"],
        "catatan": "checklist sementara; perlu tinjauan ahli",
    }
    (REF_DIR / "reference.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
                                            encoding="utf-8", newline="\n")

    # 1.6 database BLAST dan SHA-256
    exe = find_blast_tool("makeblastdb")
    if exe:
        build_blast_db(exe, REF_DIR / "ref12S.fasta", REF_DIR / "ref12S")
    else:
        print("PERINGATAN: makeblastdb tidak ditemukan; database BLAST dibangun saat pertama dipakai")
    tracked = sorted(set(REFERENCE_FILES) | {"aksesi_dicek.csv", "kelengkapan_spesies.csv", "alias.csv",
                                             "jalur_masuk.csv", "sumber/invasif.csv"})
    with open(REF_DIR / "manifest_sha256.txt", "w", encoding="utf-8", newline="\n") as fh:
        for name in tracked:
            fh.write(f"{sha256_file(REF_DIR / name)}  {name}\n")
    for name in ("ref12S.fasta", "ref12S_taksonomi.csv", "aksesi_dicek.csv", "kelengkapan.csv", "status.csv"):
        upsert(REF_DIR / name, "BioTrace referensi v0.1 (turunan tahap 1)", relpath(REF_DIR / name),
               "v0.1", "turunan; ikuti lisensi sumber (mitohelper, GenBank, GBIF)")

    # ringkasan sesuai kriteria selesai tahap 1
    endemic = cov[cov["status_di_malili"] == "endemik"]
    tel = comp[(comp["wilayah"] == REGION) & (comp["genus"] == "Telmatherina")].iloc[0]
    print(f"{len(ref)} sekuens, {ref['spesies_kunci'].nunique()} takson; "
          f"tervalidasi {int((ref['status_validasi'] == 'tervalidasi').sum())}; "
          f"tercatat di Indonesia (sekuens) {int((ref['tercatat_di_indonesia'] == 'ya').sum())}")
    print(f"endemik dengan 12S: {int((endemic['ada_referensi'] == 'ya').sum())} dari {len(endemic)}; "
          f"dengan 12S tervalidasi: {int((endemic['ada_referensi_tervalidasi'] == 'ya').sum())} dari {len(endemic)}")
    print(f"P Telmatherina ({REGION}) = {tel['p_belum_di_kamus']} (n={tel['n_checklist']}, r={tel['r_tervalidasi']})")
    tel_fam = endemic[endemic["spesies"].map(genus_of).isin(["Telmatherina", "Paratherina", "Tominanga"])]
    print(f"telmatherinid tanpa 12S: {int((tel_fam['ada_referensi'] == 'tidak').sum())} dari {len(tel_fam)}")


if __name__ == "__main__":
    main()
