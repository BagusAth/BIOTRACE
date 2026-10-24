from pathlib import Path

import pandas as pd

from biotrace.config import load_rules
from biotrace.io import load_project, read_table
from biotrace.provenance import build_manifest, fingerprint

MINI = Path(__file__).parent / "fixtures" / "mini"
LAKES = ["Matano", "Mahalona", "Towuti"]


def _load(**kw):
    args = dict(reads=MINI / "bacaan_lebar.csv", metadata=MINI / "metadata.csv",
                taxonomy=MINI / "taksonomi.csv", fasta=MINI / "asv.fasta", reference_lakes=LAKES)
    args.update(kw)
    return load_project(**args)


def test_wide_to_long_keeps_every_filled_cell():
    p = _load()
    wide = read_table((MINI / "bacaan_lebar.csv").read_bytes()).set_index("ASV")
    filled = (wide.apply(pd.to_numeric, errors="coerce").fillna(0) > 0).sum().sum()
    assert p.reads_were_wide
    assert len(p.reads) == filled
    assert list(p.reads.columns) == ["asv_id", "sample_id", "reads"]


def test_long_format_accepted(tmp_path):
    long = _load().reads
    path = tmp_path / "bacaan_panjang.csv"
    long.to_csv(path, index=False)
    p = _load(reads=path)
    assert not p.reads_were_wide
    pd.testing.assert_frame_equal(p.reads, long)


def test_faire_columns_mapped():
    p = _load()
    m = p.metadata.set_index("sample_id")
    assert m.loc["S1A", "latitude"] == "-2.4800"
    assert m.loc["S1A", "site_id"] == "ST1"
    assert m.loc["NEG1", "sample_type"] == "kontrol_negatif_pcr"
    assert m.loc["S1A", "lake"] == "Matano"
    assert p.column_map["metadata"]["latitude"] == "decimalLatitude"


def test_validation_records_missing_info_without_stopping():
    p = _load()
    text = " | ".join(p.missing_info)
    assert "batch B2 tanpa kontrol negatif" in text
    assert "L4 dinilai tanpa kontrol untuk batch B2" in text
    assert "NEG2" in text   # sampel di bacaan tanpa metadata


def test_missing_marker_column_still_processed(tmp_path):
    meta = pd.read_csv(MINI / "metadata.csv", dtype=str, keep_default_na=False).drop(columns=["target_gene"])
    path = tmp_path / "metadata_tanpa_marker.csv"
    meta.to_csv(path, index=False)
    p = _load(metadata=path)
    assert len(p.reads) > 0
    assert any("kolom marker tidak ada" in m for m in p.missing_info)


def test_bad_coordinates_flagged(tmp_path):
    meta = pd.read_csv(MINI / "metadata.csv", dtype=str, keep_default_na=False)
    meta.loc[0, "decimalLatitude"] = "-95"
    path = tmp_path / "metadata_koordinat.csv"
    meta.to_csv(path, index=False)
    p = _load(metadata=path)
    assert any("koordinat tidak valid" in m for m in p.missing_info)


def test_without_fasta_notes_lab_database():
    p = _load(fasta=None)
    assert p.sequences is None
    assert any("dinilai dengan database lab" in m for m in p.missing_info)


def test_same_input_same_manifest_and_fingerprint():
    rules = load_rules()
    m1 = build_manifest(_load(), rules=rules)
    m2 = build_manifest(_load(), rules=rules)
    assert m1 == m2
    assert fingerprint(m1) == fingerprint(m2)
    assert m1["input"]["bacaan_lebar.csv"].startswith("sha256:")
    assert m1["aplikasi"] == "biotrace 0.2.0"


def test_fingerprint_changes_with_input(tmp_path):
    rules = load_rules()
    changed = tmp_path / "bacaan_lebar.csv"
    changed.write_bytes((MINI / "bacaan_lebar.csv").read_bytes().replace(b"1520", b"1521"))
    assert fingerprint(build_manifest(_load(), rules=rules)) != fingerprint(build_manifest(_load(reads=changed), rules=rules))
