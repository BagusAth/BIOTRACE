from pathlib import Path

import pandas as pd
import pytest

from biotrace.config import load_rules
from biotrace.decision import decide, origin
from biotrace.pipeline import ReferenceSeparationError, run
from biotrace.reference import load_reference
from biotrace.scoring import claim_causes

MINI = Path(__file__).parent / "fixtures" / "mini"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def ref():
    return load_reference()


@pytest.fixture(scope="module")
def report(rules, ref):
    return run(MINI / "bacaan_lebar.csv", MINI / "metadata.csv", MINI / "taksonomi.csv",
               rules=rules, reference=ref)


def _row(**kw):
    base = {"tingkat": "spesies", "nilai": "A", "label_L3": "", "penyebab": [], "taxon_dilaporkan": "X y",
            "danau": "Matano", "site_id": "ST1"}
    base.update(kw)
    return base


@pytest.mark.parametrize("grade,labels,expected", [
    ("A", "", "aman dilaporkan"), ("B", "invasif", "aman dilaporkan"),
    ("C", "", "dengan catatan"), ("C", "endemik", "wajib verifikasi"),
    ("D", "", "jangan dipakai"), ("D", "endemik", "wajib verifikasi"),
    ("D", "kemungkinan louhan hibrida; invasif", "wajib verifikasi"),
])
def test_decision_matrix(rules, grade, labels, expected):
    assert decide(_row(nilai=grade, label_L3=labels), rules)[0] == expected


def test_unknown_decisions(rules):
    assert decide(_row(tingkat="tidak dikenal", nilai="D", penyebab=["referensi"]), rules)[0] == "dengan catatan"
    k, t = decide(_row(tingkat="tidak dikenal", nilai="D", penyebab=["referensi", "sampel"]), rules)
    assert k == "jangan dipakai"
    assert "ikan tidak dikenal, kemungkinan belum ada di kamus" in t


def test_endemic_d_not_discarded(rules):
    k, t = decide(_row(nilai="D", label_L3="endemik"), rules)
    assert k == "wajib verifikasi" and "tidak dibuang" in t


def test_b_claim_always_has_cause(rules):
    row = {"penyebab_penamaan": [], "batas_D": "", "replikat_positif": 2, "l2_dinilai": True, "skor_L2": 1,
           "peluang_belum_di_kamus": 0.0, "kemiripan_terbaik": 100.0, "selisih_spesies_lain": 3.0,
           "skor_L1": 2, "skor_L4": 1}
    assert claim_causes(row, "B", rules) == ["sampel"]


def test_every_claim_has_reasons_and_bd_claims_have_causes(report):
    c = report.claims
    assert len(c) > 0
    for col in ("alasan_penamaan_id", "alasan_L1_id", "alasan_L2_id", "alasan_L4_id",
                "alasan_penamaan_en", "alasan_L1_en", "alasan_L2_en", "alasan_L4_en"):
        assert (c[col].str.len() > 0).all(), col
    bd = c[c["nilai"].isin(["B", "C", "D"])]
    assert (bd["penyebab"].str.len() > 0).all()


def test_caps_and_causes_in_pipeline(report):
    c = report.claims.set_index("claim_id")
    assert c.loc["asv03@ST1", "nilai"] == "D"                       # kontrol negatif batch B1
    assert "sampel" in c.loc["asv03@ST1", "penyebab"]
    assert c.loc["asv01@ST1", "nilai"] == "A" and c.loc["asv01@ST1", "keputusan"] == "aman dilaporkan"
    assert c.loc["asv04@ST1", "keputusan"] == "jangan dipakai"      # tidak dikenal + sinyal lab bermasalah
    assert c.loc["asv02@ST2", "peluang_belum_di_kamus"] == 1.0      # Telmatherina di Kompleks Malili
    assert (report.claims["galat_nilai"].str.len() > 0).all()       # angka uji atau "belum dikalibrasi"


def test_endemic_genus_claim_needs_verification(report):
    c = report.claims.set_index("claim_id").loc["asv02@ST2"]
    assert c["tingkat"] == "genus" and "kemungkinan endemik di luar kamus" in c["label_L3"]
    assert c["keputusan"] == "wajib verifikasi"


def test_origin_uses_possibility_language(report, ref):
    text = report.claims.set_index("claim_id").loc["asv01@ST1", "asal_usul"]
    assert text.count("kemungkinan") + text.count("Kemungkinan") >= 2
    assert "budidaya" in text and "populasi" not in text


def test_same_input_identical_claims_and_fingerprint(rules, ref, report):
    again = run(MINI / "bacaan_lebar.csv", MINI / "metadata.csv", MINI / "taksonomi.csv",
                rules=rules, reference=ref)
    pd.testing.assert_frame_equal(report.claims, again.claims)
    assert report.fingerprint == again.fingerprint


def test_summary_sentence(report):
    s = report.summary_sentence()
    assert s.startswith(f"Dari {len(report.claims)} klaim,") and "tidak dikenal" in s


def test_external_reference_refused_for_indonesian_project(rules, ref):
    import copy
    foreign = copy.copy(ref)
    foreign.meta = dict(ref.meta, jenis="uji_luar")
    with pytest.raises(ReferenceSeparationError):
        run(MINI / "bacaan_lebar.csv", MINI / "metadata.csv", MINI / "taksonomi.csv", rules=rules, reference=foreign)
