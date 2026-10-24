"""Jalankan mesin BioTrace dari input lab sampai tabel klaim, keputusan, dan manifest."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd

from . import texts
from .audit import audit_claims, site_info
from .config import Rules, load_rules
from .decision import apply_decisions
from .io import Issue, ProjectInput, load_project
from .naming import Naming, name_project
from .provenance import build_manifest, fingerprint
from .reference import Reference, load_reference
from .scoring import grade_claims

DECISIONS = ("aman dilaporkan", "dengan catatan", "wajib verifikasi", "jangan dipakai")

# skema keluaran per klaim (PRD v2, "Keluaran per klaim"), ditambah kolom penjelas
OUTPUT_COLUMNS = [
    "claim_id", "asv_id", "site_id", "danau", "taxon_lab", "taxon_dilaporkan", "tingkat",
    "kecocokan_dalam_0,5%", "kemiripan_terbaik", "selisih_spesies_lain",
    "skor_L1", "skor_L2", "skor_L4", "label_L3", "total", "nilai", "batas_diterapkan", "galat_nilai",
    "peluang_belum_di_kamus", "penyebab", "keputusan", "tindak_lanjut", "asal_usul",
    "alasan_penamaan_id", "alasan_penamaan_en", "alasan_L1_id", "alasan_L1_en",
    "alasan_L2_id", "alasan_L2_en", "alasan_L4_id", "alasan_L4_en",
    "replikat_positif", "replikat_total", "total_bacaan", "status_kontrol",
    "sumber_penamaan", "catatan_penamaan", "jejak",
]


class ReferenceSeparationError(ValueError):
    """Referensi uji luar dipakai pada proyek Indonesia."""


@dataclass
class Report:
    project: ProjectInput
    reference: Reference
    rules: Rules
    namings: dict[str, Naming]
    claims: pd.DataFrame
    manifest: dict
    fingerprint: str
    seconds: float
    simulation: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> dict:
        counts = self.claims["keputusan"].value_counts().to_dict() if len(self.claims) else {}
        unknown = int((self.claims["tingkat"] == "tidak dikenal").sum()) if len(self.claims) else 0
        return {"n": len(self.claims), **{d: int(counts.get(d, 0)) for d in DECISIONS}, "tidak dikenal": unknown}

    def summary_sentence(self) -> str:
        s = self.summary
        return (f"Dari {s['n']} klaim, {s['aman dilaporkan']} aman dilaporkan, {s['dengan catatan']} dengan catatan, "
                f"{s['wajib verifikasi']} wajib verifikasi, {s['jangan dipakai']} jangan dipakai; "
                f"{s['tidak dikenal']} tidak dikenal.")


def is_simulation(project: ProjectInput) -> bool:
    """Data demo membawa kolom label_data = SIMULASI di setiap baris metadata."""
    meta = project.metadata
    return "label_data" in meta.columns and meta["label_data"].astype(str).str.upper().eq("SIMULASI").any()


def naming_reason(row: dict, lang: str) -> str:
    if row["tingkat"] == "tidak dikenal":
        return texts.unknown_reason(lang)
    n_species = len([x for x in str(row["kecocokan_dalam_0,5%"]).split("; ") if x])
    return texts.naming_reason(row["taxon_dilaporkan"], max(n_species, 1), lang)


def trace(manifest: dict) -> str:
    inputs = "; ".join(f"{k} {v[:19]}" for k, v in manifest["input"].items())
    return f"input: {inputs} | referensi: {manifest.get('referensi', '-')} | aturan: {manifest.get('aturan', '-')}"


def finalize_claims(claims: pd.DataFrame, manifest: dict) -> pd.DataFrame:
    if claims.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    out = claims.copy()
    out["alasan_penamaan_id"] = [naming_reason(r, "id") for r in out.to_dict("records")]
    out["alasan_penamaan_en"] = [naming_reason(r, "en") for r in out.to_dict("records")]
    out["penyebab"] = out["penyebab"].map(lambda c: "; ".join(c))
    out["jejak"] = trace(manifest)
    out["kemiripan_terbaik"] = out["kemiripan_terbaik"].map(lambda x: None if x is None or pd.isna(x) else round(float(x), 2))
    out["selisih_spesies_lain"] = out["selisih_spesies_lain"].map(lambda x: None if x is None or pd.isna(x) else round(float(x), 2))
    out["peluang_belum_di_kamus"] = out["peluang_belum_di_kamus"].map(lambda x: None if x is None else round(float(x), 2))
    return out[OUTPUT_COLUMNS].sort_values("claim_id").reset_index(drop=True)


def run(reads, metadata, taxonomy=None, fasta=None, rules: Rules | None = None,
        reference: Reference | None = None, mode: str = "proyek", threads: int = 1,
        simulation: bool = False) -> Report:
    """mode='proyek' untuk data Indonesia; mode='uji' hanya untuk referensi uji luar (F27)."""
    start = time.perf_counter()
    rules = rules or load_rules()
    reference = reference or load_reference()
    if reference.kind != "indonesia" and mode != "uji":
        raise ReferenceSeparationError(
            f"Referensi {reference.label} berjenis '{reference.kind}' hanya untuk mode uji; "
            "tidak boleh dipakai menamai ikan Indonesia")
    project = load_project(reads, metadata, taxonomy, fasta, rules=rules, reference_lakes=reference.lakes)
    if is_simulation(project):
        simulation = True
        project.issues.append(Issue("metadata", "data berlabel SIMULASI", "laporan ditandai SIMULASI", "info"))
    namings, notes = name_project(project, reference, rules, threads=threads)
    for note in notes:
        project.issues.append(Issue("referensi", note, ""))
    if mode == "uji":
        project.issues.append(Issue("referensi", f"mode uji dengan referensi luar ({reference.region})",
                                    "hasil hanya untuk menguji logika mesin", "info"))
    if rules["l4"].get("tag_jump_status") == "belum dikalibrasi":
        project.issues.append(Issue("aturan", "tag_jump_fraction belum dikalibrasi",
                                    "ambang data nyasar memakai nilai usulan 0,001", "info"))
    claims = audit_claims(project, namings, reference, rules)
    if not claims.empty:
        claims = grade_claims(claims, rules)
        facilities = site_info(project).set_index("site_id")["fasilitas_sekitar"].to_dict()
        claims = apply_decisions(claims, reference, rules, facilities)
    manifest = build_manifest(project, reference, rules)
    manifest["mode"] = mode
    if simulation:
        manifest["label_data"] = "SIMULASI"
    table = finalize_claims(claims, manifest)
    fp = fingerprint(manifest, table)
    return Report(project=project, reference=reference, rules=rules, namings=namings, claims=table,
                  manifest=manifest, fingerprint=fp, seconds=time.perf_counter() - start,
                  simulation=simulation, notes=notes)
