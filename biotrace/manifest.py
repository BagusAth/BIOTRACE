"""Manifest data: satu baris per berkas sumber, dengan SHA-256 dan lisensi."""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from .config import DATA_DIR, ROOT, sha256_file

MANIFEST_PATH = DATA_DIR / "ref" / "v0.1" / "manifest.csv"
COLUMNS = ["berkas", "sumber", "url_atau_doi", "versi", "tanggal_unduh", "sha256", "lisensi"]


def read_manifest(path: Path = MANIFEST_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_manifest(rows: list[dict], path: Path = MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: r["berkas"])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def relpath(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def upsert(path: Path, sumber: str, url_atau_doi: str, versi: str, lisensi: str,
           manifest_path: Path = MANIFEST_PATH) -> dict:
    """Tambah atau perbarui baris berkas; tanggal unduh lama dipertahankan bila isinya sama."""
    rows = read_manifest(manifest_path)
    key = relpath(path)
    digest = sha256_file(path) if Path(path).is_file() else ""
    old = next((r for r in rows if r["berkas"] == key), None)
    tanggal = dt.date.today().isoformat()
    if old and old.get("sha256") == digest and old.get("tanggal_unduh"):
        tanggal = old["tanggal_unduh"]
    row = {"berkas": key, "sumber": sumber, "url_atau_doi": url_atau_doi, "versi": versi,
           "tanggal_unduh": tanggal, "sha256": digest, "lisensi": lisensi}
    rows = [r for r in rows if r["berkas"] != key] + [row]
    write_manifest(rows, manifest_path)
    return row
