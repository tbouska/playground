"""Behavior-lock tests for Geometry.hole address->coordinate mapping.

These tests lock the CURRENT behavior of Geometry.hole as of the time they
were written. The SUT (render_layout.py) must NOT be modified. All expected
values were captured by running Geometry(63).hole(addr) directly.
"""

import pytest

from breadboard.geometry import Geometry

GEO = Geometry(63)


@pytest.mark.parametrize(
    "address, expected",
    [
        ("B1", (1.0, -4.0)),
        ("I19", (19.0, -12.0)),
        ("E37", (37.0, -7.0)),
    ],
)
def test_hole_grid_address_maps_to_column_and_row(
    address: str, expected: tuple[float, float]
) -> None:
    assert GEO.hole(address) == expected


@pytest.mark.parametrize(
    "address, expected",
    [
        ("B-31", (31.0, -16.0)),
        ("T+1", (1.0, 0.0)),
    ],
)
def test_hole_rail_address_resolves_to_rail_row(
    address: str, expected: tuple[float, float]
) -> None:
    assert GEO.hole(address) == expected


def test_hole_invalid_letter_raises_value_error() -> None:
    with pytest.raises(ValueError):
        GEO.hole("Z9")
