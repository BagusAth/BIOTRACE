"""Tahap 7: skenario demo Danau Matano berlabel SIMULASI.

Sekuens referensi nyata (amplikon MiFish dari referensi v0.1) ditambah variasi buatan
berbenih tetap (random.seed 2026), supaya setiap cabang aturan muncul di layar dan demo
bisa diulang serta diaudit juri. 3 stasiun x 3 replikat, satu kontrol negatif per batch.

Keluaran di data/demo/matano/: bacaan.csv, metadata.csv, taksonomi.csv, asv.fasta,
README.md (asal setiap ASV, hasil yang diharapkan vs hasil mesin), dan hasil/ (klaim,
ringkasan, prioritas barcode, laporan PDF, manifest).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from biotrace.config import ROOT, load_rules  # noqa: E402
from biotrace.naming import hits_from_blast, run_blast  # noqa: E402
from biotrace.pipeline import run  # noqa: E402
from biotrace.reference import load_reference, read_fasta  # noqa: E402
from biotrace.report import write_outputs  # noqa: E402
from biotrace.simulate import as_amplicon, mutate  # noqa: E402

SEED = 2026
OUT = ROOT / "data" / "demo" / "matano"
LABEL = "SIMULASI"
STATIONS = {
    "ST1": {"lat": -2.4710, "lon": 121.2950, "batch": "B1", "fasilitas": ""},
    "ST2": {"lat": -2.4980, "lon": 121.3560, "batch": "B2",
            "fasilitas": "keramba jaring apung nila sekitar 300 m dari stasiun (SIMULASI)"},
    "ST3": {"lat": -2.5290, "lon": 121.4180, "batch": "B3", "fasilitas": ""},
}
REPS = ("A", "B", "C")

# asv_id, nama, asal urutan, aksesi sumber, substitusi, kehadiran {stasiun: replikat}, rentang bacaan, harapan rencana
SCENARIO = [
    ("asv01", "Nila", "sekuens referensi nyata", "MZ605472", 0, {"ST1": "ABC", "ST2": "ABC"}, (600, 2400),
     "nama spesies; label invasif"),
    ("asv02", "Gabus", "sekuens referensi nyata", "MN205549", 0, {"ST1": "ABC"}, (400, 1800),
     "nama spesies; label invasif"),
    ("asv03", "Sapu-sapu", "sekuens referensi nyata", "KT239016", 0, {"ST3": "ABC"}, (300, 1500),
     "nama spesies; label invasif"),
    ("asv04", "Karper", "sekuens referensi nyata", "LC069407", 0, {"ST1": "ABC", "ST2": "ABC"}, (500, 2000),
     "nama spesies; label invasif; di ST1 juga ada di kontrol batch B1 -> batas maksimal D"),
    ("asv05", "Amphilophus citrinellus (induk louhan)", "sekuens referensi nyata", "OQ681458", 0,
     {"ST1": "ABC", "ST2": "ABC", "ST3": "ABC"}, (2500, 6000), "kemungkinan louhan hibrida; invasif"),
    ("asv06", "Telmatherina celebensis", "sekuens referensi nyata", "AP006772", 0, {"ST3": "ABC"}, (300, 1200),
     "nama spesies bila referensinya tervalidasi; endemik"),
    ("asv07", "Telmatherina tak berreferensi", "T. celebensis + substitusi acak berbenih", "AP006772", 5,
     {"ST2": "ABC", "ST3": "ABC"}, (800, 3000), "Telmatherina sp.; penyebab referensi; peluang belum di kamus; wajib verifikasi"),
    ("asv08", "Urutan jauh", "sekuens ikan + sekitar 8% substitusi", "LC049786", 14, {"ST1": "AB"}, (150, 450),
     "tidak dikenal; masuk daftar prioritas barcode"),
    ("asv09", "Dua Oryzias yang mirip", "Oryzias dancena (12S identik dengan O. melastigma)", "AB498069", 0,
     {"ST3": "ABC"}, (300, 1000), "genus Oryzias; penyebab marker"),
    ("asv10", "Sidat (ikan asli, sinyal lemah)", "sekuens referensi nyata", "MZ605514", 0, {"ST2": "B"}, (6, 6),
     "tambahan BioTrace: bacaan < 10 tanpa label L3 -> jangan dipakai"),
]
CONTROL_READS = {("asv04", "B1"): 60}


def sample_id(station: str, rep: str) -> str:
    return f"SIM-MTN-{station}-{rep}"


def build_files(rng: random.Random) -> dict[str, str]:
    ref = load_reference()
    seqs = read_fasta(ref.root / "ref12S.fasta")
    asvs: dict[str, str] = {}
    for asv, _, _, acc, subs, _, _, _ in SCENARIO:
        amp = as_amplicon(seqs[acc])
        if amp is None:
            raise SystemExit(f"amplikon MiFish tidak ditemukan untuk {acc}")
        asvs[asv] = mutate(amp, subs, rng) if subs else amp

    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for asv, _, _, _, _, presence, (lo, hi), _ in SCENARIO:
        for station, reps in presence.items():
            for rep in reps:
                rows.append((asv, sample_id(station, rep), rng.randint(lo, hi)))
    for (asv, batch), n in CONTROL_READS.items():
        rows.append((asv, f"SIM-MTN-NEG-{batch}", n))
    reads = pd.DataFrame(rows, columns=["asv_id", "sample_id", "reads"]).sort_values(["asv_id", "sample_id"])
    reads["label_data"] = LABEL
    reads.to_csv(OUT / "bacaan.csv", index=False, lineterminator="\n")

    meta = []
    for station, info in STATIONS.items():
        for i, rep in enumerate(REPS, start=1):
            meta.append({"sample_id": sample_id(station, rep), "site_id": f"MTN-{station}", "latitude": info["lat"],
                         "longitude": info["lon"], "collection_date": "2026-08-14", "sample_type": "sampel",
                         "replicate": i, "extraction_batch": info["batch"], "marker": "12S MiFish-U",
                         "lake": "Matano", "fasilitas_sekitar": info["fasilitas"], "label_data": LABEL})
        meta.append({"sample_id": f"SIM-MTN-NEG-{info['batch']}", "site_id": f"NEG-{info['batch']}", "latitude": "",
                     "longitude": "", "collection_date": "2026-08-14", "sample_type": "kontrol_negatif_pcr",
                     "replicate": 1, "extraction_batch": info["batch"], "marker": "12S MiFish-U", "lake": "Matano",
                     "fasilitas_sekitar": "", "label_data": LABEL})
    pd.DataFrame(meta).to_csv(OUT / "metadata.csv", index=False, lineterminator="\n")

    with open(OUT / "asv.fasta", "w", encoding="utf-8", newline="\n") as fh:
        for asv in sorted(asvs):
            fh.write(f">{asv} {LABEL}\n{asvs[asv]}\n")

    # taksonomi gaya lab: kecocokan teratas dan spesies berbeda berikutnya (ambang 97% lab)
    rules = load_rules()
    hits = hits_from_blast(run_blast(asvs, ref.ensure_blast_db(), rules), ref)
    tax = []
    for asv in sorted(asvs):
        hs = sorted(hits.get(asv, []), key=lambda h: (-h.pident, h.accession))
        top = hs[0] if hs else None
        second = next((h for h in hs if top and h.species_key != top.species_key), None)
        tax.append({"asv_id": asv, "taxon": top.species if top else "",
                    "rank": "species" if top and top.pident >= 97 else "genus" if top else "",
                    "pct_identity": round(top.pident, 2) if top else "",
                    "runner_up_taxon": second.species if second else "",
                    "runner_up_pct_identity": round(second.pident, 2) if second else "",
                    "reference_db": "NCBI nt (SIMULASI)", "label_data": LABEL})
    pd.DataFrame(tax).to_csv(OUT / "taksonomi.csv", index=False, lineterminator="\n")
    return asvs


def write_readme(report) -> None:
    c = report.claims
    lines = [
        "# Skenario demo Danau Matano — SIMULASI",
        "",
        "**Data demo sintetis berlabel SIMULASI; bukan hasil lapangan.** Dibuat oleh `scripts/make_demo.py`",
        f"dengan `random.seed({SEED})`. Setiap baris berkas memuat kolom `label_data = SIMULASI`, ID sampel",
        "berawalan `SIM-`, dan header FASTA bertanda SIMULASI.",
        "",
        "Desain: 3 stasiun (ST1-ST3) x 3 replikat di Danau Matano, satu kontrol negatif PCR per batch",
        "ekstraksi (B1-B3). ST2 diberi fasilitas sekitar fiktif (keramba nila) untuk kalimat asal-usul.",
        "",
        "| ASV | Isi | Asal urutan | Aksesi sumber | Substitusi | Harapan rencana | Hasil mesin |",
        "|---|---|---|---|---:|---|---|",
    ]
    for asv, name, origin, acc, subs, _, _, expect in SCENARIO:
        got = c[c["asv_id"] == asv]
        res = "; ".join(f"{r.site_id}: {r.taxon_dilaporkan} ({r.tingkat}), nilai {r.nilai}, {r.keputusan}"
                        + (f", label {r.label_L3}" if r.label_L3 else "") + (f", penyebab {r.penyebab}" if r.penyebab else "")
                        for r in got.itertuples())
        lines.append(f"| {asv} | {name} | {origin} | {acc} | {subs} | {expect} | {res} |")
    lines += [
        "",
        f"**Ringkasan keputusan:** {report.summary_sentence()}",
        "",
        "## Perbedaan dari harapan rencana dan alasannya",
        "",
        "- *Telmatherina celebensis* dilaporkan sebagai genus *Telmatherina*: kedua sekuensnya di GenBank",
        "  tidak punya `specimen_voucher`, jadi belum tervalidasi. Peluang belum di kamus untuk *Telmatherina*",
        "  di Kompleks Malili = 1,00 (bukan 0,89, yang mengandaikan sekuens itu tervalidasi).",
        "- Sapu-sapu dilaporkan sebagai genus *Pterygoplichthys* (penyebab marker): amplikon MiFish",
        "  *P. pardalis* identik dengan *P. anisitsi* dan *P. disjunctivus* di referensi.",
        "- Karper di ST1 terkena batas D karena muncul di kontrol batch B1. Karper berlabel invasif, dan",
        "  matriks keputusan PRD menetapkan nilai D dengan label L3 sebagai **wajib verifikasi** (ikan invasif",
        "  C-D tidak dijadikan dasar pemberantasan sebelum dicek). Cabang **jangan dipakai** ditunjukkan oleh",
        "  sidat (asv10): ikan asli tanpa label L3, bacaan di bawah 10.",
        "",
        "## Membuat ulang",
        "",
        "```bash",
        ".venv/Scripts/python scripts/make_demo.py",
        "```",
        "",
        f"Sidik jari laporan demo: `sha256:{report.fingerprint}`",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    build_files(random.Random(SEED))
    report = run(OUT / "bacaan.csv", OUT / "metadata.csv", OUT / "taksonomi.csv", OUT / "asv.fasta")
    assert report.simulation, "data demo harus terdeteksi sebagai SIMULASI"
    write_outputs(report, OUT / "hasil")
    write_readme(report)
    print(report.summary_sentence())
    print(report.claims[["claim_id", "taxon_dilaporkan", "tingkat", "nilai", "label_L3", "penyebab", "keputusan"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
