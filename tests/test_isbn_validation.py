import pytest

from bookworm.isbn_validation import (
    convert_isbn10_to_isbn13,
    extract_isbn_from_text,
    is_isbn_barcode,
    is_valid_isbn10,
    is_valid_isbn13,
    normalize_isbn,
)


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("9780306406157", True),
        ("9780306406158", False),
        ("978030640615", False),
        ("97803064061570", False),
        ("978030640615X", False),
        ("", False),
    ],
)
def test_is_valid_isbn13(candidate: str, expected: bool) -> None:
    assert is_valid_isbn13(candidate) is expected


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("0306406152", True),
        ("080442957X", True),
        ("0306406153", False),
        ("030640615", False),
        ("X306406152", False),
        ("", False),
    ],
)
def test_is_valid_isbn10(candidate: str, expected: bool) -> None:
    assert is_valid_isbn10(candidate) is expected


@pytest.mark.parametrize(
    ("isbn10", "expected_isbn13"),
    [
        ("0306406152", "9780306406157"),
        ("080442957X", "9780804429573"),
    ],
)
def test_convert_isbn10_to_isbn13(isbn10: str, expected_isbn13: str) -> None:
    assert convert_isbn10_to_isbn13(isbn10) == expected_isbn13


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("978-0-306 40615-7", "9780306406157"),
        ("080442957x", "080442957X"),
    ],
)
def test_normalize_isbn_removes_separators_and_uppercases(raw: str, expected: str) -> None:
    assert normalize_isbn(raw) == expected


@pytest.mark.parametrize(
    ("barcode_text", "expected"),
    [
        ("9780306406157", True),
        ("9790000000001", True),
        ("4006381333931", False),
        ("9780306406158", False),
    ],
)
def test_is_isbn_barcode_requires_bookland_prefix_and_checksum(barcode_text: str, expected: bool) -> None:
    assert is_isbn_barcode(barcode_text) is expected


@pytest.mark.parametrize(
    ("text", "expected_isbn"),
    [
        ("ISBN 978-0-306-40615-7", "9780306406157"),
        ("ISBN-10: 0-306-40615-2", "9780306406157"),
        ("isbn 080442957x", "9780804429573"),
        ("Price 12.99 ISBN 9780306406157 printed in USA", "9780306406157"),
        ("The Great Gatsby", None),
        ("ISBN 978-0-306-40615-8", None),
        ("", None),
    ],
)
def test_extract_isbn_from_text(text: str, expected_isbn: str | None) -> None:
    assert extract_isbn_from_text(text) == expected_isbn
