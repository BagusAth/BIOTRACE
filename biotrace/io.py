"""F1-F3: baca 3 CSV dan FASTA dari lab, ubah ke format panjang, dan validasi.

Setiap kekurangan dicatat sebagai "informasi yang hilang" beserta dampaknya; proses tidak
pernah dihentikan karena kolom atau baris yang kurang.
"""

from __future__ import annotations

import csv
import hashlib
import io as _io
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Union

import pandas as pd

Source = Union[str, Path, bytes, BinaryIO]
CONTROL_TYPES = ("kontrol_negatif_lapangan", "kontrol_negatif_pcr")


@dataclass(frozen=True, order=True)
class Issue:
    berkas: str
    masalah: str
    dampak: str
    tingkat: str = "peringatan"   # galat | peringatan | info

    def text(self) -> str:
        return f"{self.masalah} — {self.dampak}" if self.dampak else self.masalah


@dataclass
class InputFile:
    role: str          # bacaan | taksonomi | metadata | fasta
    name: str
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass
class ProjectInput:
    reads: pd.DataFrame                      # asv_id, sample_id, reads
    metadata: pd.DataFrame                   # kolom internal, satu baris per sample_id
    taxonomy: pd.DataFrame | None            # kolom internal per asv_id
    sequences: dict[str, str] | None         # asv_id -> urutan
    files: list[InputFile]
    issues: list[Issue] = field(default_factory=list)
    reads_were_wide: bool = False
    column_map: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def missing_info(self) -> list[str]:
        return [i.text() for i in sorted(set(self.issues))]

    @property
    def samples(self) -> pd.DataFrame:
        return self.metadata[self.metadata["sample_type"] == "sampel"]


# ---- pembacaan berkas ---------------------------------------------------------------
def read_bytes(src: Source) -> tuple[str, bytes]:
    if isinstance(src, (str, Path)):
        p = Path(src)
        return p.name, p.read_bytes()
    if isinstance(src, bytes):
        return "berkas", src
    name = getattr(src, "name", "berkas")
    data = src.read()
    return Path(str(name)).name, data if isinstance(data, bytes) else data.encode()


def read_table(data: bytes) -> pd.DataFrame:
    text = data.decode("utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        sep = dialect.delimiter
    except csv.Error:
        sep = ","
    df = pd.read_csv(_io.StringIO(text), sep=sep, dtype=str, keep_default_na=False)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def read_fasta_bytes(data: bytes) -> dict[str, str]:
    seqs: dict[str, str] = {}
    name, buf = None, []
    for line in data.decode("utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith(">"):
            if name:
                seqs[name] = "".join(buf).upper()
            name, buf = line[1:].split()[0], []
        elif line:
            buf.append(line)
    if name:
        seqs[name] = "".join(buf).upper()
    return seqs


def normalize_columns(df: pd.DataFrame, aliases: dict[str, list[str]],
                      wanted: list[str]) -> tuple[pd.DataFrame, dict[str, str]]:
    """Petakan nama kolom lab (mis. decimalLatitude) ke nama internal (latitude)."""
    lower = {c.lower(): c for c in df.columns}
    mapping: dict[str, str] = {}
    for internal in wanted:
        for alias in aliases.get(internal, [internal]):
            if alias.lower() in lower and lower[alias.lower()] not in mapping.values():
                mapping[internal] = lower[alias.lower()]
                break
    out = df.rename(columns={v: k for k, v in mapping.items()})
    return out, mapping


def to_long(df: pd.DataFrame, aliases: dict[str, list[str]]) -> tuple[pd.DataFrame, bool, list[Issue]]:
    """Format panjang diterima apa adanya; format lebar (ASV x sampel) dilebur."""
    issues: list[Issue] = []
    norm, _ = normalize_columns(df, aliases, ["asv_id", "sample_id", "reads"])
    if {"asv_id", "sample_id", "reads"} <= set(norm.columns):
        long = norm[["asv_id", "sample_id", "reads"]].copy()
        wide = False
    else:
        id_col = "asv_id" if "asv_id" in norm.columns else norm.columns[0]
        if id_col != "asv_id":
            issues.append(Issue("bacaan", f"kolom asv_id tidak ditemukan; kolom '{id_col}' dipakai sebagai ID ASV",
                                "periksa bahwa kolom pertama memang ID ASV"))
        sample_cols = [c for c in norm.columns if c != id_col]
        long = norm.melt(id_vars=[id_col], value_vars=sample_cols, var_name="sample_id", value_name="reads")
        long = long.rename(columns={id_col: "asv_id"})
        wide = True
    long["asv_id"] = long["asv_id"].astype(str).str.strip()
    long["sample_id"] = long["sample_id"].astype(str).str.strip()
    raw = long["reads"].astype(str).str.strip()
    num = pd.to_numeric(raw, errors="coerce")
    bad = raw.ne("") & num.isna()
    if bad.any():
        issues.append(Issue("bacaan", f"{int(bad.sum())} sel bacaan bukan angka",
                            "sel itu dianggap kosong"))
    long["reads"] = num.fillna(0).round().astype(int)
    long = long[long["reads"] > 0]
    long = long.sort_values(["asv_id", "sample_id"]).reset_index(drop=True)
    return long, wide, issues


# ---- validasi -----------------------------------------------------------------------
MISSING_IMPACT = {
    "site_id": "lokasi tidak diketahui; klaim digabung per sampel",
    "latitude": "koordinat tidak dicek",
    "longitude": "koordinat tidak dicek",
    "collection_date": "tanggal sampling tidak tercantum di laporan",
    "sample_type": "semua baris dianggap sampel; L4 dinilai tanpa kontrol negatif",
    "replicate": "replikat dihitung dari jumlah sampel per lokasi",
    "extraction_batch": "kontrol negatif tidak bisa dicocokkan per batch; L4 dinilai tanpa kontrol",
    "marker": "marker diasumsikan 12S rRNA (MiFish-U)",
}
TAXONOMY_IMPACT = {
    "rank": "tingkat takson lab tidak dipakai",
    "pct_identity": "kemiripan lab tidak ada; klaim dari taksonomi lab dinilai tidak dikenal",
    "runner_up_taxon": "selisih dengan spesies lain tidak bisa dihitung; L1 maksimal 0",
    "runner_up_pct_identity": "selisih dengan spesies lain tidak bisa dihitung; L1 maksimal 0",
    "reference_db": "database lab tidak tercatat",
}


def normalize_sample_type(series: pd.Series, rules: dict) -> tuple[pd.Series, list[str]]:
    lookup = {}
    for canon, names in rules["input"]["sample_type_aliases"].items():
        for n in names:
            lookup[n.lower()] = canon
    raw = series.astype(str).str.strip().str.lower()
    mapped = raw.map(lookup)
    unknown = sorted(set(raw[mapped.isna() & raw.ne("")]))
    return mapped.fillna("sampel"), unknown


def validate_metadata(meta: pd.DataFrame, rules: dict, reference_lakes: list[str]) -> tuple[pd.DataFrame, list[Issue]]:
    issues: list[Issue] = []
    req = rules["input"]["required_columns"]["metadata"]
    for col in req:
        if col == "sample_id":
            continue
        if col not in meta.columns:
            issues.append(Issue("metadata", f"kolom {col} tidak ada", MISSING_IMPACT.get(col, "")))
            meta[col] = ""
    for col in ("lake", "region", "fasilitas_sekitar"):
        if col not in meta.columns:
            meta[col] = ""
    if (meta["lake"] == "").all():
        issues.append(Issue("metadata", "kolom danau (lake/waterBody) tidak ada",
                            "L2 dinilai terhadap checklist seluruh wilayah"))
    else:
        unknown = sorted(set(meta["lake"]) - set(reference_lakes) - {""})
        if unknown:
            issues.append(Issue("metadata", f"danau di luar referensi: {', '.join(unknown)}",
                                "L2 dinilai terhadap checklist seluruh wilayah"))

    meta["sample_type"], unknown_types = normalize_sample_type(meta["sample_type"], rules)
    if unknown_types:
        issues.append(Issue("metadata", f"sample_type tidak dikenal: {', '.join(unknown_types)}",
                            "baris itu dianggap sampel"))
    if (meta["site_id"] == "").any():
        meta.loc[meta["site_id"] == "", "site_id"] = meta["sample_id"]

    lat = pd.to_numeric(meta["latitude"], errors="coerce")
    lon = pd.to_numeric(meta["longitude"], errors="coerce")
    has_coord = meta["latitude"].ne("") | meta["longitude"].ne("")
    lo, hi = rules["input"]["latitude_range"]
    lo2, hi2 = rules["input"]["longitude_range"]
    bad = has_coord & (lat.isna() | lon.isna() | ~lat.between(lo, hi) | ~lon.between(lo2, hi2))
    if bad.any():
        ids = ", ".join(sorted(meta.loc[bad, "sample_id"])[:5])
        issues.append(Issue("metadata", f"{int(bad.sum())} koordinat tidak valid atau di luar rentang ({ids})",
                            "koordinat sampel itu tidak dipakai", "galat"))
    box = rules["input"].get("focus_bbox")
    if box:
        ok = ~bad & has_coord
        outside = ok & ~(lat.between(*box["lat"]) & lon.between(*box["lon"]))
        if outside.any():
            issues.append(Issue("metadata", f"{int(outside.sum())} sampel di luar wilayah fokus Malili",
                                "checklist dan kelengkapan Malili mungkin tidak berlaku", "info"))

    if "marker" in meta.columns:
        markers = sorted(set(meta["marker"]) - {""})
        other = [m for m in markers if "12s" not in m.lower() and "mifish" not in m.lower()]
        if other:
            issues.append(Issue("metadata", f"marker {', '.join(other)}", "referensi v0.1 hanya 12S rRNA"))

    # batch ekstraksi tanpa kontrol negatif
    if (meta["extraction_batch"] != "").any():
        for batch, grp in meta.groupby("extraction_batch"):
            if batch == "":
                continue
            if (grp["sample_type"] == "sampel").any() and not grp["sample_type"].isin(CONTROL_TYPES).any():
                issues.append(Issue("metadata", f"batch {batch} tanpa kontrol negatif",
                                    f"L4 dinilai tanpa kontrol untuk batch {batch}"))
    return meta, issues


def load_project(reads: Source, metadata: Source, taxonomy: Source | None = None,
                 fasta: Source | None = None, rules: dict | None = None,
                 reference_lakes: list[str] | None = None) -> ProjectInput:
    from .config import load_rules

    rules = rules or load_rules()
    aliases = rules["input"]["column_aliases"]
    files: list[InputFile] = []
    issues: list[Issue] = []
    column_map: dict[str, dict[str, str]] = {}

    name, data = read_bytes(reads)
    files.append(InputFile("bacaan", name, data))
    long, wide, iss = to_long(read_table(data), aliases)
    issues += iss

    name, data = read_bytes(metadata)
    files.append(InputFile("metadata", name, data))
    meta_raw = read_table(data)
    wanted = list(rules["input"]["required_columns"]["metadata"]) + ["lake", "region", "fasilitas_sekitar"]
    meta, column_map["metadata"] = normalize_columns(meta_raw, aliases, wanted)
    if "sample_id" not in meta.columns:
        issues.append(Issue("metadata", "kolom sample_id tidak ada",
                            "metadata tidak bisa dicocokkan; semua sampel dianggap tanpa metadata", "galat"))
        meta = pd.DataFrame({"sample_id": sorted(set(long["sample_id"]))})
    meta["sample_id"] = meta["sample_id"].astype(str).str.strip()
    dup = meta["sample_id"].duplicated()
    if dup.any():
        issues.append(Issue("metadata", f"{int(dup.sum())} sample_id ganda di metadata", "baris pertama dipakai"))
        meta = meta[~dup]
    meta, iss = validate_metadata(meta, rules, reference_lakes or [])
    issues += iss

    in_reads = set(long["sample_id"])
    in_meta = set(meta["sample_id"])
    only_reads = sorted(in_reads - in_meta)
    only_meta = sorted(in_meta - in_reads)
    if only_reads:
        issues.append(Issue("bacaan", f"{len(only_reads)} sampel di tabel bacaan tidak ada di metadata "
                                      f"({', '.join(only_reads[:5])})",
                            "dianggap sampel dengan lokasi sendiri dan tanpa batch"))
        extra = pd.DataFrame({"sample_id": only_reads, "site_id": only_reads, "sample_type": "sampel"})
        meta = pd.concat([meta, extra], ignore_index=True).fillna("")
    if only_meta:
        issues.append(Issue("metadata", f"{len(only_meta)} sampel di metadata tanpa bacaan "
                                        f"({', '.join(only_meta[:5])})",
                            "dihitung sebagai nol bacaan", "info"))

    tax = None
    if taxonomy is not None:
        name, data = read_bytes(taxonomy)
        files.append(InputFile("taksonomi", name, data))
        wanted_tax = rules["input"]["required_columns"]["taxonomy"]
        tax, column_map["taksonomi"] = normalize_columns(read_table(data), aliases, wanted_tax)
        for col in wanted_tax:
            if col not in tax.columns:
                if col in ("asv_id", "taxon"):
                    issues.append(Issue("taksonomi", f"kolom {col} tidak ada",
                                        "tabel taksonomi lab tidak bisa dipakai", "galat"))
                else:
                    issues.append(Issue("taksonomi", f"kolom {col} tidak ada", TAXONOMY_IMPACT.get(col, "")))
                tax[col] = ""
        tax["asv_id"] = tax["asv_id"].astype(str).str.strip()
        tax = tax.drop_duplicates("asv_id").sort_values("asv_id").reset_index(drop=True)

    seqs = None
    if fasta is not None:
        name, data = read_bytes(fasta)
        files.append(InputFile("fasta", name, data))
        seqs = read_fasta_bytes(data)
        missing = sorted(set(long["asv_id"]) - set(seqs))
        if missing:
            issues.append(Issue("fasta", f"{len(missing)} ASV di tabel bacaan tanpa urutan di FASTA",
                                "ASV itu dinilai dengan taksonomi lab bila ada, selain itu tidak dikenal"))
    elif tax is None:
        issues.append(Issue("fasta", "FASTA dan tabel taksonomi tidak ada",
                            "semua ASV dilaporkan tidak dikenal", "galat"))
    else:
        issues.append(Issue("fasta", "FASTA tidak ada",
                            "penamaan memakai taksonomi lab dengan catatan 'dinilai dengan database lab'"))
    if tax is not None and seqs is None:
        missing_tax = sorted(set(long["asv_id"]) - set(tax["asv_id"]))
        if missing_tax:
            issues.append(Issue("taksonomi", f"{len(missing_tax)} ASV tanpa baris taksonomi",
                                "ASV itu dilaporkan tidak dikenal"))

    meta = meta.sort_values("sample_id").reset_index(drop=True)
    return ProjectInput(reads=long, metadata=meta, taxonomy=tax, sequences=seqs, files=files,
                        issues=sorted(set(issues)), reads_were_wide=wide, column_map=column_map)
