from naf.measure import _band


def test_band_rare_below_half_percent():
    assert _band(0.001) == "rare"
    assert _band(0.00499) == "rare"


def test_band_occasional_between_half_and_five_percent():
    assert _band(0.005) == "occasional"
    assert _band(0.02) == "occasional"
    assert _band(0.05) == "occasional"


def test_band_common_above_five_percent():
    assert _band(0.0501) == "common"
    assert _band(0.5) == "common"
