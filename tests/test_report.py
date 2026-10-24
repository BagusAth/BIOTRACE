import io
import sys
from pathlib import Path

import pandas as pd
import pytest
from pypdf import PdfReader

from biotrace.config import ROOT, find_blast_tool, load_rules
from biotrace.pipeline import run
from biotrace.reference import load_reference
from biotrace.report import barcode_priority, build_pdf, cards_for_pdf, claims_csv, evidence_card, write_outputs

MINI = Path(__file__).parent / "fixtures" / "mini"


@pytest.fixture(scope="module")
def report():
    return run(MINI / "bacaan_lebar.csv", MINI / "metadata.csv", MINI / "taksonomi.csv",
               rules=load_rules(), reference=load_reference(), simulation=True)


def pdf_text(data: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(data)).pages)


def test_csv_matches_app_table(report):
    back = pd.read_csv(io.BytesIO(claims_csv(report)), dtype=str, keep_default_na=False)
    assert list(back.columns) == list(report.claims.columns)
    assert back["claim_id"].tolist() == report.claims["claim_id"].tolist()
    assert back["keputusan"].tolist() == report.claims["keputusan"].tolist()


def test_pdf_opens_and_matches_summary(report):
    text = " ".join(pdf_text(build_pdf(report)).split())
    assert "SIMULASI" in text
    assert report.summary_sentence() in text
    assert "Deteksi DNA bukan bukti pasti ikan hidup di lokasi." in text
    assert report.fingerprint in text.replace(" ", "")
    for claim_id in cards_for_pdf(report)["claim_id"]:
        assert claim_id in text


def test_pdf_is_reproducible(report):
    assert build_pdf(report) == build_pdf(report)


def test_unknown_claims_in_barcode_priority(report):
    prio = barcode_priority(report)
    unknown_asvs = set(report.claims.loc[report.claims["tingkat"] == "tidak dikenal", "asv_id"])
    assert unknown_asvs
    for asv in unknown_asvs:
        assert prio["target"].str.contains(f"ASV {asv}").any()
    # celah kamus: Telmatherina tanpa referensi tervalidasi, endemik di atas bila jumlah sama
    assert prio["target"].str.contains("Telmatherina").any()
    counts = prio["jumlah_klaim_terdampak"].tolist()
    assert counts == sorted(counts, reverse=True)


def test_card_has_four_outputs_and_limit(report):
    row = report.claims.iloc[0].to_dict()
    card = evidence_card(row, report)
    assert card["simulasi"] and card["judul"].startswith("SIMULASI")
    assert {"tingkat", "nilai", "peluang", "penyebab"} <= set(card)
    assert len(card["alasan"]) == 4 and all(r[1] and r[2] for r in card["alasan"])
    assert card["batas_interpretasi"][0] == "Deteksi DNA bukan bukti pasti ikan hidup di lokasi."


def test_write_outputs(report, tmp_path):
    paths = write_outputs(report, tmp_path)
    for p in paths.values():
        assert p.exists() and p.stat().st_size > 0


def test_streamlit_app_pages(report):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["report"] = report
    at.run()
    assert not at.exception
    assert "SIMULASI" in at.title[0].value
    for page in ["2. Ringkasan keputusan", "3. Tabel klaim", "4. Evidence Card", "5. Peta celah"]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page


@pytest.mark.skipif(find_blast_tool("blastn") is None, reason="BLAST+ tidak terpasang")
def test_200_samples_2000_asvs_under_two_minutes():
    sys.path.insert(0, str(ROOT / "scripts"))
    from benchmark import benchmark
    report = benchmark(200, 2000)
    assert report.seconds < 120
    assert len(report.claims) > 0
