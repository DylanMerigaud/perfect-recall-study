"""Coordinate-transform math in naf/registration.py that needs no image and no preflight import:
turn_point (quarter-turn point mapping) and the canonical<->original affine coefficients.

pick_medoid, register_group and field_ink_rows need dossier-preflight's own code and real images;
those are exercised by naf/README.md's rerun recipe under $DP/.venv/bin/python, not here.
"""
import numpy as np
import pytest

from naf.registration import (
    _affine_canonical_from_original,
    pick_medoid,
    turn_point,
)


def test_turn_point_identity_at_quarter_turns_zero():
    assert turn_point(3, 7, 0, orig_w=20, orig_h=10) == (3, 7)


def test_turn_point_180_matches_numpy_rot90_minus_two():
    h, w = 4, 6
    a = np.arange(h * w).reshape(h, w)
    turned = np.rot90(a, k=-2)
    for y in range(h):
        for x in range(w):
            xt, yt = turn_point(x, y, 2, orig_w=w, orig_h=h)
            assert turned[yt, xt] == a[y, x]


def test_turn_point_unsupported_quarter_turns_raises():
    with pytest.raises(ValueError):
        turn_point(0, 0, 1, orig_w=10, orig_h=10)


class _FakeReg:
    def __init__(self, quarter_turns, scale, dx, dy):
        self.quarter_turns = quarter_turns
        self.scale = scale
        self.dx = dx
        self.dy = dy


def _forward_point(x, y, reg, orig_w, orig_h):
    xt, yt = turn_point(x, y, reg.quarter_turns, orig_w, orig_h)
    return reg.dx + xt * reg.scale, reg.dy + yt * reg.scale


def test_affine_coeffs_invert_the_forward_point_mapping_qt0():
    reg = _FakeReg(quarter_turns=0, scale=1.4, dx=12, dy=-5)
    orig_w, orig_h = 50, 40
    a, b, c, d, e, f = _affine_canonical_from_original(reg, orig_h, orig_w)
    for x, y in [(0, 0), (10, 20), (49, 39)]:
        X, Y = _forward_point(x, y, reg, orig_w, orig_h)
        x_back = a * X + b * Y + c
        y_back = d * X + e * Y + f
        assert abs(x_back - x) < 1e-6
        assert abs(y_back - y) < 1e-6


def test_affine_coeffs_invert_the_forward_point_mapping_qt2():
    reg = _FakeReg(quarter_turns=2, scale=0.8, dx=3, dy=6)
    orig_w, orig_h = 50, 40
    a, b, c, d, e, f = _affine_canonical_from_original(reg, orig_h, orig_w)
    for x, y in [(0, 0), (10, 20), (49, 39)]:
        X, Y = _forward_point(x, y, reg, orig_w, orig_h)
        x_back = a * X + b * Y + c
        y_back = d * X + e * Y + f
        assert abs(x_back - x) < 1e-6
        assert abs(y_back - y) < 1e-6


def test_affine_unsupported_quarter_turns_raises():
    reg = _FakeReg(quarter_turns=1, scale=1.0, dx=0, dy=0)
    with pytest.raises(ValueError):
        _affine_canonical_from_original(reg, 10, 10)


def test_pick_medoid_picks_the_image_closest_to_the_rest():
    # three near-identical grey images and one outlier: the medoid must be one of the three
    base = np.full((200, 200), 200, dtype=np.uint8)
    close_a = base.copy()
    close_a[0:5, 0:5] = 0
    close_b = base.copy()
    close_b[5:10, 5:10] = 0
    close_c = base.copy()
    outlier = np.full((200, 200), 10, dtype=np.uint8)
    greys = [close_a, close_b, close_c, outlier]
    idx = pick_medoid(greys)
    assert idx in (0, 1, 2)
