"""The crop audit and sensitivity sweep of the X3 reading (results/naf-reading.md).

Re-runs the pixel measure of naf/registration.py on the seven qualifying groups with variants:
consensus dilation radius 0, 3 (the committed value) and 6 px, and at radius 3 a leave-one-out
consensus (each image excluded from its own vote). Per field it also records how many added-ink
pixels lie more than 8 px from any template ink (`near8` counts those within 8 px) and the
largest connected component of added ink. Writes OUT/variants.csv, and for every key given
(group:image_id:field_id, as printed by audit_sample.py) a three-panel PNG at radius 3: the scan,
the consensus warped into the scan's frame, and the scan with added ink in red and the field
outline in blue. Must run under dossier-preflight's venv:

  $PY naf/diagnostics/crop_audit.py OUT $(python3 naf/diagnostics/audit_sample.py $AR/x3 | awk '{print $2}')

NAF is read from $AR/x3/NAF. Takes about 10 minutes on the 70 images.
"""
import sys, os, csv, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from PIL import Image
from scipy import ndimage
from naf import registration as R
from naf.annotations import iter_images, read_image_annotation
from naf.geometry import polygon_bbox, rasterize_at
from preflight.deskew import build_frame

NAF = os.path.join(os.environ["AR"], "x3", "NAF")
OUT = sys.argv[1]
CROPS = set(tuple(x.split(":")) for x in sys.argv[2:])  # group:image:field
os.makedirs(OUT, exist_ok=True)
GROUPS = ["1", "104_1", "106", "107", "108", "131", "132"]


class _Reg:
    pass


def json_for(group, image_id):
    for g, iid, p in iter_images(NAF):
        if g == group and iid == image_id:
            return p


rows = []
for group in GROUPS:
    imgs = R.load_group_images(NAF, group)
    greys = [g for _, g in imgs]
    mi = R.pick_medoid(greys)
    med = greys[mi]
    ch, cw = med.shape
    regs = {}
    raw = {}
    for iid, g in imgs:
        reg = R._register_best_of(g, med)
        regs[iid] = reg
        raw[iid] = R.warp_to_canonical(g, reg, (cw, ch)) < 128
    for radius in (0, 3, 6):
        st = np.ones((2 * radius + 1,) * 2, bool)
        stack = {iid: (ndimage.binary_dilation(m, structure=st) if radius else m) for iid, m in raw.items()}
        total = np.sum(np.stack(list(stack.values())), axis=0).astype(np.int16)
        n = len(stack)
        for iid, g in imgs:
            for loo in (False, True):
                if loo and radius != 3:
                    continue
                if loo:
                    vote = (total - stack[iid]) / (n - 1)
                else:
                    vote = total / n
                cons = np.where(vote >= 0.5, 0, 255).astype(np.uint8)
                reg = regs[iid]
                frame = build_frame(g, cons, reg)
                fields, comments, _, _ = read_image_annotation(json_for(group, iid))
                oh, ow = g.shape
                # template-dark distance map in native frame, for residue proximity
                tdark = frame.blank < 128
                dist = ndimage.distance_transform_edt(~tdark)
                for f in fields:
                    poly = [R.turn_point(x, y, reg.quarter_turns, ow, oh) for x, y in f["poly"]]
                    x0, y0, x1, y1 = polygon_bbox(poly)
                    mask = rasterize_at(poly, x0, y0, x1 - x0, y1 - y0).astype(bool)
                    area = int(mask.sum())
                    sp = frame.scan[y0:y1, x0:x1]
                    bp = frame.blank[y0:y1, x0:x1]
                    added = mask & (sp < 128) & ~(bp < 128)
                    a = int(added.sum())
                    near = int((added & (dist[y0:y1, x0:x1] <= 8)).sum())
                    # connected components of the added mask
                    lab, ncomp = ndimage.label(added)
                    big = 0
                    if ncomp:
                        sizes = ndimage.sum(added, lab, range(1, ncomp + 1))
                        big = int(sizes.max())
                    rows.append(dict(group=group, image_id=iid, field_id=f["id"], radius=radius, loo=loo,
                                     area=area, added=a, share=a / area, near8=near, ncomp=ncomp, bigcomp=big))
                    key = (group, iid, f["id"])
                    if key in CROPS and radius == 3 and not loo:
                        pad = 40
                        X0, Y0 = max(0, x0 - pad), max(0, y0 - pad)
                        X1, Y1 = min(frame.scan.shape[1], x1 + pad), min(frame.scan.shape[0], y1 + pad)
                        s = frame.scan[Y0:Y1, X0:X1]
                        b = frame.blank[Y0:Y1, X0:X1]
                        rgb = np.stack([s, s, s], -1).astype(np.uint8).copy()
                        full_added = np.zeros_like(s, bool)
                        full_added[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = added
                        rgb[full_added] = [255, 0, 0]
                        # field outline in blue
                        fm = np.zeros_like(s, bool)
                        fm[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = mask
                        edge = fm ^ ndimage.binary_erosion(fm)
                        rgb[edge] = [0, 0, 255]
                        brgb = np.stack([b, b, b], -1).astype(np.uint8)
                        raw_s = np.stack([s, s, s], -1).astype(np.uint8)
                        sep = np.full((6, s.shape[1], 3), 128, np.uint8)
                        im = np.concatenate([raw_s, sep, brgb, sep, rgb], 0)
                        Image.fromarray(im).save(os.path.join(OUT, "%s__%s__%s.png" % key))
    print("done", group, file=sys.stderr)

with open(os.path.join(OUT, "variants.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
