#!/usr/bin/env python3
"""Draw the crop-audit sample of the X3 reading (results/naf-reading.md).

Among pixel-positive fields (added ink >= 0.345%) with NO comment overlap: the 15 highest
shares, plus 10 drawn at random from the rest with random.Random(20260925). Plus every field
that carries a comment overlap (4 in the committed run). Prints one line per field:
`<tag> <group>:<image_id>:<field_id> <share>`, the key form crop_audit.py takes.

  python3 naf/diagnostics/audit_sample.py $AR/x3
"""
import csv
import os
import random
import sys

X3 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ["AR"], "x3")
h = {(r['group'], r['image_id'], r['field_id']): float(r['comment_overlap_share'])
     for r in csv.DictReader(open(os.path.join(X3, 'naf_fields_human_label.csv')))}
p = list(csv.DictReader(open(os.path.join(X3, 'naf_fields_pixel.csv'))))
flag = [r for r in p if r['above_0.345pct'] == 'True' and h[(r['group'], r['image_id'], r['field_id'])] == 0]
flag.sort(key=lambda r: -float(r['added_ink_share']))
top = flag[:15]
rnd = random.Random(20260925).sample(flag[15:], 10)
pos = [r for r in p if h[(r['group'], r['image_id'], r['field_id'])] > 0]
for tag, rows in (("top", top), ("rnd", rnd), ("pos", pos)):
    for r in rows:
        print("%s %s:%s:%s %.4f" % (tag, r['group'], r['image_id'], r['field_id'],
                                    float(r['added_ink_share'])))
