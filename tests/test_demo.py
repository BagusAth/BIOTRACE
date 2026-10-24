import random
import sys

import pandas as pd
import pytest

from biotrace.config import ROOT, find_blast_tool
from biotrace.pipeline import run
from biotrace.report import barcode_priority

DEMO = ROOT / "data" / "demo" / "matano"
needs_blast = pytest.mark.skipif(find_blast_tool("blastn") is None, reason="BLAST+ tidak terpasang")


@pytest.fixture(scope="module")
def demo():
    return run(DEMO / "bacaan.csv", DEMO / "metadata.csv", DEMO / "taksonomi.csv", DEMO / "asv.fasta")


def test_demo_files_are_labelled_simulation():
    for name in ("bacaan.csv", "metadata.csv", "taksonomi.csv"):
        df = pd.read_csv(DEMO / name, dtype=str)
        assert (df["label_data"] == "SIMULASI").all(), name
    meta = pd.read_csv(DEMO / "metadata.csv", dtype=str)
    assert meta["sample_id"].str.startswith("SIM-").all()
    headers = [line for line in (DEMO / "asv.fasta").read_text(encoding="utf-8").splitlines() if line.startswith(">")]
    assert headers and all("SIMULASI" in h for h in headers)
    assert "SIMULASI" in (DEMO / "README.md").read_text(encoding="utf-8")


def test_demo_design_three_stations_three_replicates_one_control_per_batch():
    meta = pd.read_csv(DEMO / "metadata.csv", dtype=str)
    samples = meta[meta["sample_type"] == "sampel"]
    assert samples.groupby("site_id")["replicate"].nunique().tolist() == [3, 3, 3]
    controls = meta[meta["sample_type"] == "kontrol_negatif_pcr"]
    assert sorted(controls["extraction_batch"]) == sorted(samples["extraction_batch"].unique())


@needs_blast
def test_demo_regenerates_identically(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_demo
    monkeypatch.setattr(make_demo, "OUT", tmp_path)
    make_demo.build_files(random.Random(make_demo.SEED))
    for name in ("asv.fasta", "bacaan.csv", "metadata.csv", "taksonomi.csv"):
        assert (tmp_path / name).read_bytes() == (DEMO / name).read_bytes(), name


@needs_blast
def test_demo_shows_every_rule_branch(demo):
    assert demo.simulation
    c = demo.claims.set_index("claim_id")
    s = demo.summary
    assert all(s[k] > 0 for k in ("aman dilaporkan", "dengan catatan", "wajib verifikasi", "jangan dipakai",
                                  "tidak dikenal"))
    assert "kemungkinan louhan hibrida" in c.loc["asv05@MTN-ST1", "label_L3"]
    assert c.loc["asv04@MTN-ST1", "nilai"] == "D" and "kontrol negatif" in c.loc["asv04@MTN-ST1", "batas_diterapkan"]
    assert c.loc["asv07@MTN-ST2", "taxon_dilaporkan"] == "Telmatherina"
    assert c.loc["asv07@MTN-ST2", "keputusan"] == "wajib verifikasi" and "referensi" in c.loc["asv07@MTN-ST2", "penyebab"]
    assert c.loc["asv08@MTN-ST1", "tingkat"] == "tidak dikenal" and c.loc["asv08@MTN-ST1", "keputusan"] == "dengan catatan"
    assert c.loc["asv09@MTN-ST3", "taxon_dilaporkan"] == "Oryzias" and "marker" in c.loc["asv09@MTN-ST3", "penyebab"]
    assert c.loc["asv10@MTN-ST2", "keputusan"] == "jangan dipakai"
    assert "keramba" in c.loc["asv01@MTN-ST2", "asal_usul"]
    assert barcode_priority(demo)["target"].str.contains("ASV asv08").any()


@needs_blast
def test_demo_fingerprint_is_stable(demo):
    again = run(DEMO / "bacaan.csv", DEMO / "metadata.csv", DEMO / "taksonomi.csv", DEMO / "asv.fasta")
    assert again.fingerprint == demo.fingerprint
    assert demo.manifest.get("label_data") == "SIMULASI"


@needs_blast
def test_app_demo_button():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    demo_button = next(b for b in at.button if "demo" in b.label.lower())
    demo_button.click().run()
    assert not at.exception
    assert at.session_state["report"].simulation
    assert "SIMULASI" in at.title[0].value
