import pandas as pd
import pytest

from biotrace.config import find_blast_tool, sha256_file
from biotrace.reference import compute_completeness, load_reference
from biotrace.taxonomy import same_species_name, species_key


@pytest.fixture(scope="module")
def ref():
    return load_reference()


@pytest.mark.parametrize("name,key,resolved", [
    ("Channa striata", "Channa striata", True),
    ("Anguilla australis australis", "Anguilla australis", True),
    ("Cyprinus carpio 'longfin'", "Cyprinus carpio", True),
    ("Oreochromis sp. 'red tilapia'", "Oreochromis sp. 'red tilapia'", False),
    ("Glossogobius cf. aureus CMH-2014", "Glossogobius cf. aureus CMH-2014", False),
    ("Paraneetroplus synspilus x Amphilophus citrinellus", "Paraneetroplus synspilus x Amphilophus citrinellus", False),
    ("louhan hibrida", "louhan hibrida", False),
])
def test_species_key(name, key, resolved):
    assert species_key(name) == (key, resolved)


def test_same_species_name_tolerates_epithet_ending():
    assert same_species_name("Cyprinus multitaeniata", "Cyprinus multitaeniatus")
    assert not same_species_name("Anguilla bicolor", "Anguilla pacifica")


def test_every_sequence_has_species_recorded_and_validation(ref):
    t = ref.taxonomy
    assert len(t) == 896
    assert (t["spesies"] != "").all()
    assert set(t["tercatat_di_indonesia"]) <= {"ya", "tidak", "belum dicek"}
    assert set(t["status_validasi"]) <= {"tervalidasi", "belum tervalidasi"}
    assert (t["sumber"] != "").all() and (t["status_voucher"] != "").all()
    # hanya sekuens bernama spesies dengan voucher yang boleh tervalidasi
    val = t[t["status_validasi"] == "tervalidasi"]
    assert (val["specimen_voucher"] != "").all() and (val["terselesaikan"] == "ya").all()


def test_completeness_reproduces_audit_finding(ref):
    cov = pd.read_csv(ref.root / "kelengkapan_spesies.csv", dtype=str)
    endemic = cov[cov["status_di_malili"] == "endemik"]
    assert len(endemic) == 19
    assert (endemic["ada_referensi"] == "ya").sum() == 1
    assert endemic.loc[endemic["ada_referensi"] == "ya", "spesies"].tolist() == ["Telmatherina celebensis"]


def _tax(validated: bool) -> pd.DataFrame:
    return pd.DataFrame({
        "spesies_kunci": ["Telmatherina celebensis", "Oreochromis niloticus"],
        "status_validasi": ["tervalidasi" if validated else "belum tervalidasi", "tervalidasi"],
    })


@pytest.mark.parametrize("validated,p", [(True, 0.8889), (False, 1.0)])
def test_completeness_formula(ref, validated, p):
    comp = compute_completeness(ref.checklist, _tax(validated), ref.region, ref.lakes)
    row = comp[(comp["wilayah"] == ref.region) & (comp["genus"] == "Telmatherina")].iloc[0]
    assert row["n_checklist"] == 9
    assert row["p_belum_di_kamus"] == p


def test_completeness_lookup_uses_region_scope(ref):
    c = ref.completeness_for("Telmatherina", "Matano", scope="wilayah")
    assert c["wilayah"] == "Kompleks Malili" and c["n"] == 9
    c_lake = ref.completeness_for("Telmatherina", "Matano", scope="danau")
    assert c_lake["wilayah"] == "Matano" and c_lake["n"] == 6
    assert ref.completeness_for("Salmo", "Matano") is None


def test_louhan_alias_labels(ref):
    assert ref.alias_of("Amphilophus citrinellus") == ["louhan hibrida"]
    assert ref.alias_of("Paraneetroplus synspilus x Amphilophus citrinellus") == ["louhan hibrida"]
    labels = ref.l3_labels("Amphilophus citrinellus", "spesies", "Matano")
    assert "kemungkinan louhan hibrida" in labels and "invasif" in labels
    assert ref.checklist_hit("Amphilophus citrinellus", "spesies", "Matano") == (True, "alias: louhan hibrida")


def test_l3_endemic_and_threatened(ref):
    assert ref.l3_labels("Telmatherina wahjui", "spesies", "Matano") == ["endemik", "terancam"]
    assert "kemungkinan endemik di luar kamus" in ref.l3_labels("Telmatherina", "genus", "Matano")
    assert ref.l3_labels("Oreochromis", "genus", "Matano") == ["invasif"]


def test_checklist_by_lake(ref):
    assert ref.checklist_hit("Telmatherina celebensis", "spesies", "Towuti")[0]
    assert not ref.checklist_hit("Telmatherina celebensis", "spesies", "Matano")[0]
    # baris tingkat wilayah berlaku di semua danau
    assert ref.checklist_hit("Clarias gariepinus", "spesies", "Matano")[0]


def test_reference_files_hashed(ref):
    lines = (ref.root / "manifest_sha256.txt").read_text(encoding="utf-8").splitlines()
    for line in lines:
        digest, name = line.split("  ", 1)
        assert sha256_file(ref.root / name) == digest, name
    assert len(ref.fingerprint) == 64 and ref.label.startswith("ref12S v0.1 (sha256:")


@pytest.mark.skipif(find_blast_tool("makeblastdb") is None, reason="BLAST+ tidak terpasang")
def test_blast_db_builds(ref):
    db = ref.ensure_blast_db()
    assert db is not None and (db.parent / (db.name + ".nsq")).exists()
