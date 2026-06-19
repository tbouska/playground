"""Behavior-lock tests for three pure functions in render_layout.

These tests lock the CURRENT behavior of _parse_ohms, _format_ohms, and
_resistor_bands. The SUT (render_layout.py) is not modified. Expected values
were captured by running the functions and hard-coding their exact output.
"""

import pytest

from breadboard.components.resistor import _format_ohms, _parse_ohms, _resistor_bands


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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "PRD 00001 Critical Scenario specifies _parse_ohms('4R7') -> 4.7, but "
        "render_layout._parse_ohms only strips a trailing 'r' ('47r' -> 47.0); "
        "'4R7' lowercases to '4r7' with 'r' mid-string, so float('4r7') raises "
        "and the function returns None. The SUT is intentionally unchanged: this "
        "is a behavior-lock harness built BEFORE the renderer refactor (PRD "
        "00002+), so implementing 4R7 parsing is out of scope and deferred to a "
        "future PRD. strict=True makes the gap loud -- if 4R7 support is ever "
        "added this test XPASSes and strict turns that into a failure, forcing a "
        "deliberate update here."
    ),
)
def test_parse_ohms_4R7_matches_prd_scenario_xfail() -> None:
    assert _parse_ohms("4R7") == 4.7


@pytest.mark.parametrize("value", ["abc", ""])
def test_parse_ohms_invalid_returns_none_without_raising(value: str) -> None:
    # Invalid input returns None and never raises. A passing `is None` assertion
    # already proves no exception escaped, so a separate "does not raise" test
    # would be redundant.
    assert _parse_ohms(value) is None


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


@pytest.mark.parametrize("value", ["abc", "", "4R7"])
def test_format_ohms_invalid_returns_raw_unchanged(value: str) -> None:
    # PRD: invalid input returns the raw string, never raises. _format_ohms
    # echoes any value it cannot parse as a number back verbatim.
    assert _format_ohms(value) == value


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


def test_resistor_bands_sub_10_ohm_uses_silver_multiplier() -> None:
    # 4.7 Ω: multiplier exponent is -2, which maps to silver (#bfc1c2). Same
    # significant digits as the 47 Ω gold case above; only the multiplier band
    # differs (gold #cda434 -> silver #bfc1c2).
    result = _resistor_bands("4.7")
    assert result == ["#f1c40f", "#8e44ad", "#1a1a1a", "#bfc1c2", "#7a4a1e"]


def test_resistor_bands_zero_returns_none() -> None:
    assert _resistor_bands("0") is None


def test_resistor_bands_invalid_returns_none() -> None:
    assert _resistor_bands("abc") is None
