import pytest
from crawler_factories import create_encoded_image, create_png_header

from bookworm.crawler.image_size_reading import ImageDecodeError, read_image_long_side


def test_reads_long_side_of_landscape_jpeg() -> None:
    assert read_image_long_side(create_encoded_image(width=640, height=480)) == 640


def test_reads_long_side_of_portrait_png() -> None:
    assert read_image_long_side(create_encoded_image(width=300, height=900, extension=".png")) == 900


def test_reads_long_side_from_the_header_without_decoding_pixels() -> None:
    assert read_image_long_side(create_png_header(width=60000, height=40000)) == 60000


def test_raises_on_bytes_that_are_not_an_image() -> None:
    with pytest.raises(ImageDecodeError):
        read_image_long_side(b"<html>not an image</html>")
