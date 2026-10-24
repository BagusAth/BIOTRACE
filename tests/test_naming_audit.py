import copy
from pathlib import Path

import pytest

from biotrace.audit import audit_claims, audit_l4, score_l1
from biotrace.config import find_blast_tool, load_rules
from biotrace.io import load_project
from biotrace.naming import Hit, lab_hits, name_asv, name_project
from biotrace.reference import load_reference, read_fasta

MINI = Path(__file__).parent / "fixtures" / "mini"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def ref():
    return load_reference()


def hit(species, pident, acc=None, validated=True, recorded="ya", genus=None, family="Fam", resolved=True):
    return Hit(accession=acc or f"{species}-{pident}", species=species, species_key=species,
               genus=genus or species.split()[0], family=family, pident=pident, bitscore=pident * 3,
               resolved=resolved, validated=validated, recorded=recorded)


# ---- aturan penamaan (data kecil buatan) ----------------------------------------------
def test_two_identical_species_reported_as_genus_marker(rules):
    n = name_asv("a", [hit("Oryzias celebensis", 100.0), hit("Oryzias woworae", 100.0)], rules)
    assert (n.taxon, n.rank, n.causes) == ("Oryzias", "genus", ["marker"])
    assert n.near_species == ["Oryzias celebensis", "Oryzias woworae"]


def test_below_95_is_unknown(rules):
    n = name_asv("a", [hit("Telmatherina celebensis", 93.0), hit("Marosatherina ladigesi", 88.0)], rules)
    assert (n.taxon, n.rank, n.causes) == ("tidak dikenal", "tidak dikenal", ["referensi"])
    assert n.taxon_lab == "Telmatherina celebensis"


def test_species_not_recorded_in_indonesia_drops_to_genus_location(rules):
    n = name_asv("a", [hit("Oryzias latipes", 100.0, recorded="tidak"), hit("Oryzias sakaizumii", 97.0)], rules)
    assert (n.taxon, n.rank, n.causes) == ("Oryzias", "genus", ["lokasi"])


def test_identity_between_95_and_98_is_genus_reference(rules):
    n = name_asv("a", [hit("Telmatherina celebensis", 96.5)], rules)
    assert (n.taxon, n.rank, n.causes) == ("Telmatherina", "genus", ["referensi"])


def test_unvalidated_reference_cannot_support_species(rules):
    n = name_asv("a", [hit("Telmatherina celebensis", 100.0, validated=False)], rules)
    assert (n.taxon, n.rank, n.causes) == ("Telmatherina", "genus", ["referensi"])


def test_validated_single_species_named(rules):
    n = name_asv("a", [hit("Channa striata", 100.0), hit("Channa limbata", 96.0)], rules)
    assert (n.taxon, n.rank, n.causes) == ("Channa striata", "spesies", [])
    assert n.gap == 4.0


def test_near_hits_across_genera_go_to_family(rules):
    n = name_asv("a", [hit("Telmatherina celebensis", 99.8, family="Telmatherinidae"),
                       hit("Marosatherina ladigesi", 99.6, family="Telmatherinidae")], rules)
    assert (n.taxon, n.rank, n.causes) == ("Telmatherinidae", "famili", ["marker"])


def test_unresolved_name_in_near_hits_blocks_species(rules):
    n = name_asv("a", [hit("Oreochromis niloticus", 100.0),
                       hit("Oreochromis sp. 'red tilapia'", 99.8, resolved=False)], rules)
    assert n.rank == "genus" and n.taxon == "Oreochromis"


def test_lab_taxonomy_mode(ref, rules):
    row = {"taxon": "Oreochromis niloticus", "pct_identity": "100", "runner_up_taxon": "Oreochromis aureus",
           "runner_up_pct_identity": "97.6"}
    n = name_asv("asv01", lab_hits(row, ref), rules, source="database lab")
    assert n.rank == "spesies" and n.taxon == "Oreochromis niloticus"
    assert "dinilai dengan database lab" in n.notes


def test_deterministic_tie_order(rules):
    hits = [hit("Oryzias woworae", 100.0, acc="B"), hit("Oryzias celebensis", 100.0, acc="A")]
    assert name_asv("a", hits, rules).taxon_lab == name_asv("a", list(reversed(hits)), rules).taxon_lab == "Oryzias celebensis"


# ---- audit ------------------------------------------------------------------------------
def _project(rules):
    return load_project(MINI / "bacaan_lebar.csv", MINI / "metadata.csv", MINI / "taksonomi.csv",
                        rules=rules, reference_lakes=["Matano", "Mahalona", "Towuti"])


def test_l4_scores_and_caps(rules):
    l4 = audit_l4(_project(rules), rules).set_index(["asv_id", "site_id"])
    assert l4.loc[("asv01", "ST1"), "skor_L4"] == 2           # 3 dari 3
    assert l4.loc[("asv01", "ST2"), "skor_L4"] == 0           # 1 dari 3
    assert l4.loc[("asv04", "ST1"), "replikat_positif"] == 2
    assert "semua bacaan di bawah 10" in l4.loc[("asv04", "ST1"), "batas_D"]
    # asv03 ada di kontrol negatif batch B1, batch yang sama dengan ST1
    assert "kontrol negatif batch yang sama" in l4.loc[("asv03", "ST1"), "batas_D"]
    assert l4.loc[("asv02", "ST2"), "status_kontrol"] == "tanpa_kontrol"


def test_tag_jump_reads_discarded(rules):
    strict = copy.deepcopy(rules)
    strict["l4"]["tag_jump_fraction"] = 0.01      # ambang 15,2 bacaan untuk asv01
    l4 = audit_l4(_project(strict), strict).set_index(["asv_id", "site_id"])
    assert l4.loc[("asv01", "ST2"), "replikat_positif"] == 0
    assert l4.loc[("asv01", "ST2"), "bacaan_nyasar_dibuang"] == 1


def test_l1_completeness_penalty(ref, rules):
    n = name_asv("a", [hit("Telmatherina celebensis", 100.0, validated=True)], rules)
    comp = ref.completeness_for("Telmatherina", "Matano")
    l1 = score_l1(n, comp, rules)
    assert l1["skor_L1_mentah"] == 2 and l1["potongan_kelengkapan"] == 1 and l1["skor_L1"] == 1
    assert "9 dari 9 spesies Telmatherina" in l1["alasan_L1_id"]


def test_louhan_parent_labelled(ref, rules):
    n = name_asv("a", [hit("Amphilophus citrinellus", 100.0, family="Cichlidae")], rules)
    labels = ref.l3_labels(n.taxon, n.rank, "Matano")
    assert "kemungkinan louhan hibrida" in labels and "invasif" in labels


def test_audit_claims_lab_mode(ref, rules):
    project = _project(rules)
    namings, _ = name_project(project, ref, rules)
    claims = audit_claims(project, namings, ref, rules).set_index("claim_id")
    c = claims.loc["asv01@ST1"]
    assert c["taxon_dilaporkan"] == "Oreochromis niloticus" and c["skor_L1"] == 2 and c["skor_L2"] == 1
    assert "invasif" in c["label_L3"]
    assert claims.loc["asv02@ST2", "tingkat"] == "genus"          # 97,1% -> genus, referensi
    assert claims.loc["asv04@ST1", "tingkat"] == "tidak dikenal"  # 92% -> tidak dikenal


@pytest.mark.skipif(find_blast_tool("blastn") is None, reason="BLAST+ tidak terpasang")
def test_blast_naming_on_reference_sequence(ref, rules, tmp_path):
    seqs = read_fasta(ref.root / "ref12S.fasta")
    acc = ref.taxonomy[(ref.taxonomy["spesies"] == "Channa striata") &
                       (ref.taxonomy["status_validasi"] == "tervalidasi")]["aksesi"].iloc[0]
    query = seqs[acc][200:380]
    fasta = tmp_path / "asv.fasta"
    fasta.write_text(f">asvX\n{query}\n", encoding="utf-8")
    reads = tmp_path / "bacaan.csv"
    reads.write_text("asv_id,sample_id,reads\nasvX,S1A,100\n", encoding="utf-8")
    project = load_project(reads, MINI / "metadata.csv", fasta=fasta, rules=rules)
    namings, notes = name_project(project, ref, rules)
    n = namings["asvX"]
    assert not notes
    assert n.best_identity == 100.0 and n.taxon.startswith("Channa")


@pytest.mark.parametrize("raw,acc", [("gb|MN057622|", "MN057622"), ("lcl|AP006772", "AP006772"),
                                     ("MN057622.1", "MN057622"), ("AB021894", "AB021894")])
def test_accession_parsing(raw, acc):
    from biotrace.naming import accession_of
    assert accession_of(raw) == acc


def test_l4_without_any_negative_control(rules, tmp_path):
    reads = tmp_path / "bacaan.csv"
    reads.write_text("asv_id,sample_id,reads\na1,S1,50\na1,S2,40\n", encoding="utf-8")
    meta = tmp_path / "metadata.csv"
    meta.write_text("sample_id,site_id,sample_type,replicate,extraction_batch\nS1,X,sampel,1,\nS2,X,sampel,2,\n",
                    encoding="utf-8")
    l4 = audit_l4(load_project(reads, meta, rules=rules), rules)
    assert l4.iloc[0]["status_kontrol"] == "tanpa_kontrol" and l4.iloc[0]["replikat_positif"] == 2
