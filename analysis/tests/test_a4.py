import os

import pytest

from analysis import a4, data


def test_level_tag():
    assert [a4.level_tag(x) for x in a4.LEVELS] == ["0", "0.002", "0.01", "0.04"]


def test_tally_pools_and_splits_by_shape():
    scored = [
        ("required_field", 0.0, None, "variant", True),
        ("required_field", 0.0, None, "variant", True),
        ("required_field", 0.01, "fold", "variant", True),
        ("required_field", 0.01, "speck", "variant", False),
        ("required_field", 0.01, "stroke", "variant", False),
        ("required_field", 0.01, "fold", "clean", False),
        ("expiry", 0.04, "stroke", "variant", True),
    ]
    t = a4.tally(scored)
    rf = t["required_field"]
    assert rf["pooled"]["variant"] == {0.0: [2, 2], 0.01: [1, 3]}
    assert rf["pooled"]["clean"] == {0.01: [0, 1]}
    assert rf["by_shape"]["fold"]["variant"] == {0.01: [1, 1]}
    assert rf["by_shape"]["speck"]["variant"] == {0.01: [0, 1]}
    # level 0 carries no shape: it never enters by_shape
    assert all(0.0 not in d.get("variant", {}) for d in rf["by_shape"].values())
    assert t["expiry"]["pooled"]["variant"] == {0.04: [1, 1]}


@pytest.mark.skipif(data.arm_path("A4") is None or not os.path.isdir(data.DP),
                    reason="A4 or dossier-preflight not on disk")
def test_a4_required_field_matches_figure1_and_the_shape_reading():
    t = a4.compute()["required_field"]
    assert t["pooled"]["variant"] == {0.0: [81, 81], 0.002: [54, 81], 0.01: [27, 81],
                                      0.04: [0, 81]}
    s = t["by_shape"]
    assert s["fold"]["variant"] == {0.002: [27, 27], 0.01: [27, 27], 0.04: [0, 27]}
    assert s["speck"]["variant"] == {0.002: [27, 27], 0.01: [0, 27], 0.04: [0, 27]}
    assert s["stroke"]["variant"] == {0.002: [0, 27], 0.01: [0, 27], 0.04: [0, 27]}
