"""Tahap 1.3: tarik metadata spesimen GenBank untuk setiap aksesi kandidat.

Membaca kolom specimen_voucher, country, dan isolate dari ringkasan GenBank (E-utilities
esummary, database nucleotide), 100 aksesi per permintaan dengan jeda supaya di bawah
batas 3 permintaan per detik. Respons mentah disimpan di data/raw/genbank/ dan dicatat di
manifest; tabel hasilnya di data/raw/genbank/voucher.csv.

Alamat email tim untuk NCBI diambil dari variabel BIOTRACE_ENTREZ_EMAIL bila ada.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import RAW_DIR  # noqa: E402
from biotrace.manifest import upsert  # noqa: E402

ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
CANDIDATES = RAW_DIR / "biotrace_ref_malili_v0.1" / "ref12S_malili_kandidat_taksonomi.csv"
OUT_DIR = RAW_DIR / "genbank"
BATCH = 100
QUALIFIERS = ("specimen_voucher", "country", "isolate", "bio_material", "culture_collection")


def esummary(ids: list[str]) -> dict:
    params = {"db": "nucleotide", "id": ",".join(ids), "retmode": "json", "tool": "biotrace"}
    email = os.environ.get("BIOTRACE_ENTREZ_EMAIL")
    if email:
        params["email"] = email
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    data = urllib.parse.urlencode(params).encode()
    for attempt in range(4):
        try:
            with urllib.request.urlopen(ESUMMARY, data=data, timeout=120) as r:
                return json.load(r)
        except Exception as exc:  # jaringan atau batas laju: coba lagi dengan jeda
            wait = 2 ** attempt
            print(f"  gagal ({exc}); ulang dalam {wait} dtk")
            time.sleep(wait)
    raise RuntimeError("esummary gagal setelah 4 percobaan")


def parse_source_qualifiers(doc: dict) -> dict:
    names = (doc.get("subtype") or "").split("|")
    values = (doc.get("subname") or "").split("|")
    q = dict(zip(names, values))
    return {k: q.get(k, "") for k in QUALIFIERS}


def main(candidates: Path = CANDIDATES) -> None:
    with open(candidates, newline="", encoding="utf-8") as fh:
        ids = [row["aksesi"] for row in csv.DictReader(fh)]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        raw_path = OUT_DIR / f"esummary_{i // BATCH:03d}.json"
        if raw_path.exists():
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
        else:
            print(f"esummary {i + 1}-{i + len(chunk)} dari {len(ids)}")
            payload = esummary(chunk)
            raw_path.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
            time.sleep(0.4)
        upsert(raw_path, "NCBI GenBank, E-utilities esummary (nucleotide)",
               "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
               "diambil saat unduh", "Data publik NCBI")
        result = payload.get("result", {})
        by_acc = {}
        for uid in result.get("uids", []):
            doc = result[uid]
            acc = doc.get("caption") or doc.get("accessionversion", "").split(".")[0]
            by_acc[acc] = doc
        for acc in chunk:
            doc = by_acc.get(acc)
            if doc is None:
                rows.append({"aksesi": acc, "ditemukan": "tidak"})
                continue
            q = parse_source_qualifiers(doc)
            rows.append({
                "aksesi": acc,
                "ditemukan": "ya",
                "aksesi_versi": doc.get("accessionversion", ""),
                "organisme_genbank": doc.get("organism", ""),
                "taxid": doc.get("taxid", ""),
                "panjang_genbank": doc.get("slen", ""),
                "tanggal_genbank": doc.get("updatedate", ""),
                **q,
            })
    out = OUT_DIR / "voucher.csv"
    cols = ["aksesi", "ditemukan", "aksesi_versi", "organisme_genbank", "taxid", "panjang_genbank",
            "tanggal_genbank", *QUALIFIERS]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["aksesi"]):
            w.writerow({c: r.get(c, "") for c in cols})
    n_v = sum(1 for r in rows if r.get("specimen_voucher"))
    print(f"{len(rows)} aksesi dicek; {n_v} punya specimen_voucher -> {out}")


if __name__ == "__main__":
    main()
