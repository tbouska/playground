"""Behavior-lock tests for three pure functions in render_layout.

These tests lock the CURRENT behavior of _parse_ohms, _format_ohms, and
_resistor_bands. The SUT (render_layout.py) is not modified. Expected values
were captured by running the functions and hard-coding their exact output.
"""

import pytest

from breadboard.components.resistor import _format_ohms, _parse_ohms, _resistor_bands
from breadboard.style import load_style


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

def test_resistor_bands_algorithm_over_diverse_values() -> None:
    # Exercises the real digit/multiplier math, not a per-input lookup: positive
    # multipliers (digit_colors), gold/silver extras, and the mantissa>=1000
    # carry branch. Each expected list is built from the style's own accessors
    # (intent), so a hardcoded-hex implementation cannot pass.
    style = load_style()
    dc = style.resistor_digit_colors
    me = style.resistor_multiplier_extra
    tol = style.color("resistor.tolerance")
    cases = [
        ("220", [dc[2], dc[2], dc[0], dc[0], tol]),
        ("4.7k", [dc[4], dc[7], dc[0], dc[1], tol]),
        ("10k", [dc[1], dc[0], dc[0], dc[2], tol]),
        ("1M", [dc[1], dc[0], dc[0], dc[4], tol]),
        ("47", [dc[4], dc[7], dc[0], me[-1], tol]),  # exponent -1 -> gold
        ("4.7", [dc[4], dc[7], dc[0], me[-2], tol]),  # exponent -2 -> silver
        ("9996", [dc[1], dc[0], dc[0], dc[2], tol]),  # rounds up via the mantissa>=1000 carry branch
    ]
    for value, expected in cases:
        assert _resistor_bands(value, style) == expected, value


def test_resistor_bands_multiplier_out_of_range_returns_none() -> None:
    # 1e12 Ω: multiplier exponent 10 is past the 0-9 digit range and not in the
    # gold/silver extras, so the real algorithm returns None. A lookup table
    # keyed on the tested inputs above cannot anticipate this rejection.
    style = load_style()
    assert _resistor_bands("1000000m", style) is None


def test_resistor_bands_reads_colors_from_passed_style() -> None:
    # A hardcoded-default implementation would pass every test above, because
    # the default palette equals the old baked-in constants. Override the digit
    # palette so the returned bands MUST come from the passed style, not from
    # inline hex. "220" -> digits 2,2,0; multiplier exponent 0 -> digit_colors[0].
    style = load_style(
        inline={
            "resistor": {
                "digit_colors": [
                    "#000000", "#111111", "#222222", "#333333", "#444444",
                    "#555555", "#666666", "#777777", "#888888", "#999999",
                ],
            },
        },
    )
    result = _resistor_bands("220", style)
    assert result == [
        "#222222",
        "#222222",
        "#000000",
        "#000000",
        style.color("resistor.tolerance"),
    ]


def test_resistor_bands_zero_returns_none() -> None:
    style = load_style()
    assert _resistor_bands("0", style) is None


def test_resistor_bands_invalid_returns_none() -> None:
    style = load_style()
    assert _resistor_bands("abc", style) is None
