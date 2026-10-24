"""F16-F19: skor total, nilai A-D dengan batas D, penyebab ketidakpastian, peluang belum di kamus."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import ROOT, grade_for_score

CAUSE_ORDER = ("referensi", "marker", "sampel", "lokasi")
GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}


def sort_causes(causes) -> list[str]:
    return [c for c in CAUSE_ORDER if c in set(causes)]


def load_error_by_grade(rules: dict) -> dict[str, str]:
    """F19 (P1): galat per nilai dari hasil uji tahap 6; bila belum ada, 'belum dikalibrasi'."""
    path = rules.get("calibration", {}).get("error_by_grade_file")
    if path and (ROOT / path).exists():
        df = pd.read_csv(ROOT / path, dtype=str, keep_default_na=False)
        return {r["nilai"]: r["galat"] for r in df.to_dict("records")}
    return {}


def claim_causes(row: dict, grade: str, rules: dict) -> list[str]:
    """Gabungkan penyebab dari penamaan dengan pemicu L4, L2, dan kelengkapan."""
    c = rules["causes"]
    causes = set(row["penyebab_penamaan"])
    if row["batas_D"] or row["replikat_positif"] <= c["sample_max_positive_replicates"]:
        causes.add("sampel")
    if row["l2_dinilai"] and row["skor_L2"] == 0:
        causes.add("lokasi")
    p = row["peluang_belum_di_kamus"]
    if p is not None and p >= c["reference_p_missing"]:
        causes.add("referensi")
    lo, hi = c["reference_identity_range"]
    pid = row["kemiripan_terbaik"]
    if pid is not None and not pd.isna(pid) and lo <= pid < hi:
        causes.add("referensi")
    if grade != "A" and not causes:
        # setiap klaim B-D wajib menyebut penyebab: ambil dari lapisan yang kehilangan skor
        l1 = rules["l1"]
        if row["skor_L1"] < 2:
            gap = row["selisih_spesies_lain"] or 0
            causes.add("marker" if pid is not None and pid >= l1["score2"]["identity"] and gap < l1["score2"]["gap"]
                       else "referensi")
        if row["skor_L4"] < 2:
            causes.add("sampel")
        if row["skor_L2"] == 0:
            causes.add("lokasi")
    return sort_causes(causes)


def grade_claims(claims: pd.DataFrame, rules: dict) -> pd.DataFrame:
    errors = load_error_by_grade(rules)
    out = claims.copy()
    totals, grades, caps, causes, pmiss, galat = [], [], [], [], [], []
    for row in out.to_dict("records"):
        total = int(row["skor_L1"] + row["skor_L2"] + row["skor_L4"])
        grade = grade_for_score(rules, total)
        cap = row["batas_D"]
        if cap and GRADE_RANK[grade] < GRADE_RANK["D"]:
            grade = "D"
        comp = row["kelengkapan"]
        p = comp["p"] if comp else None
        row["peluang_belum_di_kamus"] = p
        totals.append(total)
        grades.append(grade)
        caps.append(cap)
        pmiss.append(p)
        causes.append(claim_causes(row, grade, rules))
        galat.append(errors.get(grade, "belum dikalibrasi"))
    out["total"] = totals
    out["nilai"] = grades
    out["batas_diterapkan"] = caps
    out["peluang_belum_di_kamus"] = pmiss
    out["penyebab"] = causes
    out["galat_nilai"] = galat
    return out
