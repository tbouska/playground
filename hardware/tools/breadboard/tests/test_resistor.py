"""Behavior-lock tests for three pure functions in render_layout.

These tests lock the CURRENT behavior of _parse_ohms, _format_ohms, and
_resistor_bands. The SUT (render_layout.py) is not modified. Expected values
were captured by running the functions and hard-coding their exact output.
"""

import pytest

from render_layout import _format_ohms, _parse_ohms, _resistor_bands


# ---------------------------------------------------------------------------
# _parse_ohms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [
        ("220", 220.0),
        ("4.7k", 4700.0),
        ("1M", 1000000.0),
        ("10k", 10000.0),
        ("47", 47.0),
        ("47r", 47.0),   # trailing 'r' stripped
    ],
)
def test_parse_ohms_valid(value: str, expected: float) -> None:
    assert _parse_ohms(value) == expected


def test_parse_ohms_4R7_returns_none_locks_current_behavior() -> None:
    # Uppercase R is lowercased to 'r' mid-string; float("4r7") raises -> None.
    # The PRD aspirationally claims 4R7 -> 4.7 but the code does not implement
    # that path today.  We lock what the code actually returns.
    assert _parse_ohms("4R7") is None


def test_parse_ohms_junk_returns_none() -> None:
    assert _parse_ohms("abc") is None


def test_parse_ohms_empty_returns_none() -> None:
    assert _parse_ohms("") is None


def test_parse_ohms_junk_does_not_raise() -> None:
    # Defensive: ensure no exception escapes for garbage input.
    result = _parse_ohms("abc")
    assert result is None


def test_parse_ohms_empty_does_not_raise() -> None:
    result = _parse_ohms("")
    assert result is None


# ---------------------------------------------------------------------------
# _format_ohms
# ---------------------------------------------------------------------------

def test_format_ohms_kilo() -> None:
    assert _format_ohms("4700") == "4.7 kΩ"


def test_format_ohms_sub_kilo() -> None:
    assert _format_ohms("220") == "220 Ω"


def test_format_ohms_mega() -> None:
    assert _format_ohms("1000000") == "1 MΩ"


def test_format_ohms_small() -> None:
    assert _format_ohms("47") == "47 Ω"


# ---------------------------------------------------------------------------
# _resistor_bands
# ---------------------------------------------------------------------------

def test_resistor_bands_220_five_element_list() -> None:
    result = _resistor_bands("220")
    assert result == ["#c0392b", "#c0392b", "#1a1a1a", "#1a1a1a", "#7a4a1e"]


def test_resistor_bands_sub_100_ohm_uses_gold_multiplier() -> None:
    # 47 Ω: multiplier exponent is -1, which maps to gold (#cda434).
    result = _resistor_bands("47")
    assert result == ["#f1c40f", "#8e44ad", "#1a1a1a", "#cda434", "#7a4a1e"]


def test_resistor_bands_zero_returns_none() -> None:
    assert _resistor_bands("0") is None


def test_resistor_bands_invalid_returns_none() -> None:
    assert _resistor_bands("abc") is None
