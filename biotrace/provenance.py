"""F4: sidik jari file input dan manifest laporan.

Sidik jari dihitung dari isi: hash input, versi referensi dan tabel acuan, versi aturan,
versi aplikasi, informasi yang hilang, dan tabel klaim. Waktu proses boleh dicetak di
laporan, tetapi tidak ikut di-hash, supaya input yang sama selalu menghasilkan sidik jari
yang sama (US7).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from . import APP_NAME, __version__
from .config import ROOT, sha256_file


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def build_manifest(project, reference=None, rules=None) -> dict:
    manifest = {
        "input": {f.name: f"sha256:{f.sha256}" for f in sorted(project.files, key=lambda f: (f.role, f.name))},
        "peran_input": {f.name: f.role for f in sorted(project.files, key=lambda f: (f.role, f.name))},
        "aplikasi": f"{APP_NAME} {__version__}",
        "informasi_hilang": project.missing_info,
    }
    if reference is not None:
        manifest["referensi"] = reference.label
        manifest["jenis_referensi"] = reference.kind
        manifest["tabel_acuan"] = {k: f"sha256:{v}" for k, v in sorted(reference.files.items())}
    if rules is not None:
        manifest["aturan"] = rules.label
        calib = rules.get("calibration", {}).get("error_by_grade_file")
        if calib and (ROOT / calib).exists():
            manifest["kalibrasi_galat"] = f"{calib} (sha256:{sha256_file(ROOT / calib)})"
    return manifest


def table_digest(df: pd.DataFrame | None) -> str:
    if df is None:
        return ""
    ordered = df.reindex(sorted(df.columns), axis=1)
    csv = ordered.to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(csv.encode("utf-8")).hexdigest()


def fingerprint(manifest: dict, claims: pd.DataFrame | None = None) -> str:
    payload = canonical_json({"manifest": manifest, "klaim": table_digest(claims)})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_manifest(path: str | Path, manifest: dict, claims: pd.DataFrame | None = None,
                   run_time: str | None = None) -> dict:
    """Tulis manifest laporan; waktu proses dicatat terpisah dan tidak di-hash."""
    doc = dict(manifest)
    doc["sidik_jari_laporan"] = f"sha256:{fingerprint(manifest, claims)}"
    if run_time:
        doc["waktu_proses_tidak_di_hash"] = run_time
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
    return doc
