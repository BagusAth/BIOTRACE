"""F5-F7: referensi tervalidasi, checklist perairan, status, alias, dan peta kelengkapan."""

from __future__ import annotations

import hashlib
import io
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from .config import ROOT, find_blast_tool, sha256_file
from .taxonomy import genera_of, genus_of, is_hybrid, same_species_name, species_key

THREATENED = {"CR", "EN", "VU"}
REFERENCE_FILES = (
    "ref12S.fasta", "ref12S_taksonomi.csv", "checklist_malili.csv", "status.csv",
    "alias.csv", "jalur_masuk.csv", "kelengkapan.csv", "reference.yaml",
)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


@dataclass
class Reference:
    root: Path
    meta: dict
    taxonomy: pd.DataFrame
    checklist: pd.DataFrame
    status: pd.DataFrame
    alias: pd.DataFrame
    pathways: pd.DataFrame
    completeness: pd.DataFrame
    files: dict[str, str] = field(default_factory=dict)
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    def _memo(self, key: tuple, fn):
        """Tabel acuan kecil dan tetap selama proses: hasil pencarian cukup dihitung sekali."""
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    # ---- identitas dan versi -------------------------------------------------
    @property
    def version(self) -> str:
        return str(self.meta.get("version", "?"))

    @property
    def kind(self) -> str:
        return str(self.meta.get("jenis", "indonesia"))

    @property
    def region(self) -> str:
        return str(self.meta.get("wilayah", ""))

    @property
    def lakes(self) -> list[str]:
        return list(self.meta.get("danau", []))

    @property
    def fingerprint(self) -> str:
        lines = "".join(f"{k}:{v}\n" for k, v in sorted(self.files.items()))
        return hashlib.sha256(lines.encode()).hexdigest()

    @property
    def label(self) -> str:
        return f"{self.meta.get('nama', 'ref12S')} {self.version} (sha256:{self.fingerprint})"

    @property
    def blast_db(self) -> Path:
        return self.root / self.meta.get("blast_db", "ref12S")

    def ensure_blast_db(self) -> Path | None:
        """Bangun database BLAST dari FASTA bila belum ada; None bila BLAST+ tidak tersedia."""
        db = self.blast_db
        if Path(str(db) + ".nsq").exists() or Path(str(db) + ".nal").exists():
            return db
        exe = find_blast_tool("makeblastdb")
        if exe is None:
            return None
        build_blast_db(exe, self.root / "ref12S.fasta", db)
        return db

    # ---- sekuens referensi ---------------------------------------------------
    def _hit_index(self) -> dict[str, dict]:
        return {r["aksesi"]: {
            "aksesi": r["aksesi"],
            "spesies": r["spesies"],
            "spesies_kunci": r["spesies_kunci"],
            "genus": r["genus"],
            "famili": r["famili"],
            "terselesaikan": r["terselesaikan"] == "ya",
            "tervalidasi": r["status_validasi"] == "tervalidasi",
            "tercatat_di_indonesia": r["tercatat_di_indonesia"],
        } for r in self.taxonomy.to_dict("records")}

    def hit(self, accession: str) -> dict:
        acc = accession.split(".")[0]
        info = self._memo(("hit_index",), self._hit_index).get(acc)
        if info is None:
            return {"aksesi": acc, "spesies": "", "spesies_kunci": "", "genus": "", "famili": "",
                    "terselesaikan": False, "tervalidasi": False, "tercatat_di_indonesia": "belum dicek"}
        return info

    def recorded_in_indonesia(self, species: str) -> str:
        return self._memo(("recorded", species), lambda: self._recorded_in_indonesia(species))

    def _recorded_in_indonesia(self, species: str) -> str:
        key, _ = species_key(species)
        rows = self.taxonomy[self.taxonomy["spesies_kunci"] == key]
        if len(rows):
            return rows["tercatat_di_indonesia"].iloc[0]
        return "ya" if self._checklist_species_match(species, self.checklist) else "belum dicek"

    def family_of(self, genus: str) -> str:
        return self._memo(("family", genus), lambda: self._family_of(genus))

    def _family_of(self, genus: str) -> str:
        fam = self.taxonomy.loc[self.taxonomy["genus"] == genus, "famili"]
        if len(fam):
            return fam.mode().iloc[0]
        fam = self.checklist.loc[self.checklist["spesies"].map(genus_of) == genus, "famili"]
        return fam.iloc[0] if len(fam) else ""

    # ---- alias, checklist, status --------------------------------------------
    def alias_of(self, taxon: str) -> list[str]:
        """Nama alias (mis. 'louhan hibrida') untuk spesies, genus, atau hibrida."""
        return list(self._memo(("alias", taxon), lambda: self._alias_of(taxon)))

    def _alias_of(self, taxon: str) -> list[str]:
        if not taxon or self.alias.empty:
            return []
        out = set()
        parts = [p.strip() for p in taxon.replace(" × ", " x ").split(" x ")] if is_hybrid(taxon) else [taxon]
        for part in parts:
            for _, a in self.alias.iterrows():
                if a["tingkat"] == "spesies" and same_species_name(part, a["nama_induk"]):
                    out.add(a["nama_alias"])
                elif a["tingkat"] == "genus" and genus_of(part) == a["nama_induk"]:
                    out.add(a["nama_alias"])
        return sorted(out)

    def checklist_for(self, lake: str | None) -> pd.DataFrame:
        """Baris checklist yang berlaku untuk danau; baris tingkat wilayah berlaku di semua danau."""
        if not lake or lake not in self.lakes:
            return self.checklist
        return self.checklist[self.checklist["danau"].isin([lake, self.region])]

    @staticmethod
    def _checklist_species_match(taxon: str, cl: pd.DataFrame) -> pd.DataFrame:
        return cl[cl["spesies"].map(lambda s: same_species_name(s, taxon))]

    def checklist_hit(self, taxon: str, rank: str, lake: str | None) -> tuple[bool, str]:
        """L2: apakah takson tercatat di checklist danau, langsung atau lewat alias."""
        return self._memo(("l2", taxon, rank, lake), lambda: self._checklist_hit(taxon, rank, lake))

    def _checklist_hit(self, taxon: str, rank: str, lake: str | None) -> tuple[bool, str]:
        cl = self.checklist_for(lake)
        if rank == "spesies":
            if len(self._checklist_species_match(taxon, cl)):
                return True, "langsung"
        elif rank == "genus":
            if (cl["spesies"].map(genus_of) == taxon).any():
                return True, "genus"
        elif rank == "famili":
            if (cl["famili"] == taxon).any():
                return True, "famili"
        for alias in self.alias_of(taxon):
            if (cl["spesies"] == alias).any():
                return True, f"alias: {alias}"
        return False, ""

    def status_row(self, name: str) -> dict:
        return dict(self._memo(("status", name), lambda: self._status_row(name)))

    def _status_row(self, name: str) -> dict:
        rows = self.status[self.status["spesies"].map(lambda s: same_species_name(s, name))]
        return rows.iloc[0].to_dict() if len(rows) else {}

    def endemics_without_reference(self, lake: str | None, genus: str | None = None,
                                   family: str | None = None) -> list[str]:
        cl = self.checklist_for(lake)
        cl = cl[cl["status"] == "endemik"]
        if genus:
            cl = cl[cl["spesies"].map(genus_of) == genus]
        if family:
            cl = cl[cl["famili"] == family]
        validated = set(self.taxonomy.loc[self.taxonomy["status_validasi"] == "tervalidasi", "spesies_kunci"])
        return sorted({s for s in cl["spesies"] if species_key(s)[0] not in validated})

    def l3_labels(self, taxon: str, rank: str, lake: str | None, near_family: str | None = None) -> list[str]:
        """L3: endemik, terancam, invasif, kemungkinan louhan hibrida, kemungkinan endemik di luar kamus."""
        key = ("l3", taxon, rank, lake, near_family if rank == "tidak dikenal" else None)
        return list(self._memo(key, lambda: self._l3_labels(taxon, rank, lake, near_family)))

    def _l3_labels(self, taxon: str, rank: str, lake: str | None, near_family: str | None) -> list[str]:
        labels: set[str] = set()
        aliases = self.alias_of(taxon) if taxon else []
        if aliases:
            labels.update(f"kemungkinan {a}" for a in aliases)
            for a in aliases:
                if self.status_row(a).get("invasif") == "ya":
                    labels.add("invasif")
        cl = self.checklist_for(lake)
        if rank == "spesies":
            st = self._checklist_species_match(taxon, cl)
            if (st["status"] == "endemik").any():
                labels.add("endemik")
            row = self.status_row(taxon)
            if row.get("kategori_iucn") in THREATENED:
                labels.add("terancam")
            if row.get("invasif") == "ya":
                labels.add("invasif")
        elif rank in ("genus", "famili"):
            genus = taxon if rank == "genus" else None
            family = taxon if rank == "famili" else None
            if self.endemics_without_reference(lake, genus=genus, family=family):
                labels.add("kemungkinan endemik di luar kamus")
            members = cl[cl["spesies"].map(genus_of) == taxon] if genus else cl[cl["famili"] == taxon]
            members = [s for s in members["spesies"] if species_key(s)[1]]
            if members and all(self.status_row(s).get("invasif") == "ya" for s in members):
                labels.add("invasif")
        elif rank == "tidak dikenal" and near_family:
            if self.endemics_without_reference(lake, family=near_family):
                labels.add("kemungkinan endemik di luar kamus")
        return sorted(labels)

    def pathway(self, taxon: str) -> dict:
        return dict(self._memo(("pathway", taxon), lambda: self._pathway(taxon)))

    def _pathway(self, taxon: str) -> dict:
        names = [taxon, *self.alias_of(taxon)]
        for n in names:
            rows = self.pathways[self.pathways["spesies"].map(lambda s: same_species_name(s, n))]
            if len(rows):
                return rows.iloc[0].to_dict()
        return {}

    # ---- kelengkapan ----------------------------------------------------------
    def completeness_for(self, genus: str, lake: str | None, scope: str = "wilayah") -> dict | None:
        """F18: P belum di kamus untuk genus di wilayah (atau danau, bila scope='danau')."""
        area = self.region if scope == "wilayah" or not lake or lake not in self.lakes else lake
        rows = self.completeness[(self.completeness["wilayah"] == area) & (self.completeness["genus"] == genus)]
        if rows.empty:
            return None
        r = rows.iloc[0]
        return {"wilayah": area, "genus": genus, "n": int(r["n_checklist"]), "r": int(r["r_tervalidasi"]),
                "p": float(r["p_belum_di_kamus"]), "tanpa_referensi": r["spesies_tanpa_referensi"]}


def load_reference(root: str | Path | None = None) -> Reference:
    root = Path(root) if root else ROOT / "data" / "ref" / "v0.1"
    meta = yaml.safe_load((root / "reference.yaml").read_text(encoding="utf-8"))
    taxonomy = read_csv(root / "ref12S_taksonomi.csv").set_index("aksesi", drop=False)
    berkas = meta.get("berkas", {})   # nama berkas lain untuk referensi selain Malili
    optional = {}
    for name in ("checklist_malili.csv", "status.csv", "alias.csv", "jalur_masuk.csv", "kelengkapan.csv"):
        p = root / berkas.get(name, name)
        optional[name] = read_csv(p) if p.exists() else pd.DataFrame()
    names = [berkas.get(n, n) for n in REFERENCE_FILES]
    files = {name: sha256_file(root / name) for name in names if (root / name).exists()}
    return Reference(
        root=root, meta=meta, taxonomy=taxonomy,
        checklist=_ensure_cols(optional["checklist_malili.csv"], ["spesies", "famili", "danau", "status"]),
        status=_ensure_cols(optional["status.csv"], ["spesies", "kategori_iucn", "invasif"]),
        alias=_ensure_cols(optional["alias.csv"], ["nama_induk", "nama_alias", "tingkat"]),
        pathways=_ensure_cols(optional["jalur_masuk.csv"], ["spesies", "jalur", "fasilitas_sekitar"]),
        completeness=_ensure_cols(optional["kelengkapan.csv"],
                                  ["wilayah", "genus", "n_checklist", "r_tervalidasi", "p_belum_di_kamus",
                                   "spesies_tanpa_referensi"]),
        files=files,
    )


def _ensure_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df


def build_blast_db(makeblastdb: str, fasta: Path, out: Path) -> None:
    subprocess.run([makeblastdb, "-in", str(fasta), "-dbtype", "nucl", "-parse_seqids",
                    "-out", str(out), "-title", out.name], check=True, capture_output=True, text=True)


# ---- sumber QIIME (mitohelper) ---------------------------------------------------
def _qza_member(path: Path, suffix: str) -> bytes:
    with zipfile.ZipFile(path) as zf:
        name = next(n for n in zf.namelist() if n.endswith(suffix))
        return zf.read(name)


def read_qza_sequences(path: Path) -> dict[str, str]:
    seqs: dict[str, str] = {}
    acc, buf = None, []
    for line in io.StringIO(_qza_member(path, "data/dna-sequences.fasta").decode()):
        line = line.strip()
        if line.startswith(">"):
            if acc:
                seqs[acc] = "".join(buf)
            acc, buf = line[1:].split()[0], []
        elif line:
            buf.append(line)
    if acc:
        seqs[acc] = "".join(buf)
    return seqs


def read_qza_taxonomy(path: Path) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(_qza_member(path, "data/taxonomy.tsv")), sep="\t", dtype=str)
    df.columns = ["aksesi", "taxon"]
    ranks = df["taxon"].str.split(";", expand=True)
    for col, prefix in (("ordo", "o__"), ("famili", "f__"), ("genus", "g__"), ("spesies", "s__")):
        match = ranks.apply(lambda r, p=prefix: next((x[len(p):] for x in r if isinstance(x, str) and x.startswith(p)), ""), axis=1)
        df[col] = match
    return df


def read_fasta(path: Path) -> dict[str, str]:
    seqs: dict[str, str] = {}
    acc, buf = None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">"):
                if acc:
                    seqs[acc] = "".join(buf)
                acc, buf = line[1:].split()[0], []
            elif line:
                buf.append(line)
    if acc:
        seqs[acc] = "".join(buf)
    return seqs


def write_fasta(seqs: dict[str, str], path: Path, width: int = 0) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for acc in sorted(seqs):
            s = seqs[acc]
            fh.write(f">{acc}\n")
            if width:
                for i in range(0, len(s), width):
                    fh.write(s[i:i + width] + "\n")
            else:
                fh.write(s + "\n")


# ---- peta kelengkapan --------------------------------------------------------------
def compute_completeness(checklist: pd.DataFrame, taxonomy: pd.DataFrame, region: str,
                         lakes: list[str]) -> pd.DataFrame:
    """n = spesies genus di checklist; r = yang punya >= 1 sekuens tervalidasi; P = (n - r) / n."""
    validated = set(taxonomy.loc[taxonomy["status_validasi"] == "tervalidasi", "spesies_kunci"])
    any_seq = set(taxonomy["spesies_kunci"])
    rows = []
    for area in [region, *lakes]:
        cl = checklist if area == region else checklist[checklist["danau"].isin([area, region])]
        species = sorted({species_key(s)[0] for s in cl["spesies"] if species_key(s)[1]})
        by_genus: dict[str, list[str]] = {}
        for s in species:
            by_genus.setdefault(genus_of(s), []).append(s)
        for genus, members in sorted(by_genus.items()):
            n = len(members)
            r = sum(1 for s in members if s in validated)
            seq = sum(1 for s in members if s in any_seq)
            missing = [s for s in members if s not in validated]
            rows.append({
                "wilayah": area, "genus": genus, "n_checklist": n, "r_tervalidasi": r,
                "n_ada_sekuens": seq, "p_belum_di_kamus": round((n - r) / n, 4),
                "spesies_tanpa_referensi": "; ".join(missing),
            })
    return pd.DataFrame(rows)


def genera_in(names: list[str]) -> list[str]:
    return sorted({g for n in names for g in genera_of(n)})
