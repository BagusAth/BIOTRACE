"""F8-F11: cocokkan ASV ke referensi tervalidasi dan tentukan tingkat nama yang aman.

Prinsipnya "tidak dikenal lebih baik daripada menebak": nama spesies hanya keluar bila semua
kecocokan dalam selisih 0,5% adalah satu spesies, kemiripannya >= 98%, spesiesnya tercatat
di Indonesia, dan minimal satu sekuens pendukungnya tervalidasi.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import find_blast_tool
from .taxonomy import genus_of, species_key

BLAST_COLUMNS = ["qseqid", "sseqid", "pident", "length", "qcovs", "evalue", "bitscore"]


@dataclass(frozen=True)
class Hit:
    accession: str
    species: str
    species_key: str
    genus: str
    family: str
    pident: float
    bitscore: float = 0.0
    resolved: bool = True
    validated: bool = False
    recorded: str = "belum dicek"


@dataclass
class Naming:
    asv_id: str
    taxon_lab: str
    taxon: str
    rank: str                       # spesies | genus | famili | tidak dikenal
    causes: list[str]
    best_identity: float | None
    best_species: str
    gap: float | None
    near_species: list[str]
    family_hint: str = ""
    source: str = "referensi"       # referensi | database lab
    notes: list[str] = field(default_factory=list)
    hits: list[Hit] = field(default_factory=list)

    @property
    def genus(self) -> str:
        if self.rank in ("spesies", "genus"):
            return genus_of(self.taxon)
        return ""


# ---- BLAST ----------------------------------------------------------------------------
DB_TAGS = {"gb", "emb", "dbj", "ref", "lcl", "gnl"}


def accession_of(sseqid: str) -> str:
    """'gb|MN057622|', 'lcl|MN057622' atau 'MN057622.1' -> 'MN057622'."""
    parts = [p for p in str(sseqid).strip().split("|") if p]
    acc = parts[1] if len(parts) > 1 and parts[0].lower() in DB_TAGS else (parts[0] if parts else "")
    return acc.split(".")[0]


def run_blast(sequences: dict[str, str], db: Path, rules: dict, threads: int = 1,
              blastn: str | None = None) -> pd.DataFrame:
    exe = blastn or find_blast_tool("blastn")
    if exe is None:
        raise RuntimeError("blastn tidak ditemukan; jalankan scripts/setup_blast.py")
    b = rules["blast"]
    with tempfile.TemporaryDirectory() as tmp:
        q = Path(tmp) / "asv.fasta"
        out = Path(tmp) / "hits.tsv"
        with open(q, "w", encoding="utf-8", newline="\n") as fh:
            for asv in sorted(sequences):
                fh.write(f">{asv}\n{sequences[asv]}\n")
        cmd = [exe, "-query", str(q), "-db", str(db), "-outfmt", b["outfmt"],
               "-max_target_seqs", str(b["max_target_seqs"]), "-perc_identity", str(b["perc_identity"]),
               "-qcov_hsp_perc", str(b["qcov_hsp_perc"]), "-num_threads", str(threads), "-out", str(out)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        hits = pd.read_csv(out, sep="\t", names=BLAST_COLUMNS, dtype={"qseqid": str, "sseqid": str})
    hits["sseqid"] = hits["sseqid"].map(accession_of)
    # satu baris per pasangan kueri-subjek (HSP terbaik), urutan deterministik
    hits = hits.sort_values(["qseqid", "sseqid", "bitscore", "pident"], ascending=[True, True, False, False])
    hits = hits.drop_duplicates(["qseqid", "sseqid"])
    return hits.sort_values(["qseqid", "pident", "bitscore", "sseqid"],
                            ascending=[True, False, False, True]).reset_index(drop=True)


def hits_from_blast(blast: pd.DataFrame, reference) -> dict[str, list[Hit]]:
    out: dict[str, list[Hit]] = {}
    for row in blast.itertuples(index=False):
        info = reference.hit(row.sseqid)
        out.setdefault(row.qseqid, []).append(Hit(
            accession=info["aksesi"], species=info["spesies"], species_key=info["spesies_kunci"],
            genus=info["genus"], family=info["famili"], pident=float(row.pident),
            bitscore=float(row.bitscore), resolved=info["terselesaikan"], validated=info["tervalidasi"],
            recorded=info["tercatat_di_indonesia"],
        ))
    return out


# ---- aturan penamaan ------------------------------------------------------------------
def _sorted(hits: list[Hit]) -> list[Hit]:
    return sorted(hits, key=lambda h: (-h.pident, -h.bitscore, h.accession))


def lowest_common_rank(hits: list[Hit]) -> tuple[str, str]:
    genera = sorted({h.genus for h in hits if h.genus})
    if len(genera) == 1:
        return genera[0], "genus"
    families = sorted({h.family for h in hits if h.family})
    if len(families) == 1:
        return families[0], "famili"
    return "tidak dikenal", "tidak dikenal"


def name_asv(asv_id: str, hits: list[Hit], rules: dict, source: str = "referensi") -> Naming:
    r = rules["naming"]
    hits = _sorted(hits)
    notes = [r["lab_db_note"]] if source == "database lab" else []
    if not hits:
        return Naming(asv_id, "", "tidak dikenal", "tidak dikenal", ["referensi"], None, "", None, [],
                      source=source, notes=notes)
    top = hits[0]
    best = top.pident
    others = [h.pident for h in hits if h.species_key != top.species_key]
    floor = float(rules["blast"]["perc_identity"])
    gap = round(best - (max(others) if others else floor), 3)
    if best < r["unknown_below_identity"]:
        return Naming(asv_id, top.species, "tidak dikenal", "tidak dikenal", ["referensi"], best,
                      top.species, gap, [], family_hint=top.family, source=source, notes=notes, hits=hits)

    near = [h for h in hits if h.pident >= best - r["near_hit_delta_pct"]]
    species = sorted({h.species_key for h in near})
    base = dict(asv_id=asv_id, taxon_lab=top.species, best_identity=best, best_species=top.species,
                gap=gap, near_species=species, family_hint=top.family, source=source, notes=notes, hits=hits)

    if len(species) == 1:
        genus = top.genus or genus_of(top.species)
        if best < r["species_min_identity"]:
            return Naming(taxon=genus, rank="genus", causes=["referensi"], **base)
        if not top.resolved:
            return Naming(taxon=genus, rank="genus", causes=["referensi"], **base)
        if top.recorded != "ya":
            return Naming(taxon=genus, rank="genus", causes=["lokasi"], **base)
        if not any(h.validated for h in near):
            return Naming(taxon=genus, rank="genus", causes=["referensi"], **base)
        return Naming(taxon=species_key(top.species)[0], rank="spesies", causes=[], **base)

    taxon, rank = lowest_common_rank(near)
    causes = ["marker" if best >= r["marker_min_identity"] else "referensi"]
    if top.resolved and top.recorded != "ya":
        causes.append("lokasi")
    if rank == "tidak dikenal":
        base["notes"] = notes + ["kecocokan setara lintas famili; kemungkinan label referensi keliru"]
    return Naming(taxon=taxon, rank=rank, causes=causes, **base)


def lab_hits(row: dict, reference) -> list[Hit]:
    """F11: ubah baris taksonomi lab menjadi kecocokan semu untuk aturan yang sama."""
    out = []
    for taxon_col, pid_col, tag in (("taxon", "pct_identity", "lab1"),
                                    ("runner_up_taxon", "runner_up_pct_identity", "lab2")):
        taxon = str(row.get(taxon_col, "") or "").strip()
        pid = pd.to_numeric(row.get(pid_col, ""), errors="coerce")
        if not taxon or pd.isna(pid):
            continue
        key, resolved = species_key(taxon)
        genus = genus_of(taxon)
        validated = bool(resolved and (reference.taxonomy["spesies_kunci"] == key).any() and
                         (reference.taxonomy.loc[reference.taxonomy["spesies_kunci"] == key,
                                                 "status_validasi"] == "tervalidasi").any())
        out.append(Hit(accession=f"{tag}:{taxon}", species=taxon, species_key=key, genus=genus,
                       family=reference.family_of(genus), pident=float(pid), resolved=resolved,
                       validated=validated,
                       recorded=reference.recorded_in_indonesia(taxon) if resolved else "belum dicek"))
    return out


def name_project(project, reference, rules: dict, threads: int = 1) -> tuple[dict[str, Naming], list[str]]:
    """Penamaan semua ASV: BLAST bila ada FASTA, selain itu taksonomi lab (F11)."""
    notes: list[str] = []
    asvs = sorted(set(project.reads["asv_id"]))
    results: dict[str, Naming] = {}
    blast_hits: dict[str, list[Hit]] = {}
    seqs = {a: s for a, s in (project.sequences or {}).items() if a in set(asvs)}
    if seqs:
        db = reference.ensure_blast_db()
        if db is None or find_blast_tool("blastn") is None:
            notes.append("BLAST+ tidak tersedia; penamaan memakai taksonomi lab")
            seqs = {}
        else:
            blast_hits = hits_from_blast(run_blast(seqs, db, rules, threads=threads), reference)
    lab = {}
    if project.taxonomy is not None:
        lab = {row["asv_id"]: row for row in project.taxonomy.to_dict("records")}
    for asv in asvs:
        if asv in seqs:
            results[asv] = name_asv(asv, blast_hits.get(asv, []), rules)
        elif asv in lab:
            results[asv] = name_asv(asv, lab_hits(lab[asv], reference), rules, source="database lab")
        else:
            results[asv] = name_asv(asv, [], rules, source="tanpa data")
            results[asv].notes.append("tidak ada urutan maupun taksonomi lab")
    return results, notes
