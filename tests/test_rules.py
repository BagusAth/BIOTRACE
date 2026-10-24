import pytest

from biotrace.config import grade_for_score, load_rules


def test_rules_v01_loads():
    rules = load_rules()
    assert rules.version == "0.1"
    assert len(rules.sha256) == 64
    assert rules["naming"]["near_hit_delta_pct"] == 0.5
    assert rules["naming"]["species_min_identity"] == 98.0
    assert rules["naming"]["unknown_below_identity"] == 95.0
    assert rules["l4"]["replicates"] == 3
    assert rules["l4"]["min_total_reads"] == 10


@pytest.mark.parametrize("score,grade", [(5, "A"), (4, "B"), (3, "C"), (2, "C"), (1, "D"), (0, "D")])
def test_grade_map(score, grade):
    assert grade_for_score(load_rules(), score) == grade


def test_rules_missing_section(tmp_path):
    bad = tmp_path / "rules_bad.yaml"
    bad.write_text('version: "x"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="tidak memuat bagian"):
        load_rules(bad)
