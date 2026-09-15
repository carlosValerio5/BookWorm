from bookworm.scan_types import BoundingBox


def test_bounding_box_from_points_uses_outer_corners() -> None:
    points = [(10.7, 20.2), (110.1, 20.9), (110.0, 50.0), (10.0, 50.0)]

    assert BoundingBox.from_points(points) == BoundingBox(x_min=10, y_min=20, x_max=110, y_max=50)
