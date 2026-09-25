"""Minimal reproduction: preflight.deskew.register refines only the coarse winner across quarters.

NAF group 132, image 007540939_00111 (upright) against the group's medoid 007540939_00212.
Measured 2026-09-25: quarters=(0, 2) returns quarter_turns 2 at peak 0.6042, quarters=(0,) alone
returns 0 at 0.6189; the coarse round alone scores the two 0.5970 and 0.5972. The tool's own
prepare() returns quarter_turns 3 at peak 0.5650 with orientation_margin -0.0539. Run with $PY.
"""
import os
import numpy as np
from PIL import Image
from preflight.deskew import register

G = os.path.join(os.environ["AR"], "x3", "NAF", "groups", "132") + os.sep
scan = np.asarray(Image.open(G + "007540939_00111.jpg").convert("L"))
blank = np.asarray(Image.open(G + "007540939_00212.jpg").convert("L"))
both = register(scan, blank, quarters=(0, 2))
q0 = register(scan, blank, quarters=(0,))
q2 = register(scan, blank, quarters=(2,))
print("quarters=(0,2): qt=%d peak=%.4f per-quarter peaks=%s" % (both.quarter_turns, both.peak, both.peaks))
print("quarters=(0,):  qt=%d peak=%.4f" % (q0.quarter_turns, q0.peak))
print("quarters=(2,):  qt=%d peak=%.4f" % (q2.quarter_turns, q2.peak))
# coarse round only (no refinement)
c = register(scan, blank, quarters=(0, 2), refinements=())
print("coarse only, quarters=(0,2): qt=%d peak=%.4f peaks=%s" % (c.quarter_turns, c.peak, c.peaks))
# prepare-like: the tool's own path deskews first, then quarters=(0,2)
from preflight.deskew import prepare
p = prepare(scan, blank)
print("prepare(): quarter_turns=%d peak=%.4f orientation_margin=%.4f" % (p.quarter_turns, p.peak, p.orientation_margin))
