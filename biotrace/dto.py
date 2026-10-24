"""Kontrak data biotrace.report.v1: satu objek JSON untuk dashboard, mode statis, dan uji.

Semua nilai berasal dari Report hasil pipeline.run(); modul ini hanya menyusun ulang dan
menghitung agregasi tampilan (jumlah per penyebab, kelompok peta celah, deskripsi berkas).
Tidak ada aturan penilaian di sini.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from .audit import site_info
from .config import grade_for_score
from .decision import origin_parts
from .io import CONTROL_TYPES
from .pipeline import DECISIONS, Report
from .report import CATEGORY_ACTION, barcode_priority, gap_map
from .taxonomy import genus_of, species_key
from .texts import frac

SCHEMA = "biotrace.report.v1"
CAUSES = (
    ("referensi", "Referensi", "kerabat belum ada di kamus"),
    ("marker", "Marker", "spesies tak terbedakan di 12S"),
    ("sampel", "Sampel", "kontrol, replikat, bacaan sedikit"),
    ("lokasi", "Lokasi", "tidak tercatat di perairan ini"),
)
# kunci, judul, skor maksimum, awalan kolom alasan di tabel klaim
LAYERS = (
    ("penamaan", "Penamaan", None, "alasan_penamaan"),
    ("L1", "L1 kamus DNA", 2, "alasan_L1"),
    ("L2", "L2 lokasi", 1, "alasan_L2"),
    ("L4", "L4 sinyal lab", 2, "alasan_L4"),
)
EXPORT_FILES = {"csv": "klaim.csv", "pdf": "laporan.pdf", "barcode": "prioritas_barcode.csv",
                "manifest": "manifest.json"}


def _num(x) -> float | None:
    if x is None or x == "":
        return None
    v = float(x)
    return None if math.isnan(v) else v


def _split(s) -> list[str]:
    return [x for x in str(s or "").split("; ") if x]


# ---- meta, berkas, informasi hilang ---------------------------------------------------------
def _meta(report: Report, processed_at: str | None) -> dict:
    project, ref, rules, c = report.project, report.reference, report.rules, report.claims
    samples = project.samples
    sites = sorted(set(samples["site_id"]))
    lakes = sorted({x for x in samples.get("lake", pd.Series(dtype=str)) if x})
    lake = lakes[0] if len(lakes) == 1 else ""
    reps = sorted(set(site_info(project)["n_replikat"]))
    area = f"Danau {lake}" if lake else ref.region
    return {
        "proyek": report.project_name or (f"Pemantauan {area}"),
        "judul": f"{area}, {', '.join(sites)}" if len(sites) <= 4 else f"{area}, {len(sites)} stasiun",
        "simulasi": report.simulation,
        "mode": report.manifest.get("mode", "proyek"),
        "marker": sorted({m for m in project.metadata.get("marker", pd.Series(dtype=str)) if m}),
        "jumlah_stasiun": len(sites),
        "replikat_per_stasiun": (str(reps[0]) if len(reps) == 1 else f"{reps[0]}–{reps[-1]}") if reps else "-",
        "jumlah_sampel": int(len(samples)),
        "jumlah_kontrol": int(project.metadata["sample_type"].isin(CONTROL_TYPES).sum()),
        "jumlah_klaim": int(len(c)),
        "jumlah_asv": int(c["asv_id"].nunique()) if len(c) else 0,
        "diproses": processed_at,
        "durasi_detik": round(report.seconds, 2),
        "referensi": {"label": ref.label, "nama": ref.meta.get("nama", "ref12S"), "versi": ref.version,
                      "jenis": ref.kind, "wilayah": ref.region},
        "aturan": {"versi": rules.version, "label": rules.label},
        "aplikasi": report.manifest.get("aplikasi", ""),
        "sidik_jari": f"sha256:{report.fingerprint}",
        "kalibrasi_galat": report.manifest.get("kalibrasi_galat", ""),
        "batas_interpretasi": dict(rules["interpretation_limit"]),
    }


def _file_description(f, project) -> str:
    reads, meta = project.reads, project.metadata
    if f.role == "bacaan":
        fmt = "lebar" if project.reads_were_wide else "panjang"
        return f"tabel bacaan, format {fmt}, {reads['asv_id'].nunique()} ASV × {reads['sample_id'].nunique()} sampel"
    if f.role == "metadata":
        n_ctrl = int(meta["sample_type"].isin(CONTROL_TYPES).sum())
        return f"{len(project.samples)} sampel, {n_ctrl} kontrol negatif"
    if f.role == "taksonomi":
        n = len(project.taxonomy) if project.taxonomy is not None else 0
        return f"taksonomi dari lab, {n} ASV"
    if f.role == "fasta":
        return f"{len(project.sequences or {})} urutan ASV"
    return f.role


def _files(report: Report) -> list[dict]:
    order = {"bacaan": 0, "taksonomi": 1, "metadata": 2, "fasta": 3}
    files = sorted(report.project.files, key=lambda f: (order.get(f.role, 9), f.name))
    return [{"nama": f.name, "peran": f.role, "deskripsi": _file_description(f, report.project),
             "sha256": f.sha256} for f in files]


def _issues(report: Report) -> list[dict]:
    return [{"berkas": i.berkas, "masalah": i.masalah, "dampak": i.dampak, "tingkat": i.tingkat}
            for i in sorted(set(report.project.issues))]


# ---- klaim dan Evidence Card ------------------------------------------------------------------
def _claim_row(r: dict) -> dict:
    return {
        "id": r["claim_id"], "asv": r["asv_id"], "stasiun": r["site_id"], "danau": r["danau"],
        "nama_lab": r["taxon_lab"], "dilaporkan": r["taxon_dilaporkan"], "tingkat": r["tingkat"],
        "kemiripan": _num(r["kemiripan_terbaik"]), "nilai": r["nilai"], "skor": int(r["total"]),
        "batas_D": r["batas_diterapkan"], "penyebab": _split(r["penyebab"]),
        "peluang_belum_di_kamus": _num(r["peluang_belum_di_kamus"]),
        "label_L3": _split(r["label_L3"]), "keputusan": r["keputusan"],
    }


def _card(r: dict, report: Report, facilities: dict[str, str]) -> dict:
    ref, rules = report.reference, report.rules
    unknown = r["tingkat"] == "tidak dikenal"
    genus = genus_of(r["taxon_dilaporkan"]) if r["tingkat"] in ("spesies", "genus") else ""
    scope = rules["reference"].get("completeness_scope", "wilayah")
    comp = ref.completeness_for(genus, r["danau"] or None, scope) if genus else None
    if comp:
        note = f"{comp['n'] - comp['r']} dari {comp['n']} spesies {genus} di {comp['wilayah']} belum punya referensi tervalidasi"
    elif unknown:
        note = "Tidak dihitung: nama tidak dikenal"
    elif r["tingkat"] == "famili":
        note = "Tidak dihitung untuk tingkat famili"
    else:
        note = f"Tidak dihitung: {genus} tidak ada di checklist wilayah"
    p = _num(r["peluang_belum_di_kamus"])
    total = int(r["total"])
    score = f"{total}/5"
    if r["batas_diterapkan"] and grade_for_score(rules, total) != "D":
        score += " → D"
    reasons = []
    for key, title, maks, col in LAYERS:
        skor = None if maks is None or (key == "L2" and unknown) else int(r[f"skor_{key}"])
        reasons.append({"lapisan": key, "judul": title, "skor": skor, "maks": maks,
                        "id": r[f"{col}_id"], "en": r[f"{col}_en"]})
    return {
        "keluaran": {"tingkat": r["tingkat"], "nilai": r["nilai"], "skor": score, "galat_nilai": r["galat_nilai"],
                     "peluang": "tidak dihitung" if p is None else frac(p), "catatan_peluang": note,
                     "penyebab": _split(r["penyebab"])},
        "alasan": reasons,
        "tindak_lanjut": r["tindak_lanjut"],
        "asal_usul": origin_parts(r, ref, facilities.get(r["site_id"], "")),
        "batas_D": r["batas_diterapkan"],
        "kecocokan_dalam_0,5%": _split(r["kecocokan_dalam_0,5%"]),
    }


# ---- peta celah -------------------------------------------------------------------------------
def _covered(name: str, pool: set[str], alias: pd.DataFrame) -> bool:
    """Spesies tercakup bila kuncinya ada di pool; nama alias (louhan hibrida) lewat spesies induknya."""
    key, resolved = species_key(name)
    if resolved:
        return key in pool
    parents = alias.loc[(alias["nama_alias"] == name) & (alias["tingkat"] == "spesies"), "nama_induk"]
    return any(species_key(p)[0] in pool for p in parents)


def _gaps(report: Report) -> dict:
    ref = report.reference
    tax = ref.taxonomy
    validated = set(tax.loc[tax["status_validasi"] == "tervalidasi", "spesies_kunci"])
    any_seq = set(tax["spesies_kunci"])
    cl = ref.checklist.drop_duplicates("spesies")
    endemic = cl["status"] == "endemik"
    tel = cl["famili"] == "Telmatherinidae"
    groups = []
    for label, mask, hint in (
        ("Telmatherinidae endemik", endemic & tel, None),
        ("Endemik lain", endemic & ~tel, "genera"),
        ("Ikan introduksi", cl["status"] == "introduksi", None),
        ("Ikan asli lain", cl["status"] == "asli", None),
    ):
        sub = cl[mask]
        if sub.empty:
            continue
        names = list(sub["spesies"])
        all_binomial = all(species_key(n)[1] for n in names)
        petunjuk = (", ".join(sorted({genus_of(n) for n in names})) if hint == "genera"
                    else f"{len(names)} spesies" if all_binomial
                    else f"{len(names)} takson, louhan lewat spesies induk")
        groups.append({"label": label, "petunjuk": petunjuk, "total": len(names),
                       "ada_sekuens": sum(_covered(n, any_seq, ref.alias) for n in names),
                       "tervalidasi": sum(_covered(n, validated, ref.alias) for n in names)})
    end_names = list(cl.loc[endemic, "spesies"])
    n_end = len(end_names)
    n_seq = sum(_covered(n, any_seq, ref.alias) for n in end_names)
    n_val = sum(_covered(n, validated, ref.alias) for n in end_names)
    per_genus = [{"wilayah": g["wilayah"], "genus": g["genus"], "n": int(g["n_checklist"]), "r": int(g["r_tervalidasi"]),
                  "p": float(g["p_belum_di_kamus"]), "tanpa_referensi": _split(g["spesies_tanpa_referensi"])}
                 for g in gap_map(report).to_dict("records")]
    return {
        "judul": f"{n_seq} dari {n_end} ikan endemik {ref.region} punya referensi 12S; {n_val} tervalidasi.",
        "kelompok": groups,
        "per_genus": per_genus,
        "sumber": f"{ref.meta.get('nama', 'ref12S')} {ref.version}: " + "; ".join(ref.meta.get("sumber", []))
                  + (f". {ref.meta['catatan']}" if ref.meta.get("catatan") else ""),
    }


def _scientific_names(report: Report, priority: list[dict]) -> list[str]:
    c = report.claims
    names = set(c["taxon_lab"]) | set(c["taxon_dilaporkan"]) | set(report.reference.checklist["spesies"])
    for near in c["kecocokan_dalam_0,5%"]:
        names |= set(_split(near))
    names |= {p["target"] for p in priority}
    names = {n for n in names if n and n[0].isupper() and not n.startswith("ASV")}
    names |= {genus_of(n) for n in names}
    return sorted(names)


# ---- objek lengkap ----------------------------------------------------------------------------
def report_to_dto(report: Report, processed_at: str | None = None) -> dict:
    records = report.claims.to_dict("records")
    facilities = site_info(report.project).set_index("site_id")["fasilitas_sekitar"].to_dict()
    claims = [_claim_row(r) for r in records]
    prio = barcode_priority(report)
    priority = [{"urutan": i + 1, "target": p["target"], "jenis": p["jenis"], "danau": p["danau"],
                 "status_L3": p["status_L3"], "alasan": p["alasan"], "klaim": int(p["jumlah_klaim_terdampak"])}
                for i, p in enumerate(prio.to_dict("records"))]
    summary = report.summary
    return {
        "schema": SCHEMA,
        "meta": _meta(report, processed_at),
        "ringkasan": {
            "kalimat": report.summary_sentence(),
            "jumlah": summary,
            "tindak_lanjut": {d: CATEGORY_ACTION[d] for d in DECISIONS},
            "tidak_dikenal_ke_barcode": sum(1 for p in priority if p["jenis"] == "tidak dikenal"),
        },
        "penyebab": [{"kode": k, "label": label, "petunjuk": hint,
                      "jumlah": sum(1 for c in claims if k in c["penyebab"])} for k, label, hint in CAUSES],
        "berkas": _files(report),
        "informasi_hilang": _issues(report),
        "klaim": claims,
        "kartu": {r["claim_id"]: _card(r, report, facilities) for r in records},
        "celah": _gaps(report),
        "prioritas_barcode": priority,
        "nama_ilmiah": _scientific_names(report, priority),
        "ekspor": dict(EXPORT_FILES),
    }


def write_json(dto: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dto, ensure_ascii=False, indent=2, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    return path
