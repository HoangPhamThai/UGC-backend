import pytest

from app.modules.reports.numbers import number_to_vietnamese


def test_zero():
    assert number_to_vietnamese(0) == "Không"


def test_below_billion_matches_known_readings():
    assert number_to_vietnamese(450_000).lower().startswith("bốn trăm năm mươi nghìn")
    assert number_to_vietnamese(21).lower() == "hai mươi mốt"
    assert number_to_vietnamese(15).lower() == "mười lăm"


def test_billions_use_ty():
    out = number_to_vietnamese(1_000_000_000).lower()
    assert out.startswith("một tỷ")
    out2 = number_to_vietnamese(2_500_000_000).lower()
    assert "tỷ" in out2 and out2.startswith("hai tỷ")


def test_capitalized_first_letter():
    assert number_to_vietnamese(5)[0].isupper()


def test_negative_rejected():
    with pytest.raises(ValueError):
        number_to_vietnamese(-1)
