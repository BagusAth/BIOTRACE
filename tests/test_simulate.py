import random

import pandas as pd
import pytest

from biotrace.config import load_rules
from biotrace.simulate import (MIFISH_F, MIFISH_R_RC, RefRecord, as_amplicon, error_by_grade, extract_mifish,
                               leave_one_out, mutate, precision_vs_electrofishing, summarize_loo)

INSERT = ("CACCGCGGTTATACGAGAGGCCCAAGTTGATAGACACCGGCGTAAAGAGTGGTTAAGATAAAAATTTAAACTAAAGCCGAACGCC"
          "TTCAAAGCTGTTATACGCATCCGAAGGTAAGAAGCCCAATTACGAAAGTGGCTTTATAACCCCGACCCCACGAAAGCTAAGAAA")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_extract_mifish_insert():
    seq = "AAAA" * 10 + MIFISH_F + INSERT + MIFISH_R_RC + "TTTT" * 10
    assert extract_mifish(seq) == INSERT


def test_extract_mifish_tolerates_primer_mismatch():
    f = "A" + MIFISH_F[1:-1] + "A"
    seq = "GGG" + f + INSERT + MIFISH_R_RC + "CCC"
    assert extract_mifish(seq) == INSERT
    assert extract_mifish("ACGT" * 100) is None


def test_short_sequence_is_its_own_amplicon():
    assert as_amplicon(INSERT) == INSERT
    assert as_amplicon("ACGT" * 10) is None


def test_mutate_is_seeded_and_exact():
    a = mutate(INSERT, 5, random.Random(2026))
    b = mutate(INSERT, 5, random.Random(2026))
    assert a == b
    assert sum(x != y for x, y in zip(a, INSERT)) == 5


def _loo(rules, hits_rows, logic_only=True):
    records = {
        "A1": RefRecord("A1", "Oryzias alpha", "Oryzias", "Adrianichthyidae"),
        "B1": RefRecord("B1", "Oryzias beta", "Oryzias", "Adrianichthyidae"),
        "C1": RefRecord("C1", "Oryzias gamma", "Oryzias", "Adrianichthyidae"),
        "D1": RefRecord("D1", "Channa delta", "Channa", "Channidae"),
    }
    hits = pd.DataFrame(hits_rows, columns=["qseqid", "sseqid", "pident", "bitscore"])
    return leave_one_out({"q": "ACGT"}, {"q": "Oryzias alpha"}, hits, records, rules, logic_only=logic_only)


def test_loo_hides_true_species_and_reports_genus(rules):
    df = _loo(rules, [("q", "A1", 100.0, 300), ("q", "B1", 99.4, 290), ("q", "C1", 99.2, 285)])
    r = df.iloc[0]
    assert r["nama_teratas_tersisa"] == "Oryzias beta"
    assert r["ambang97_memberi_nama"]                     # ambang 97% memberi nama keliru
    assert r["biotrace_tingkat"] == "genus" and not r["keliru"]
    assert not r["keliru_lolos_aman"]


def test_loo_wrong_species_counted(rules):
    df = _loo(rules, [("q", "A1", 100.0, 300), ("q", "B1", 99.6, 290), ("q", "D1", 90.0, 200)])
    r = df.iloc[0]
    assert r["biotrace_tingkat"] == "spesies" and r["keliru"] and r["keliru_lolos_aman"]
    s = summarize_loo(df, "uji", "logika")
    assert s["biotrace_nama_keliru_lolos_pct"] == 100.0 and s["ambang97_nama_keliru_lolos_pct"] == 100.0
    eg = error_by_grade(df).set_index("nilai")
    assert eg.loc["A", "n"] == 1 and eg.loc["A", "galat_pct"] == 100.0


def test_loo_unknown_when_nothing_close(rules):
    df = _loo(rules, [("q", "A1", 100.0, 300), ("q", "D1", 88.0, 200)])
    assert df.iloc[0]["biotrace_tingkat"] == "tidak dikenal" and not df.iloc[0]["ambang97_memberi_nama"]


def test_precision_vs_electrofishing():
    codes = pd.DataFrame({"Genus": ["Esox", "Perca"], "Species": ["lucius", "flavescens"], "CODE_BDRSI": ["ESLU", "PEFL"]})
    elec = pd.DataFrame({"station": ["E1"], "year": [2019], "CODE_BDRSI": ["ESLU"], "count": [3]})
    elec_env = pd.DataFrame({"station": ["E1"], "year": [2019], "region": ["R1"]})
    edna = pd.DataFrame({"site": ["S1"], "year": [2019], "region": ["R1"]})
    claims = pd.DataFrame({"site_id": ["S1_2019", "S1_2019"], "nilai": ["A", "B"], "tingkat": ["spesies", "spesies"],
                           "taxon_dilaporkan": ["Esox lucius", "Perca flavescens"]})
    p = precision_vs_electrofishing(claims, codes, elec, elec_env, edna)
    assert (p["klaim_AB_spesies_di_sektor_electrofishing"], p["cocok_electrofishing"], p["presisi_AB_pct"]) == (2, 1, 50.0)
    assert p["presisi_spesies_semua_nilai_pct"] == 50.0


def test_external_reference_is_separate_and_refused():
    from pathlib import Path

    from biotrace.pipeline import ReferenceSeparationError, run
    from biotrace.reference import load_reference

    root = Path(__file__).resolve().parent.parent
    lsp = load_reference(root / "data" / "test" / "lake_st_pierre" / "ref")
    assert lsp.kind == "uji_luar" and lsp.region == "Lake St. Pierre"
    assert "checklist_lsp.csv" in lsp.files and len(lsp.checklist) > 100
    mini = root / "tests" / "fixtures" / "mini"
    with pytest.raises(ReferenceSeparationError):
        run(mini / "bacaan_lebar.csv", mini / "metadata.csv", mini / "taksonomi.csv", reference=lsp)
