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
