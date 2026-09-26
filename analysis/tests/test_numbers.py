import json
import os

import pytest

from analysis import data, numbers


def test_formatting():
    assert numbers.f3(0.39611650485436894) == "0.396"
    assert numbers.count(14976) == "14,976"
    assert numbers.pct(0.002) == "0.2%"
    assert numbers.ci(0.35479, 0.43897) == "[0.355, 0.439]"
    assert numbers.clean(float("nan")) is None
    assert numbers.clean(0.1 + 0.2) == 0.3


def test_rate_writes_value_counts_and_interval():
    R = numbers.Registry()
    R.rate("x", 0, 81, "src", "how")
    assert R.d["x"]["text"] == "0.000"
    assert R.d["x.ci"]["text"] == "[0.000, 0.045]"
    assert (R.d["x.k"]["value"], R.d["x.n"]["value"]) == (0, 81)
    with pytest.raises(SystemExit):
        R.put("x", 1, "1", "src", "how")


@pytest.mark.skipif(not all(os.path.exists(os.path.join(data.RESULTS, f))
                            for f in ("hypotheses.json", "protocols.json")),
                    reason="results/hypotheses.json and protocols.json not written yet")
def test_build_is_deterministic_and_every_entry_is_complete():
    a = numbers.build()
    b = numbers.build()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    for k, v in a.items():
        assert set(v) == {"value", "text", "source", "how"}, k
        assert isinstance(v["text"], str) and v["text"], k
        assert "{{" not in v["text"], k


def test_committed_registry_has_no_long_dash():
    path = os.path.join(data.RESULTS, "numbers.json")
    if not os.path.exists(path):
        pytest.skip("numbers.json not written yet")
    text = open(path, encoding="utf-8").read()
    assert chr(0x2014) not in text and chr(0x2013) not in text
    # ensure_ascii writes a long dash as an escape: read the decoded values too
    for k, v in json.load(open(path, encoding="utf-8")).items():
        s = json.dumps(v, ensure_ascii=False)
        assert chr(0x2014) not in s and chr(0x2013) not in s, k


def test_dossier_rate_recovers_the_count_and_refuses_a_fraction():
    R = numbers.Registry()
    numbers.dossier_rate(R, "d", {"dossier_fpr": 13 / 18, "n_dossiers": 18}, "src", "how")
    assert (R.d["d.k"]["value"], R.d["d.n"]["value"]) == (13, 18)
    with pytest.raises(SystemExit):
        numbers.dossier_rate(R, "e", {"dossier_fpr": 0.5, "n_dossiers": 7}, "src", "how")


def test_census_tool_status_counts_only_objective_and_human_tiers():
    sheet = [
        {"episode_id": "a1", "repo": "a", "tier": "T-A"},
        {"episode_id": "a2", "repo": "a", "tier": "T-C"},
        {"episode_id": "b1", "repo": "b", "tier": "T-A"},
        {"episode_id": "b2", "repo": "b", "tier": "T-B"},
        {"episode_id": "c1", "repo": "c", "tier": "T-C"},
    ]
    first = {"a1": "M0", "a2": "M1", "b1": "M0", "b2": "M3", "c1": "M1"}
    status, contra = numbers.census_tool_status(sheet, first)
    # a: its only contradiction is tier C, so it agrees on T-A and T-B
    assert status == {"a": "agree", "b": "contradicted", "c": "no objective or human episode"}
    assert contra == ["b2"]
    status, contra = numbers.census_tool_status(sheet, first, tiers=("T-A", "T-B", "T-C"))
    assert status["a"] == "contradicted" and sorted(contra) == ["a2", "b2", "c1"]


def test_protocol_extra_numbers_flags_the_domain_fallback():
    P = {"protocols": {"PX": {"folds": [
        {"fold": "PX", "status": "run", "domain": 96,
         "domain_attempts": [[96, 0.0], [150, 0.0]], "rules": {}},
        {"fold": "PX/k=1", "status": "run", "domain": 300,
         "domain_attempts": [[96, 0.2], [300, 1.0]], "rules": {}}]}}}
    R = numbers.Registry()
    numbers.protocol_extra_numbers(R, P)
    assert R.d["protocol.PX.domain_fallback"]["text"] == "yes"
    assert R.d["protocol.PX.k_1.domain_fallback"]["text"] == "no"
    assert R.d["protocol.PX.k_1.domain_attempts"]["text"] == "96 dpi 0.200, 300 dpi 1.000"


def test_pct_short():
    assert numbers.pct_short(0.005) == "0.5%"
    assert numbers.pct_short(0.01) == "1%"
    assert numbers.pct_short(0.0005) == "0.05%"
    assert numbers.pct_short(0.002) == "0.2%"


def test_design_numbers_read_the_code():
    R = numbers.Registry()
    numbers.design_numbers(R)
    assert R.d["design.h1_ink_min"]["text"] == "0.5%"
    assert R.d["design.no_ink_max"]["text"] == "0.05%"
    assert R.d["design.cal_seeds"]["text"] == "11 and 23"
    assert R.d["design.report_seed"]["text"] == "37"
    assert R.d["design.release_gate"]["text"] == "0.90"
    assert R.d["design.bootstrap_resamples"]["text"] == "10,000"
    assert R.d["design.a4.level.0.01"]["text"] == "1%"
    assert R.d["design.naf_comment_min"]["text"] == "1%"
    assert R.d["design.ci_level"]["text"] == "95%"


def test_census_quote_numbers_every_pattern_matches_and_a_miss_fails():
    R = numbers.Registry()
    numbers.census_quote_numbers(R)
    assert len([k for k in R.d if k.startswith("census.q.")]) == len(numbers.CENSUS_QUOTE_NUMBERS)
    assert R.d["census.q.blazonry-01-rejected-marks-pass-gate.pass"]["text"] == "13"
    assert R.d["census.q.dsh-internals-01-existence-only-validator.found"]["text"] == "44"
    sheet = [{"episode_id": e, "self_generated_claim": "", "independent_finding": ""}
             for e, _s, _n, _p in numbers.CENSUS_QUOTE_NUMBERS]
    with pytest.raises(SystemExit):
        numbers.census_quote_numbers(numbers.Registry(), sheet=sheet)


def test_disclosure_counts_match_the_plan_commands():
    import subprocess
    R = numbers.Registry()
    numbers.disclosure_numbers(R)
    if "disclosure.dp.commits" not in R.d:
        pytest.skip("dossier-preflight has no tag v0.2.0")
    log = subprocess.run(["git", "-C", data.DP, "log", "v0.2.0",
                          "--format=%(trailers:key=Co-Authored-By,valueonly)"],
                         capture_output=True, text=True, check=True).stdout
    assert R.d["disclosure.dp.claude_commits"]["value"] == log.count("Claude")
    assert 0 < R.d["disclosure.dp.claude_commits"]["value"] <= R.d["disclosure.dp.commits"]["value"]
