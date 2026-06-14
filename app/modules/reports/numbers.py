# app/modules/reports/numbers.py
"""Vietnamese amount-in-words. Vendored from num_to_verbal.py and extended past
999,999,999 with a `tỷ` (billion) wrapper for the acceptance report's
{final_award_verbal}."""

_DIGITS = [
    "không", "một", "hai", "ba", "bốn",
    "năm", "sáu", "bảy", "tám", "chín",
]


def _read_3_digits(num: int, force_full: bool = False) -> str:
    hundred = num // 100
    ten = (num % 100) // 10
    one = num % 10
    parts: list[str] = []

    if hundred > 0:
        parts.append(_DIGITS[hundred])
        parts.append("trăm")
    elif force_full and (ten > 0 or one > 0):
        parts.append("không")
        parts.append("trăm")

    if ten > 1:
        parts.append(_DIGITS[ten])
        parts.append("mươi")
        if one == 1:
            parts.append("mốt")
        elif one == 4:
            parts.append("tư")
        elif one == 5:
            parts.append("lăm")
        elif one > 0:
            parts.append(_DIGITS[one])
    elif ten == 1:
        parts.append("mười")
        if one == 5:
            parts.append("lăm")
        elif one > 0:
            parts.append(_DIGITS[one])
    else:  # ten == 0
        if one > 0:
            if hundred > 0 or force_full:
                parts.append("linh")
            parts.append(_DIGITS[one])

    return " ".join(parts)


def _below_billion(n: int) -> str:
    """Reading of 1..999,999,999 (no capitalization)."""
    million = n // 1_000_000
    thousand = (n % 1_000_000) // 1_000
    remainder = n % 1_000
    parts: list[str] = []
    if million:
        parts.append(_read_3_digits(million))
        parts.append("triệu")
    if thousand:
        force = million > 0 and thousand < 100
        parts.append(_read_3_digits(thousand, force))
        parts.append("nghìn")
    if remainder:
        force = (million > 0 or thousand > 0) and remainder < 100
        parts.append(_read_3_digits(remainder, force))
    return " ".join(parts)


def number_to_vietnamese(n: int) -> str:
    """Amount in words, capitalized. Handles 0 .. ~10^18 (billions via 'tỷ')."""
    if n < 0:
        raise ValueError("Number must be non-negative")
    if n == 0:
        return "Không"

    billions = n // 1_000_000_000
    rest = n % 1_000_000_000
    parts: list[str] = []
    if billions:
        parts.append(_below_billion(billions))
        parts.append("tỷ")
    if rest:
        parts.append(_below_billion(rest))

    text = " ".join(p for p in parts if p)
    return text[0].upper() + text[1:]
