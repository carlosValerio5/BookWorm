from pathlib import Path

import numpy as np
import pytest
from image_factories import RED_BGR, create_blank_image, create_solid_color_image, write_heic_image, write_image

from bookworm.image_loading import ImageLoadError, load_image, shrink_image_to_long_side


def test_loads_image_from_disk(tmp_path: Path, blank_image: np.ndarray) -> None:
    image_path = write_image(tmp_path / "blank.png", blank_image)

    assert load_image(image_path).shape == blank_image.shape


def test_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ImageLoadError):
        load_image(tmp_path / "missing.png")


def test_raises_for_file_that_is_not_an_image(tmp_path: Path) -> None:
    fake_image_path = tmp_path / "notes.png"
    fake_image_path.write_text("not an image")

    with pytest.raises(ImageLoadError):
        load_image(fake_image_path)


def test_loads_heic_image_from_disk(tmp_path: Path) -> None:
    heic_path = write_heic_image(tmp_path / "photo.heic", create_solid_color_image(RED_BGR))

    assert load_image(heic_path).shape == (480, 640, 3)


def test_loads_iphone_heic_colors_in_bgr_order(tmp_path: Path) -> None:
    heic_path = write_heic_image(tmp_path / "IMG_0001.HEIC", create_solid_color_image(RED_BGR))

    blue_mean, _green_mean, red_mean = load_image(heic_path).mean(axis=(0, 1))

    assert red_mean > 200
    assert blue_mean < 50


def test_raises_for_heic_file_that_is_not_an_image(tmp_path: Path) -> None:
    fake_heic_path = tmp_path / "notes.heic"
    fake_heic_path.write_text("not an image")

    with pytest.raises(ImageLoadError):
        load_image(fake_heic_path)


def test_raises_for_missing_heic_file(tmp_path: Path) -> None:
    with pytest.raises(ImageLoadError):
        load_image(tmp_path / "missing.heic")


@pytest.mark.parametrize(
    ("height", "width", "expected_shape"),
    [
        (1920, 2560, (960, 1280, 3)),
        (2560, 1920, (1280, 960, 3)),
    ],
)
def test_shrinks_large_image_to_long_side(height: int, width: int, expected_shape: tuple[int, int, int]) -> None:
    shrunk_image = shrink_image_to_long_side(create_blank_image(height=height, width=width), 1280)

    assert shrunk_image.pixels.shape == expected_shape


def test_shrunk_image_remembers_scale_back_to_original() -> None:
    shrunk_image = shrink_image_to_long_side(create_blank_image(height=1920, width=2560), 1280)

    assert shrunk_image.scale_to_original == 2.0


def test_keeps_small_image_at_original_size() -> None:
    shrunk_image = shrink_image_to_long_side(create_blank_image(height=480, width=640), 1280)

    assert (shrunk_image.pixels.shape, shrunk_image.scale_to_original) == ((480, 640, 3), 1.0)
