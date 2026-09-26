"""X2, the real captures, as a scoring target. It plugs in by path.

Until `x2/readings.jsonl` exists in the archive, status() says so and every X2 result in
protocols.json and hypotheses.json reads "not tested yet". When the file appears (written by
dossier-preflight's grid/read_images.py from the manifest grid/realscan_ingest.py builds), the
next run of protocols.py and hypotheses.py scores it with no code change.

How X2 readings are grouped (dossier-preflight's grid/realscan_kit.py fixes the design):

- UNMARKED captures (mark_step empty) of one identity, one capture round and one device form a
  dossier: analyze.load() keys them on (dpi, identity, source x2, capture "phone-1", ...), and
  the variants a dossier must carry are the kit's own `expected.json` (the nine v0.1.0 names).
  They are swept by analyze.sweep() like any generator arm.
- MARK SHEETS (mark_step 0 to 3) are single pages, the clean copy and the emptied copy of one
  piece, captured after each mark step. They are scored for required_field alone, page by page,
  through preflight.checks.evaluate() on that one piece, abstention off.

A real-capture CONDITION (PREREG.md section 4.1, H4) is (device, dpi) for unmarked captures and
(device, mark step) for mark sheets. The CLUSTER is the physical sheet: (identity, piece, variant)
for an unmarked page, plus "mark" for a mark sheet.
"""
import json
import os

from analysis import data

CONTENT_CHECKS = ("required_field", "required_checkbox", "signature", "expiry", "consistency",
                  "forbidden_value")
CAPTURE_INDEX = 9
MARK_INDEX = 10


def status():
    path, st = data.arm_status("X2")
    return st if path is None else "present"


def device_of(capture):
    return (capture or "").split("-")[0] or None


def sheet_of_target(identity, t, positive):
    """The physical sheet a sweep target sits on: the variant's piece for a positive, the clean
    piece for a negative."""
    if positive:
        variant, piece = t[0], t[1]
        v = data.catalog().get(variant)
        return (identity, (v.piece if v is not None and v.piece else piece.split("+")[-1]),
                variant)
    return (identity, t[0], "clean")


def observations_from_sweep(per_cell, threshold, condition_of):
    """One row per target: sheet, condition, positive, fires (raw sensors)."""
    a = data.analyze()
    rows = []
    for key in sorted(per_cell, key=repr):
        v = per_cell[key]
        cond = condition_of(key)
        for side in ("pos", "neg"):
            for t in sorted(v[side], key=repr):
                rows.append({"sheet": sheet_of_target(key[a.IDENTITY_INDEX], t, side == "pos"),
                             "condition": cond, "positive": side == "pos",
                             "fires": v[side][t] > threshold, "key": key, "target": t})
    return rows


def recall_by_condition(rows):
    out = {}
    for r in rows:
        if not r["positive"]:
            continue
        k, n = out.get(r["condition"], (0, 0))
        out[r["condition"]] = (k + r["fires"], n + 1)
    return {c: kn[0] / kn[1] for c, kn in out.items() if kn[1]}


def mean_abs_error(rows_by_check, validated):
    """H4's statistic: the mean over (check, condition) pairs with a positive of
    |validated recall of the check - observed recall in that condition|."""
    errs = []
    for check in sorted(rows_by_check):
        v = validated.get(check)
        if v is None:
            continue
        for cond, rec in sorted(recall_by_condition(rows_by_check[check]).items(), key=repr):
            errs.append(abs(v - rec))
    return sum(errs) / len(errs) if errs else float("nan")


class X2:
    def __init__(self, info, dossiers, sweeps, marks):
        self.info, self.dossiers, self.sweeps, self.marks = info, dossiers, sweeps, marks

    @classmethod
    def load(cls, sweeps_by_arm=None, checks=None):
        path, st = data.arm_status("X2")
        if path is None:
            return None
        a = data.analyze()
        from preflight.reading import Reading
        kit = os.path.join(data.AR, "x2", "kit", "expected.json")
        expected = {i: frozenset(n) for i, n in json.load(open(kit, encoding="utf-8")).items()}
        index = a.load(data.plain(path))
        unmarked = {k: v for k, v in index.items() if k[MARK_INDEX] is None}
        dossiers, missing, dropped = data.assemble(unmarked, expected.__getitem__)
        info = {"arm": "X2", "status": "present", "path": os.path.relpath(path, data.AR),
                "sha256": data.sha256(path), "dossiers": len(dossiers),
                "variants_missing": len(missing), "keys_dropped": len(dropped)}
        checks = checks or list(a.CHECKS)
        sweeps = {c: data.sweep_arm(dossiers, info, c) for c in checks}
        marks = []
        for line in data.load_lines(path):
            if line.get("mark_step") is None:
                continue
            marks.append({"identity": line["identity"], "piece": line["piece"],
                          "variant": line["variant"], "capture": line.get("capture"),
                          "mark_step": int(line["mark_step"]),
                          "mark_ink_share": line.get("mark_ink_share"),
                          "reading": Reading.from_dict(line["reading"])})
        info["mark_captures"] = len(marks)
        return cls(info, dossiers, sweeps, marks)

    # --- unmarked captures -------------------------------------------------------------
    @staticmethod
    def condition_unmarked(key):
        return f"{device_of(key[CAPTURE_INDEX])}|{key[1]}dpi"

    def rows_unmarked(self, check, reg, threshold):
        return observations_from_sweep(self.sweeps[check].get(reg, {}), threshold,
                                       self.condition_unmarked)

    # --- mark sheets ---------------------------------------------------------------------
    def mark_scores(self, reg):
        """[(mark row, {target: score}, damaged targets)] for required_field, abstention off."""
        from preflight.checks import evaluate
        a = data.analyze()
        refs = data.identities()
        out = []
        for m in self.marks:
            ref = refs[m["identity"]]
            found = {str(c.target): c.score
                     for c in evaluate({m["piece"]: m["reading"]}, ref, "filing", reg,
                                       checks=["required_field"], abstention=False)
                     if c.score is not None}
            v = data.catalog().get(m["variant"])
            damaged = ({t for p, t in a.damaged_targets(v, ref) if p == m["piece"]}
                       if v is not None and v.check == "required_field" else set())
            out.append((m, found, damaged))
        return out

    def rows_marks(self, reg, threshold, steps=(0, 1, 2, 3)):
        rows = []
        for m, found, damaged in self.mark_scores(reg):
            if m["mark_step"] not in steps:
                continue
            cond = f"{device_of(m['capture'])}|mark{m['mark_step']}"
            sheet = (m["identity"], m["piece"], m["variant"], "mark")
            for t, s in sorted(found.items()):
                rows.append({"sheet": sheet, "condition": cond, "positive": t in damaged,
                             "fires": s > threshold, "target": t,
                             "key": (m["identity"], m["piece"], m["variant"], m["capture"],
                                     m["mark_step"])})
        return rows

    # --- what protocols.py asks --------------------------------------------------------
    def rows(self, check, reg, threshold):
        rows = self.rows_unmarked(check, reg, threshold)
        if check == "required_field":
            rows += self.rows_marks(reg, threshold)
        return rows

    def score_choice(self, check, reg, threshold):
        rows = self.rows(check, reg, threshold)
        pos = [r for r in rows if r["positive"]]
        neg = [r for r in rows if not r["positive"]]
        tp = sum(r["fires"] for r in pos)
        fp = sum(r["fires"] for r in neg)
        return {"recall": tp / len(pos) if pos else None, "tp": tp, "n_pos": len(pos),
                "fpr": fp / len(neg) if neg else None, "fp": fp, "n_neg": len(neg),
                "recall_by_condition": recall_by_condition(rows)}

    def score_combined(self, ink_choice, ocr_choice, op):
        def index(choice):
            return {(r["key"], r["target"]): r for r in
                    self.rows("required_field", choice["settings"], choice["threshold"])}
        ri, ro = index(ink_choice), index(ocr_choice)
        common = sorted(set(ri) & set(ro), key=repr)
        rows = [dict(ri[k], fires=(ri[k]["fires"] and ro[k]["fires"]) if op == "and"
                     else (ri[k]["fires"] or ro[k]["fires"])) for k in common]
        pos = [r for r in rows if r["positive"]]
        tp = sum(r["fires"] for r in pos)
        return {"recall": tp / len(pos) if pos else None, "tp": tp, "n_pos": len(pos),
                "recall_by_condition": recall_by_condition(rows)}

    def errors(self, choices):
        from preflight.checks import Settings
        by_check, validated = {}, {}
        for check, rec in choices.items():
            if check not in CONTENT_CHECKS + ("resolution", "cropped_page", "rotated_page"):
                continue
            reg = Settings(**rec["measured_settings"])
            by_check[check] = self.rows(check, reg, rec["threshold"])
            if rec.get("validation") and rec["validation"].get("n_pos"):
                validated[check] = rec["validation"]["recall"]
        return {"mean_recall_abs_error": mean_abs_error(by_check, validated)}
