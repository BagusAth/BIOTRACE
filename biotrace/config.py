"""Lokasi berkas proyek, pemuat aturan berversi, dan pencari BLAST+."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RULES_DIR = ROOT / "rules"
TOOLS_DIR = ROOT / "tools"
DEFAULT_RULES = RULES_DIR / "rules_v0.1.yaml"

REQUIRED_RULE_SECTIONS = (
    "version", "reference", "blast", "naming", "l1", "l2", "l4",
    "grades", "caps", "causes", "decision", "input", "interpretation_limit",
)


class Rules(dict):
    """Dict aturan yang juga menyimpan path dan SHA-256 berkas asalnya."""

    path: Path
    sha256: str

    @property
    def version(self) -> str:
        return str(self["version"])

    @property
    def label(self) -> str:
        return f"{self.path.name} (sha256:{self.sha256})"


def sha256_file(path: str | os.PathLike, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_rules(path: str | os.PathLike | None = None) -> Rules:
    """Muat berkas aturan dan pastikan semua bagian wajib ada."""
    p = Path(path) if path else DEFAULT_RULES
    with open(p, encoding="utf-8") as fh:
        data: Any = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Berkas aturan {p} bukan pemetaan YAML")
    missing = [k for k in REQUIRED_RULE_SECTIONS if k not in data]
    if missing:
        raise ValueError(f"Berkas aturan {p} tidak memuat bagian: {', '.join(missing)}")
    _check_grades(data["grades"])
    rules = Rules(data)
    rules.path = p
    rules.sha256 = sha256_file(p)
    return rules


def _check_grades(grades: dict) -> None:
    covered = sorted(s for scores in grades.values() for s in scores)
    if covered != list(range(6)):
        raise ValueError(f"Peta nilai harus mencakup skor 0-5 tepat sekali, didapat {covered}")


def grade_for_score(rules: dict, score: int) -> str:
    for grade, scores in rules["grades"].items():
        if score in scores:
            return grade
    raise ValueError(f"Skor {score} tidak ada di peta nilai")


def find_blast_tool(name: str) -> str | None:
    """Cari blastn/makeblastdb: env BIOTRACE_BLAST_BIN, lalu tools/, lalu PATH."""
    exe = name + (".exe" if os.name == "nt" else "")
    env_dir = os.environ.get("BIOTRACE_BLAST_BIN")
    candidates = []
    if env_dir:
        candidates.append(Path(env_dir) / exe)
    candidates += sorted(TOOLS_DIR.glob(f"ncbi-blast-*/bin/{exe}"), reverse=True)
    for c in candidates:
        if c.is_file():
            return str(c)
    return shutil.which(name)
