import json
import os

from naf.annotations import is_annotation_file, read_image_annotation

TOY = {
    "imageFilename": "toy.jpg",
    "width": 100,
    "height": 100,
    "fieldBBs": [
        {"id": "f0", "type": "field", "isBlank": 3,
         "poly_points": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        {"id": "f1", "type": "field", "isBlank": 1,   # handwriting, not blank: excluded
         "poly_points": [[20, 0], [30, 0], [30, 10], [20, 10]]},
        {"id": "f2", "type": "fieldP", "isBlank": 3,
         "poly_points": [[40, 0], [50, 0], [50, 10], [40, 10]]},
        {"id": "f3", "type": "graphic", "isBlank": 3,  # not a field type: excluded
         "poly_points": [[60, 0], [70, 0], [70, 10], [60, 10]]},
        {"id": "c0", "type": "comment", "isBlank": 1,
         "poly_points": [[5, 5], [8, 5], [8, 8], [5, 8]]},
        {"id": "c1", "type": "comment", "isBlank": 3,  # a comment box, never a field candidate
         "poly_points": [[45, 5], [48, 5], [48, 8], [45, 8]]},
    ],
    "textBBs": [],
}


def _write_toy(tmp_path):
    path = os.path.join(str(tmp_path), "toy.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(TOY, fh)
    return path


def test_only_isblank3_field_types_are_fields(tmp_path):
    path = _write_toy(tmp_path)
    fields, comments, width, height = read_image_annotation(path)
    field_ids = sorted(f["id"] for f in fields)
    assert field_ids == ["f0", "f2"]
    assert width == 100
    assert height == 100


def test_comments_are_never_fields_whatever_their_isblank(tmp_path):
    path = _write_toy(tmp_path)
    fields, comments, _w, _h = read_image_annotation(path)
    comment_ids = sorted(c["id"] for c in comments)
    assert comment_ids == ["c0", "c1"]
    assert all(f["id"] not in ("c0", "c1") for f in fields)


def test_is_annotation_file_excludes_nf_and_template():
    assert is_annotation_file("007182398_00026.json")
    assert not is_annotation_file("007182398_00026.json.nf")
    assert not is_annotation_file("template1.json")
