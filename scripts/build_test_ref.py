"""Tahap 6.2: bangun referensi uji Kanada untuk Lake St. Pierre (F27).

Mitohelper 12S disaring ke spesies di fish_codes.csv beserta kerabat satu genus, lalu
disimpan terpisah di data/test/lake_st_pierre/ref dengan jenis "uji_luar". Mesin menolak
memakai referensi ini pada proyek Indonesia.

Kolom tercatat_di_indonesia di referensi uji berarti "tercatat di wilayah uji": ya untuk
spesies di fish_codes.csv, tidak untuk kerabat dari luar wilayah. Status voucher tidak
dicek; semua sekuens bernama spesies dianggap tervalidasi karena modul ini hanya menguji
logika mesin.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import RAW_DIR, ROOT, find_blast_tool, sha256_file  # noqa: E402
from biotrace.reference import (REFERENCE_FILES, build_blast_db, compute_completeness,  # noqa: E402
                                read_qza_sequences, read_qza_taxonomy, write_fasta)
from biotrace.taxonomy import species_key  # noqa: E402

LSP_RAW = RAW_DIR / "lake_st_pierre"
TEST_DIR = ROOT / "data" / "test" / "lake_st_pierre"
REF_DIR = TEST_DIR / "ref"
REGION = "Lake St. Pierre"
LAKE = "Lac Saint-Pierre"


def main() -> None:
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    for f in ("edna_env.csv", "edna_lg_clean.csv", "elec_env.csv", "elec_long.csv", "fish_codes.csv", "README.md"):
        shutil.copy2(LSP_RAW / f, TEST_DIR / f)

    codes = pd.read_csv(LSP_RAW / "fish_codes.csv", dtype=str).dropna(subset=["Genus", "Species"])
    named = codes[~codes["Species"].str.fullmatch(r"spp?\.?")].copy()   # "sp." = deteksi tingkat genus
    named["spesies"] = named["Genus"] + " " + named["Species"]
    named = named[named["spesies"].map(lambda s: species_key(s)[1])]
    region_species = set(named["spesies"])
    genera = set(named["Genus"])

    qdir = RAW_DIR / "mitohelper" / "QIIME-compatible"
    tax = read_qza_taxonomy(qdir / "12S-tax-derep-uniq.qza")
    seqs = read_qza_sequences(qdir / "12S-seqs-derep-uniq.qza")
    tax = tax[tax["genus"].isin(genera)].copy()
    keys = tax["spesies"].map(species_key)
    tax["spesies_kunci"] = keys.map(lambda k: k[0])
    tax["terselesaikan"] = keys.map(lambda k: "ya" if k[1] else "tidak")
    tax["tercatat_di_indonesia"] = tax["spesies_kunci"].map(lambda s: "ya" if s in region_species else "tidak")
    tax["status_validasi"] = tax["terselesaikan"].map(lambda r: "tervalidasi" if r == "ya" else "belum tervalidasi")
    tax["alasan_validasi"] = "referensi uji: voucher tidak dicek"
    tax["panjang_bp"] = tax["aksesi"].map(lambda a: str(len(seqs[a])))
    tax["peran_di_malili"] = ""
    tax["sumber"] = "mitohelper 12S Jul2026 (GenBank+MitoFish)"
    tax["status_voucher"] = "tidak dicek"
    tax["sumber_tercatat"] = "fish_codes.csv Lake St. Pierre"
    tax["tanggal_masuk"] = "2026-10-24"
    cols = ["aksesi", "famili", "genus", "spesies", "spesies_kunci", "terselesaikan", "panjang_bp", "peran_di_malili",
            "sumber", "status_voucher", "status_validasi", "alasan_validasi", "tercatat_di_indonesia",
            "sumber_tercatat", "tanggal_masuk"]
    tax = tax[cols].sort_values("aksesi").reset_index(drop=True)

    REF_DIR.mkdir(parents=True, exist_ok=True)
    write_fasta({a: seqs[a].upper() for a in tax["aksesi"]}, REF_DIR / "ref12S.fasta")
    tax.to_csv(REF_DIR / "ref12S_taksonomi.csv", index=False, lineterminator="\n")
    checklist = pd.DataFrame({"spesies": sorted(region_species)})
    fam = named.set_index("spesies")["Family"].to_dict()
    checklist["famili"] = checklist["spesies"].map(fam)
    checklist["danau"] = REGION
    checklist["status"] = "tercatat"
    checklist["sumber"] = "fish_codes.csv (Astorg dkk. 2025)"
    checklist["tahun"] = "2025"
    checklist.to_csv(REF_DIR / "checklist_lsp.csv", index=False, lineterminator="\n")
    for name, cols_ in (("status.csv", ["spesies", "kategori_iucn", "invasif"]),
                        ("alias.csv", ["nama_induk", "nama_alias", "tingkat"]),
                        ("jalur_masuk.csv", ["spesies", "jalur", "fasilitas_sekitar", "sumber_dna_lain"])):
        pd.DataFrame(columns=cols_).to_csv(REF_DIR / name, index=False, lineterminator="\n")
    comp = compute_completeness(checklist, tax, REGION, [LAKE])
    comp.to_csv(REF_DIR / "kelengkapan.csv", index=False, lineterminator="\n")
    meta = {"nama": "ref12S-uji-LSP", "version": "v0.1", "jenis": "uji_luar", "wilayah": REGION, "danau": [LAKE],
            "marker": "12S rRNA", "blast_db": "ref12S", "aturan_validasi": "tidak dicek (uji logika mesin)",
            "dibuat": "2026-10-24", "berkas": {"checklist_malili.csv": "checklist_lsp.csv"},
            "sumber": ["mitohelper 12S Juli 2026", "Astorg dkk. 2025 fish_codes.csv"],
            "catatan": "hanya untuk modul uji; tidak pernah dipakai menamai ikan Indonesia"}
    (REF_DIR / "reference.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
                                            encoding="utf-8", newline="\n")
    exe = find_blast_tool("makeblastdb")
    if exe:
        build_blast_db(exe, REF_DIR / "ref12S.fasta", REF_DIR / "ref12S")
    with open(REF_DIR / "manifest_sha256.txt", "w", encoding="utf-8", newline="\n") as fh:
        for name in [meta["berkas"].get(n, n) for n in REFERENCE_FILES]:
            fh.write(f"{sha256_file(REF_DIR / name)}  {name}\n")
    covered = comp[comp["wilayah"] == REGION]
    print(f"referensi uji: {len(tax)} sekuens, {tax['spesies_kunci'].nunique()} takson, "
          f"{len(region_species)} spesies wilayah, {int(covered['r_tervalidasi'].sum())} punya 12S")


if __name__ == "__main__":
    main()
