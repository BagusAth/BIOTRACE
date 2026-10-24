"""Tahap 1.2: cek nama baku dan kemunculan di Indonesia lewat GBIF species API.

Untuk setiap nama binomial kandidat: cocokkan nama (species/match), lalu hitung catatan
kemunculan dengan filter negara Indonesia (occurrence/search?country=ID). Juga mengambil
daftar spesies Telmatherinidae yang diterima GBIF untuk menormalkan checklist.
Respons mentah disimpan di data/raw/gbif/ dan dicatat di manifest.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import DATA_DIR, RAW_DIR  # noqa: E402
from biotrace.manifest import upsert  # noqa: E402
from biotrace.taxonomy import species_key  # noqa: E402

API = "https://api.gbif.org/v1/"
OUT_DIR = RAW_DIR / "gbif"
CANDIDATES = RAW_DIR / "biotrace_ref_malili_v0.1" / "ref12S_malili_kandidat_taksonomi.csv"
CHECKLIST = DATA_DIR / "ref" / "v0.1" / "checklist_malili.csv"


def get(path: str, **params) -> dict:
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as exc:
            time.sleep(2 ** attempt)
            last = exc
    raise RuntimeError(f"GBIF gagal: {url}: {last}")


def iucn_category(key: int) -> dict:
    """Kategori IUCN Red List lewat GBIF; kosong bila spesies belum dinilai."""
    url = API + f"species/{key}/iucnRedListCategory"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            body = r.read()
        return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        if exc.code in (204, 404):
            return {}
        raise


def check_species(name: str) -> dict:
    match = get("species/match", name=name, kingdom="Animalia", strict="true")
    key = match.get("acceptedUsageKey") or match.get("usageKey")
    count = None
    iucn: dict = {}
    if key and match.get("matchType") != "NONE":
        count = get("occurrence/search", taxonKey=key, country="ID", limit=0).get("count")
        iucn = iucn_category(key)
    return {"nama": name, "match": match, "taxon_key": key, "jumlah_kemunculan_id": count, "iucn": iucn}


def telmatherinidae() -> dict:
    fam = get("species/match", name="Telmatherinidae", rank="FAMILY", kingdom="Animalia")
    res = get("species/search", highertaxon_key=fam["usageKey"], rank="SPECIES",
              status="ACCEPTED", limit=100)
    names = sorted({r["canonicalName"] for r in res.get("results", []) if r.get("canonicalName")})
    return {"family": fam, "accepted_species": names}


def main() -> None:
    names: set[str] = set()
    with open(CANDIDATES, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key, resolved = species_key(row["spesies"])
            if resolved:
                names.add(key)
    if CHECKLIST.exists():
        with open(CHECKLIST, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                key, resolved = species_key(row["spesies"])
                if resolved:
                    names.add(key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = OUT_DIR / "gbif_species_indonesia.json"
    cached = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.exists() else {}
    todo = sorted(n for n in names if n not in cached)
    print(f"{len(names)} nama; {len(todo)} perlu dicek ke GBIF")
    with ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(check_species, todo):
            cached[res["nama"]] = res
    raw_path.write_text(json.dumps(cached, indent=1, sort_keys=True), encoding="utf-8")
    upsert(raw_path, "GBIF species API dan occurrence search (country=ID)",
           "https://api.gbif.org/v1/", "diambil saat unduh", "Cek lisensi per dataset GBIF")

    fam_path = OUT_DIR / "gbif_telmatherinidae.json"
    if not fam_path.exists():
        fam_path.write_text(json.dumps(telmatherinidae(), indent=1, sort_keys=True), encoding="utf-8")
    upsert(fam_path, "GBIF species API, Telmatherinidae (spesies diterima)",
           "https://api.gbif.org/v1/species/search", "diambil saat unduh", "Cek lisensi per dataset GBIF")

    out = OUT_DIR / "gbif_indonesia.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["spesies", "taxon_key", "nama_gbif", "status_gbif", "match_type",
                    "jumlah_kemunculan_id", "kategori_iucn"])
        for n in sorted(cached):
            r = cached[n]
            m = r["match"]
            w.writerow([n, r["taxon_key"] or "", m.get("species") or m.get("canonicalName", ""),
                        m.get("status", ""), m.get("matchType", ""),
                        "" if r["jumlah_kemunculan_id"] is None else r["jumlah_kemunculan_id"],
                        (r.get("iucn") or {}).get("code", "")])
    fam = json.loads(fam_path.read_text(encoding="utf-8"))
    print(f"Telmatherinidae diterima GBIF: {len(fam['accepted_species'])} spesies")
    print(f"tabel -> {out}")


if __name__ == "__main__":
    main()
