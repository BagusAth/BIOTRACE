"""Tahap 0: unduh semua berkas sumber ke data/raw/ dan catat di manifest data.

Isi data/raw/ tidak pernah diubah; turunannya dibuat oleh skrip tahap berikutnya.
Berkas GitHub dipatok ke nomor commit supaya versinya bisa diaudit.

    python scripts/fetch_raw.py --malili-zip ../GENOHACK/biotrace_ref_malili_v0.1.zip \
        --dryad-zip ../GENOHACK/doi_10_5061_dryad_3bk3j9kzf__v20250924.zip
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import RAW_DIR, ROOT  # noqa: E402
from biotrace.manifest import upsert  # noqa: E402

MITOHELPER_COMMIT = "f3d92c7a5f1d4d95555988286b71a1a3c756c315"
MITOHELPER_RAW = f"https://raw.githubusercontent.com/aomlomics/mitohelper/{MITOHELPER_COMMIT}/"
MITOHELPER_FILES = [
    "QIIME-compatible/12S-seqs-derep-uniq.qza",
    "QIIME-compatible/12S-tax-derep-uniq.qza",
    "QIIME-compatible/README.MD",
    "MitoFish_download_links.MD",
]
MITOHELPER_LICENSE = "Lisensi tidak tercantum; data dari GenBank dan MitoFish; sitasi Lim & Thompson 2021"

DBP_COMMIT = "6c29a4594220c3429d9a6c78679af971619ffd09"
DBP_RAW = f"https://raw.githubusercontent.com/mdaniealmalik/DBP_Metabarcoding_Pipeline/{DBP_COMMIT}/"
DBP_DB = "Curated-Metabarcoding-Database-for-Marine-Fish-in-Indonesia/"
DBP_FILES = [
    DBP_DB + "database_local/Sequence_mifish_indo_derep_clean.fasta",
    DBP_DB + "database_local/Sequence_mifish_indo_derep_clean_taxon.txt",
    DBP_DB + "README.md",
    "MyProject/1_Sample/Sample_1.fastq.gz",
    "MyProject/1_Sample/Sample_2.fastq.gz",
    "MyProject/1_Sample/Sample_3.fastq.gz",
    "README.md",
    "LICENSE",
]

DRYAD_DOI = "10.5061/dryad.3bk3j9kzf"
DRYAD_FILES = ["edna_env.csv", "edna_lg_clean.csv", "elec_env.csv", "elec_long.csv",
               "fish_codes.csv", "README.md"]

DEFAULT_GENOHACK = ROOT.parent / "GENOHACK"


def fetch(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    print(f"unduh {url}")
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as fh:
        shutil.copyfileobj(r, fh)
    return dest


def fetch_mitohelper() -> None:
    for f in MITOHELPER_FILES:
        dest = fetch(MITOHELPER_RAW + f, RAW_DIR / "mitohelper" / f)
        upsert(dest, "mitohelper (aomlomics), 12S Juli 2026",
               "https://github.com/aomlomics/mitohelper; Zenodo 10.5281/zenodo.21326269",
               f"commit {MITOHELPER_COMMIT[:7]}", MITOHELPER_LICENSE)


def fetch_dbp() -> None:
    for f in DBP_FILES:
        dest = fetch(DBP_RAW + f, RAW_DIR / "dbp" / f)
        upsert(dest, "DBP Metabarcoding Pipeline / I-MarFish (DBP UNDIP)",
               "https://github.com/mdaniealmalik/DBP_Metabarcoding_Pipeline",
               f"commit {DBP_COMMIT[:7]}", "GPL-3.0; jangan dibundel ke produk komersial tanpa cek")


def fetch_malili(zip_path: Path) -> None:
    if not zip_path.exists():
        print(f"PERINGATAN: {zip_path} tidak ada; lewati referensi kandidat Malili")
        return
    dest_zip = RAW_DIR / zip_path.name
    if not dest_zip.exists():
        shutil.copy2(zip_path, dest_zip)
    upsert(dest_zip, "Audit Dataset BioTrace: ekstraksi kandidat Malili dari mitohelper",
           "berkas proyek (Audit Dataset)", "v0.1", MITOHELPER_LICENSE)
    out_dir = RAW_DIR / "biotrace_ref_malili_v0.1"
    with zipfile.ZipFile(dest_zip) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            target = out_dir / Path(name).name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
            upsert(target, "Audit Dataset BioTrace: ekstraksi kandidat Malili dari mitohelper",
                   "berkas proyek (Audit Dataset)", "v0.1", MITOHELPER_LICENSE)


def fetch_lake_st_pierre(zip_path: Path) -> None:
    """Hanya lima CSV kecil dan README; raw_seq.zip (2,94 GB) tidak diambil."""
    if not zip_path.exists():
        print(f"PERINGATAN: {zip_path} tidak ada; unduh manual dari https://doi.org/{DRYAD_DOI}")
        return
    out_dir = RAW_DIR / "lake_st_pierre"
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for name in DRYAD_FILES:
            target = out_dir / name
            if not target.exists():
                target.write_bytes(zf.read(name))
            upsert(target, "Lake St. Pierre eDNA dan electrofishing (Astorg dkk. 2025, Dryad)",
                   f"https://doi.org/{DRYAD_DOI}", "v20250924", "CC0 1.0 (ketentuan Dryad); wajib sitasi")


def fetch_li2019(path: Path | None) -> None:
    out_dir = RAW_DIR / "li2019"
    if path is None or not path.exists():
        print("CATATAN: tabel Li dkk. 2019 belum diberikan (--li2019); L4 tetap 'belum dikalibrasi'")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / path.name
    shutil.copy2(path, target)
    upsert(target, "Li dkk. 2019, tabel bacaan 12S 14 danau dengan kontrol",
           "Li dkk. 2019, Journal of Applied Ecology", "data tim", "Sitasi")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--malili-zip", type=Path, default=DEFAULT_GENOHACK / "biotrace_ref_malili_v0.1.zip")
    ap.add_argument("--dryad-zip", type=Path,
                    default=DEFAULT_GENOHACK / "doi_10_5061_dryad_3bk3j9kzf__v20250924.zip")
    ap.add_argument("--li2019", type=Path, default=None)
    ap.add_argument("--skip-network", action="store_true")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not args.skip_network:
        fetch_mitohelper()
        fetch_dbp()
    fetch_malili(args.malili_zip)
    fetch_lake_st_pierre(args.dryad_zip)
    fetch_li2019(args.li2019)
    print("manifest: data/ref/v0.1/manifest.csv")


if __name__ == "__main__":
    main()
