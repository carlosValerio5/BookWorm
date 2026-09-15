import re

ISBN_BOOKLAND_PREFIXES = ("978", "979")
ISBN10_CHECK_CHARACTER_VALUE = 10
ISBN_SEPARATOR_PATTERN = re.compile(r"[\s-]")
ISBN10_PATTERN = re.compile(r"[0-9]{9}[0-9X]")
ISBN13_PATTERN = re.compile(r"[0-9]{13}")
ISBN_CANDIDATE_PATTERN = re.compile(r"(?:97[89][\s-]?)?(?:[0-9][\s-]?){9}[0-9Xx]")


def normalize_isbn(raw_isbn: str) -> str:
    return ISBN_SEPARATOR_PATTERN.sub("", raw_isbn).upper()


def read_isbn10_character_value(character: str) -> int:
    return ISBN10_CHECK_CHARACTER_VALUE if character == "X" else int(character)


def calculate_isbn13_weighted_sum(digits: str) -> int:
    return sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(digits))


def calculate_isbn10_weighted_sum(characters: str) -> int:
    return sum(
        read_isbn10_character_value(character) * (10 - position) for position, character in enumerate(characters)
    )


def is_valid_isbn13(candidate: str) -> bool:
    return ISBN13_PATTERN.fullmatch(candidate) is not None and calculate_isbn13_weighted_sum(candidate) % 10 == 0


def is_valid_isbn10(candidate: str) -> bool:
    return ISBN10_PATTERN.fullmatch(candidate) is not None and calculate_isbn10_weighted_sum(candidate) % 11 == 0


def is_isbn_barcode(barcode_text: str) -> bool:
    return barcode_text.startswith(ISBN_BOOKLAND_PREFIXES) and is_valid_isbn13(barcode_text)


def convert_isbn10_to_isbn13(isbn10: str) -> str:
    isbn13_without_check_digit = "978" + isbn10[:9]
    check_digit = (10 - calculate_isbn13_weighted_sum(isbn13_without_check_digit) % 10) % 10
    return f"{isbn13_without_check_digit}{check_digit}"


def convert_to_isbn13(valid_isbn: str) -> str:
    return valid_isbn if len(valid_isbn) == 13 else convert_isbn10_to_isbn13(valid_isbn)


def extract_isbn_from_text(text: str) -> str | None:
    candidates = [normalize_isbn(match.group()) for match in ISBN_CANDIDATE_PATTERN.finditer(text)]
    valid_isbns = [
        convert_to_isbn13(candidate)
        for candidate in candidates
        if is_valid_isbn13(candidate) or is_valid_isbn10(candidate)
    ]
    return next(iter(valid_isbns), None)
