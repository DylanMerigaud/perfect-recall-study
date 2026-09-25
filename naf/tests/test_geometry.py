from naf.geometry import is_degenerate, overlap_share, polygon_area, polygon_bbox, rasterize_at


def test_polygon_bbox_rectangle_is_padded_one_past_the_ceiling():
    # PIL fills the pixel AT an integer vertex coordinate (an inclusive edge); the bbox is
    # padded one past ceil(max) so that edge is never silently clipped. See polygon_bbox's
    # docstring for the measurement that forced this.
    assert polygon_bbox([[10, 20], [30, 20], [30, 40], [10, 40]]) == (10, 20, 31, 41)


def test_polygon_area_rectangle_10x20():
    # a box from (0,0) to (10,20) covers columns 0..10 and rows 0..20 inclusive: 11 x 21 = 231
    poly = [[0, 0], [10, 0], [10, 20], [0, 20]]
    assert polygon_area(poly) == 231


def test_polygon_area_triangle_half_of_bbox():
    # right triangle inside a 0..10 x 0..10 inclusive box (121 px): area should be roughly half
    poly = [[0, 0], [10, 0], [0, 10]]
    area = polygon_area(poly)
    assert 50 <= area <= 70  # rasterisation edge effects, not exactly 60.5


def test_rasterize_at_matches_polygon_area():
    poly = [[5, 5], [15, 5], [15, 25], [5, 25]]
    x0, y0, x1, y1 = polygon_bbox(poly)
    mask = rasterize_at(poly, x0, y0, x1 - x0, y1 - y0)
    assert int(mask.sum()) == polygon_area(poly)


def test_overlap_share_full_containment():
    field = [[0, 0], [10, 0], [10, 10], [0, 10]]  # inclusive 0..10: 121 px field
    comment = [[2, 2], [8, 2], [8, 8], [2, 8]]     # inclusive 2..8: 49 px comment fully inside
    share, area = overlap_share(field, [comment])
    assert area == 121
    assert abs(share - 49 / 121) < 0.01


def test_overlap_share_no_overlap_far_apart():
    field = [[0, 0], [10, 0], [10, 10], [0, 10]]
    comment = [[1000, 1000], [1010, 1000], [1010, 1010], [1000, 1010]]
    share, area = overlap_share(field, [comment])
    assert share == 0.0
    assert area == 121


def test_overlap_share_no_comments():
    field = [[0, 0], [10, 0], [10, 10], [0, 10]]
    share, area = overlap_share(field, [])
    assert share == 0.0
    assert area == 121


def test_overlap_share_exactly_at_one_percent_threshold():
    # a 0..100 field (inclusive 101 x 101 = 10,201 px) with a 45..55 comment (inclusive 11 x
    # 11 = 121 px) fully inside: 121 / 10201 is just above 1%
    field = [[0, 0], [100, 0], [100, 100], [0, 100]]
    comment = [[45, 45], [55, 45], [55, 55], [45, 55]]
    share, area = overlap_share(field, [comment])
    assert area == 10201
    assert abs(share - 121 / 10201) < 0.001


def test_overlap_share_union_of_two_overlapping_comments_not_double_counted():
    field = [[0, 0], [20, 0], [20, 20], [0, 20]]       # inclusive 0..20: 21 x 21 = 441 px
    comment_a = [[0, 0], [12, 0], [12, 20], [0, 20]]   # left columns, overlaps comment_b
    comment_b = [[8, 0], [20, 0], [20, 20], [8, 20]]   # right columns, overlaps comment_a
    share_union, area = overlap_share(field, [comment_a, comment_b])
    # union covers the whole field, not the sum of the two (which would exceed the field area)
    assert area == 441
    assert share_union <= 1.0
    assert abs(share_union - 1.0) < 0.05


def test_degenerate_field_is_excluded_not_measured_as_one_pixel():
    # a zero-width sliver: without is_degenerate, the +1 pad in polygon_bbox would measure this
    # as a spurious 1x1 field instead of excluding it.
    poly = [[5, 5], [5, 5], [5, 5]]
    assert is_degenerate(poly)
    assert polygon_area(poly) == 0
    share, area = overlap_share(poly, [[[0, 0], [10, 0], [10, 10], [0, 10]]])
    assert area == 0
    assert share == 0.0


def test_degenerate_other_polygon_is_ignored_in_overlap():
    field = [[0, 0], [10, 0], [10, 10], [0, 10]]
    degenerate_comment = [[3, 3], [3, 3], [3, 3]]
    share, area = overlap_share(field, [degenerate_comment])
    assert share == 0.0
    assert area == 121
