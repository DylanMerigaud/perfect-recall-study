"""Read NAF's per-image JSON annotations into the field and comment records this study measures.

See FORMAT.md for the dataset's own schema and for the two decisions this module encodes: which
`fieldBBs` types count as a candidate "field" for the isBlank == 3 population, and that
`type == "comment"` boxes are the added-writing layer, never a field, whatever their own
`isBlank` value happens to be.
"""
import json
import os

# Box types that represent an actual response area a filer could leave blank. "comment" (added
# writing not inside a field) and "graphic" (an image or photograph) are excluded: neither is a
# field a person fills in. "fieldRegion" is excluded too (used to separate multiple documents
# scanned in one image, not itself a response area); it never carries isBlank == 3 in this
# dataset (checked 2026-09-25), so the exclusion is a documented no-op, not a live filter.
FIELD_TYPES = frozenset({
    "field", "fieldP", "fieldRow", "fieldCol", "fieldCheckBox", "fieldCircle",
})

BLANK = 3
COMMENT_TYPE = "comment"


def _load(json_path):
    with open(json_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_image_annotation(json_path):
    """(fields, comments, width, height) for one NAF image JSON.

    fields: list of {"id", "poly", "type"} for boxes with type in FIELD_TYPES and isBlank == 3.
    comments: list of {"id", "poly"} for every type == "comment" box, regardless of its isBlank.
    """
    data = _load(json_path)
    fields = []
    comments = []
    for box in data.get("fieldBBs", []):
        btype = box.get("type")
        poly = box.get("poly_points")
        if not poly or len(poly) < 3:
            continue
        if btype == COMMENT_TYPE:
            comments.append({"id": box.get("id"), "poly": poly})
        elif btype in FIELD_TYPES and box.get("isBlank") == BLANK:
            fields.append({"id": box.get("id"), "poly": poly, "type": btype})
    return fields, comments, data.get("width"), data.get("height")


def is_annotation_file(name):
    """True for a primary per-image annotation JSON, excluding .nf variants and group templates."""
    return name.endswith(".json") and not name.endswith(".json.nf") and "template" not in name


def iter_images(naf_dir):
    """Yield (group, image_id, json_path) for every primary annotation under naf_dir/groups."""
    groups_dir = os.path.join(naf_dir, "groups")
    for group in sorted(os.listdir(groups_dir)):
        group_path = os.path.join(groups_dir, group)
        if not os.path.isdir(group_path):
            continue
        for name in sorted(os.listdir(group_path)):
            if is_annotation_file(name):
                image_id = name[: -len(".json")]
                yield group, image_id, os.path.join(group_path, name)


def image_path(naf_dir, group, image_id):
    return os.path.join(naf_dir, "groups", group, image_id + ".jpg")
