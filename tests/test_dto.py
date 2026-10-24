import json
from collections import Counter
from pathlib import Path

import pytest

from biotrace.__main__ import main as cli
from biotrace.config import ROOT, find_blast_tool, load_rules
from biotrace.dto import SCHEMA, report_to_dto
from biotrace.pipeline import DECISIONS, run
from biotrace.reference import load_reference

MINI = Path(__file__).parent / "fixtures" / "mini"
DEMO = ROOT / "data" / "demo" / "matano"
needs_blast = pytest.mark.skipif(find_blast_tool("blastn") is None, reason="BLAST+ tidak terpasang")


def _mini(**kw):
    return run(MINI / "bacaan_lebar.csv", MINI / "metadata.csv", MINI / "taksonomi.csv",
               rules=load_rules(), reference=load_reference(), **kw)


@pytest.fixture(scope="module")
def mini_dto():
    return report_to_dto(_mini(), processed_at="2026-10-24T22:00:00+07:00")


def test_contract_top_level(mini_dto):
    assert mini_dto["schema"] == SCHEMA
    assert set(mini_dto) == {"schema", "meta", "ringkasan", "penyebab", "berkas", "informasi_hilang", "klaim",
                             "kartu", "celah", "prioritas_barcode", "nama_ilmiah", "ekspor"}
    json.dumps(mini_dto, allow_nan=False)   # tanpa NaN supaya terbaca JSON.parse di browser


def test_counts_match_claims_table(mini_dto):
    report = _mini()
    c = report.claims
    assert mini_dto["meta"]["jumlah_klaim"] == len(c) == len(mini_dto["klaim"])
    by_decision = Counter(k["keputusan"] for k in mini_dto["klaim"])
    for d in DECISIONS:
        assert mini_dto["ringkasan"]["jumlah"][d] == by_decision[d] == int((c["keputusan"] == d).sum())
    for cause in mini_dto["penyebab"]:
        assert cause["jumlah"] == int(c["penyebab"].str.split("; ").map(lambda x: cause["kode"] in x).sum())
    assert mini_dto["ringkasan"]["kalimat"] == report.summary_sentence()


def test_every_claim_has_bilingual_card(mini_dto):
    assert [k["id"] for k in mini_dto["klaim"]] == list(mini_dto["kartu"])
    for claim in mini_dto["klaim"]:
        card = mini_dto["kartu"][claim["id"]]
        assert [r["lapisan"] for r in card["alasan"]] == ["penamaan", "L1", "L2", "L4"]
        assert all(r["id"] and r["en"] for r in card["alasan"])
        assert card["keluaran"]["nilai"] == claim["nilai"]
    unknown = next(k for k in mini_dto["klaim"] if k["tingkat"] == "tidak dikenal")
    assert mini_dto["kartu"][unknown["id"]]["alasan"][2]["skor"] is None   # L2 tidak dinilai


def test_files_and_issues(mini_dto):
    report = _mini()
    assert {f["nama"]: f["sha256"] for f in mini_dto["berkas"]} == {f.name: f.sha256 for f in report.project.files}
    assert any("batch B2 tanpa kontrol negatif" in i["masalah"] for i in mini_dto["informasi_hilang"])
    assert mini_dto["berkas"][0]["deskripsi"].startswith("tabel bacaan, format lebar")


def test_project_name_is_display_only():
    a, b = _mini(project_name="Proyek A"), _mini(project_name="Proyek B")
    assert a.fingerprint == b.fingerprint
    assert report_to_dto(a)["meta"]["proyek"] == "Proyek A"


def test_cli_writes_report_json(tmp_path):
    cli(["run", "--reads", str(MINI / "bacaan_lebar.csv"), "--metadata", str(MINI / "metadata.csv"),
         "--taxonomy", str(MINI / "taksonomi.csv"), "--out", str(tmp_path), "--json", "--project-name", "Uji"])
    dto = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert dto["meta"]["proyek"] == "Uji" and dto["meta"]["diproses"]
    for name in dto["ekspor"].values():
        assert (tmp_path / name).exists(), name


@needs_blast
def test_demo_contract_values():
    dto = report_to_dto(run(DEMO / "bacaan.csv", DEMO / "metadata.csv", DEMO / "taksonomi.csv", DEMO / "asv.fasta"))
    assert dto["meta"]["simulasi"] and dto["meta"]["jumlah_stasiun"] == 3
    groups = {g["label"]: g for g in dto["celah"]["kelompok"]}
    tel = groups["Telmatherinidae endemik"]
    assert (tel["total"], tel["ada_sekuens"], tel["tervalidasi"]) == (15, 1, 0)
    assert dto["celah"]["judul"].startswith("1 dari 19 ikan endemik")
    card = dto["kartu"]["asv01@MTN-ST2"]
    assert "keramba" in card["asal_usul"]["fasilitas"] and card["asal_usul"]["status"].startswith("Status di Matano")
    assert dto["kartu"]["asv04@MTN-ST1"]["keluaran"]["skor"] == "5/5 → D"
    assert "Telmatherina celebensis" in dto["nama_ilmiah"] and "Telmatherina" in dto["nama_ilmiah"]
