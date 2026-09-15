from pathlib import Path

import numpy as np
import pytest
from image_factories import write_image

from bookworm.image_loading import ImageLoadError, load_image


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
