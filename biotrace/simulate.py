"""F26-F27: uji tanpa-satu-spesies pada referensi aktif dan mode uji dengan referensi luar.

Uji tanpa-satu-spesies: untuk setiap spesies, sembunyikan semua sekuensnya, cocokkan
amplikon MiFish-nya ke sisa referensi, lalu bandingkan ambang 97% (nama teratas) dengan
aturan BioTrace. Cara cepat sesuai rencana: BLAST semua-lawan-semua sekali dengan
-max_target_seqs 500, lalu buang kecocokan ke spesies yang sedang disembunyikan.
"""

from __future__ import annotations

import copy
import random
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import find_blast_tool, grade_for_score
from .naming import Hit, name_asv, run_blast
from .reference import write_fasta
from .taxonomy import genus_of, species_key

MIFISH_F = "GTCGGTAAAACTCGTGCCAGC"
MIFISH_R_RC = "CAAACTGGGATTAGATACCCCACTATG"   # komplemen balik MiFish-U-R
BASES = "ACGT"


def _best_window(seq: str, primer: str, start: int = 0, end: int | None = None) -> tuple[int, int]:
    """Posisi dengan jumlah salah-pasang terkecil (jarak Hamming) untuk primer di seq[start:end]."""
    end = len(seq) - len(primer) if end is None else min(end, len(seq) - len(primer))
    best_pos, best_mm = -1, len(primer) + 1
    for i in range(max(0, start), end + 1):
        mm = 0
        for a, b in zip(seq[i:i + len(primer)], primer):
            if a != b:
                mm += 1
                if mm >= best_mm:
                    break
        if mm < best_mm:
            best_pos, best_mm = i, mm
    return best_pos, best_mm


def extract_mifish(seq: str, max_mm_f: int = 4, max_mm_r: int = 5,
                   min_len: int = 140, max_len: int = 260) -> str | None:
    """Ambil sisipan amplikon MiFish-U (tanpa primer) dari sekuens 12S; None bila primer tidak ketemu."""
    s = seq.upper()
    pf, mf = _best_window(s, MIFISH_F)
    if pf < 0 or mf > max_mm_f:
        return None
    ins_start = pf + len(MIFISH_F)
    pr, mr = _best_window(s, MIFISH_R_RC, ins_start + min_len, ins_start + max_len)
    if pr < 0 or mr > max_mm_r:
        return None
    return s[ins_start:pr]


def as_amplicon(seq: str, min_len: int = 140, max_len: int = 260) -> str | None:
    """Amplikon MiFish: hasil ekstraksi primer, atau sekuens pendek yang memang sisipan MiFish."""
    amp = extract_mifish(seq, min_len=min_len, max_len=max_len)
    if amp:
        return amp
    s = seq.upper()
    return s if min_len <= len(s) <= max_len else None


def mutate(seq: str, n_subs: int, rng: random.Random) -> str:
    """Substitusi acak pada posisi berbeda, berbenih (untuk skenario SIMULASI)."""
    s = list(seq)
    for i in sorted(rng.sample(range(len(s)), n_subs)):
        s[i] = rng.choice([b for b in BASES if b != s[i]])
    return "".join(s)


# ---- uji tanpa-satu-spesies (F26) -----------------------------------------------------------
@dataclass
class RefRecord:
    accession: str
    species: str
    genus: str
    family: str
    validated: bool = True
    recorded: str = "ya"

    @property
    def key(self) -> tuple[str, bool]:
        return species_key(self.species)


def all_vs_all(queries: dict[str, str], db_seqs: dict[str, str], rules: dict, threads: int = 2) -> pd.DataFrame:
    exe = find_blast_tool("makeblastdb")
    if exe is None or find_blast_tool("blastn") is None:
        raise RuntimeError("BLAST+ tidak ditemukan")
    r = copy.deepcopy(rules)
    r["blast"]["max_target_seqs"] = 500
    with tempfile.TemporaryDirectory() as tmp:
        fasta = Path(tmp) / "db.fasta"
        write_fasta(db_seqs, fasta)
        subprocess.run([exe, "-in", str(fasta), "-dbtype", "nucl", "-parse_seqids", "-out", str(Path(tmp) / "db")],
                       check=True, capture_output=True, text=True)
        return run_blast(queries, Path(tmp) / "db", r, threads=threads)


def leave_one_out(queries: dict[str, str], query_species: dict[str, str], hits: pd.DataFrame,
                  records: dict[str, RefRecord], rules: dict, logic_only: bool = False) -> pd.DataFrame:
    """Satu baris per kueri: ambang 97% vs aturan BioTrace setelah spesies kueri disembunyikan."""
    by_query = {q: g for q, g in hits.groupby("qseqid", sort=False)}
    rows = []
    l1 = rules["l1"]
    for qid in sorted(queries):
        true_sp = query_species[qid]
        true_genus = genus_of(true_sp)
        g = by_query.get(qid)
        remaining: list[Hit] = []
        if g is not None:
            for row in g.itertuples(index=False):
                rec = records.get(row.sseqid)
                if rec is None:
                    continue
                key, resolved = rec.key
                if key == true_sp or true_sp in rec.species:   # termasuk hibrida dengan induk spesies ini
                    continue
                remaining.append(Hit(accession=rec.accession, species=rec.species, species_key=key,
                                     genus=rec.genus, family=rec.family, pident=float(row.pident),
                                     bitscore=float(row.bitscore), resolved=resolved,
                                     validated=True if logic_only else rec.validated,
                                     recorded="ya" if logic_only else rec.recorded))
        n = name_asv(qid, remaining, rules)
        best = n.best_identity
        # L1 tanpa potongan kelengkapan; nilai dengan asumsi L2 = 1 dan L4 = 2 (batas atas)
        score1 = 0
        if n.rank != "tidak dikenal" and best is not None:
            gap = n.gap or 0.0
            if best >= l1["score2"]["identity"] and gap >= l1["score2"]["gap"]:
                score1 = 2
            elif best >= l1["score1"]["identity"] and gap >= l1["score1"]["gap"]:
                score1 = 1
        grade = grade_for_score(rules, score1 + 3) if n.rank != "tidak dikenal" else "-"
        if n.rank == "spesies":
            wrong = True
        elif n.rank == "genus":
            wrong = n.taxon != true_genus
        elif n.rank == "famili":
            fam = next((r.family for r in records.values() if r.key[0] == true_sp), "")
            wrong = bool(fam) and n.taxon != fam
        else:
            wrong = False
        rows.append({
            "kueri": qid, "spesies_asli": true_sp, "genus_asli": true_genus,
            "kemiripan_tersisa": best, "nama_teratas_tersisa": n.taxon_lab,
            "ambang97_memberi_nama": best is not None and best >= 97.0,
            "biotrace_nama": n.taxon, "biotrace_tingkat": n.rank, "biotrace_penyebab": "; ".join(n.causes),
            "skor_L1": score1, "nilai": grade, "keliru": wrong,
            "keliru_lolos_aman": n.rank == "spesies" and grade in ("A", "B"),
        })
    return pd.DataFrame(rows)


def summarize_loo(df: pd.DataFrame, reference: str, rule: str) -> dict:
    n = len(df)
    pct = lambda x: round(100.0 * x / n, 1) if n else None  # noqa: E731
    return {
        "referensi": reference, "aturan_biotrace": rule, "n_spesies": df["spesies_asli"].nunique(), "n_kueri": n,
        "ambang97_nama_keliru_lolos_pct": pct(int(df["ambang97_memberi_nama"].sum())),
        "biotrace_nama_keliru_lolos_pct": pct(int(df["keliru_lolos_aman"].sum())),
        "biotrace_nama_keliru_nilai_A_pct": pct(int(((df["biotrace_tingkat"] == "spesies") & (df["nilai"] == "A")).sum())),
        "biotrace_nama_spesies_keliru_pct": pct(int((df["biotrace_tingkat"] == "spesies").sum())),
        "biotrace_turun_genus_atau_tidak_dikenal_pct": pct(int((df["biotrace_tingkat"] != "spesies").sum())),
        "biotrace_tidak_dikenal_pct": pct(int((df["biotrace_tingkat"] == "tidak dikenal").sum())),
    }


def error_by_grade(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for grade in ("A", "B", "C", "D"):
        g = df[df["nilai"] == grade]
        rows.append({"nilai": grade, "n": len(g), "keliru": int(g["keliru"].sum()),
                     "galat_pct": round(100.0 * g["keliru"].mean(), 1) if len(g) else None})
    return pd.DataFrame(rows)


# ---- mode uji Lake St. Pierre (F27, jalur kedua) -------------------------------------------
def detection_project(edna: pd.DataFrame, codes: pd.DataFrame, amplicons: dict[str, str],
                      out_dir: Path) -> dict[str, Path]:
    """Tabel deteksi per spesies -> proyek BioTrace: ASV semu = amplikon referensi spesies itu.

    Ronde sampling dipakai sebagai replikat; tabel ini tidak memuat kontrol negatif.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    det = edna[edna["count"] > 0].merge(codes, on="CODE_BDRSI", how="left")
    det["spesies"] = det["Genus"] + " " + det["Species"]
    det = det[det["spesies"].isin(amplicons)]
    det["asv_id"] = "lsp_" + det["CODE_BDRSI"]
    det["sample_id"] = det["site"] + "_" + det["year"].astype(str) + "_" + det["round"]
    reads = det[["asv_id", "sample_id", "count"]].rename(columns={"count": "reads"}).sort_values(["asv_id", "sample_id"])
    reads.to_csv(out_dir / "bacaan.csv", index=False, lineterminator="\n")
    samples = edna[["site", "year", "round", "region"]].drop_duplicates()
    meta = pd.DataFrame({
        "sample_id": samples["site"] + "_" + samples["year"].astype(str) + "_" + samples["round"],
        "site_id": samples["site"] + "_" + samples["year"].astype(str),
        "latitude": "", "longitude": "", "collection_date": samples["year"].astype(str),
        "sample_type": "sampel", "replicate": samples["round"], "extraction_batch": "",
        "marker": "12S MiFish-U", "lake": "Lac Saint-Pierre", "region": samples["region"],
    }).sort_values("sample_id")
    meta.to_csv(out_dir / "metadata.csv", index=False, lineterminator="\n")
    seqs = {f"lsp_{c}": amplicons[sp] for c, sp in zip(det["CODE_BDRSI"], det["spesies"])}
    write_fasta(seqs, out_dir / "asv.fasta")
    return {"reads": out_dir / "bacaan.csv", "metadata": out_dir / "metadata.csv", "fasta": out_dir / "asv.fasta"}


def precision_vs_electrofishing(claims: pd.DataFrame, codes: pd.DataFrame, elec: pd.DataFrame,
                                elec_env: pd.DataFrame, edna: pd.DataFrame) -> dict:
    """Presisi klaim spesies bernilai A-B terhadap tangkapan electrofishing per sektor dan tahun."""
    caught = elec[elec["count"] > 0].merge(elec_env[["station", "year", "region"]], on=["station", "year"])
    caught = caught.merge(codes, on="CODE_BDRSI")
    caught["spesies"] = caught["Genus"] + " " + caught["Species"]
    caught_set = set(zip(caught["region"], caught["year"], caught["spesies"]))
    sector = edna[["site", "year", "region"]].drop_duplicates()
    sector["site_id"] = sector["site"] + "_" + sector["year"].astype(str)
    c = claims.merge(sector[["site_id", "year", "region"]], on="site_id", how="left")
    sp = c[(c["tingkat"] == "spesies") & c["region"].isin(set(caught["region"]))]

    def precision(df: pd.DataFrame) -> tuple[int, int, float | None]:
        ok = sum((r, y, t) in caught_set for r, y, t in zip(df["region"], df["year"], df["taxon_dilaporkan"]))
        return len(df), int(ok), round(100.0 * ok / len(df), 1) if len(df) else None

    n_ab, ok_ab, p_ab = precision(sp[sp["nilai"].isin(["A", "B"])])
    n_all, ok_all, p_all = precision(sp)
    return {"klaim_AB_spesies_di_sektor_electrofishing": n_ab, "cocok_electrofishing": ok_ab, "presisi_AB_pct": p_ab,
            "klaim_spesies_semua_nilai": n_all, "cocok_electrofishing_semua_nilai": ok_all,
            "presisi_spesies_semua_nilai_pct": p_all}
