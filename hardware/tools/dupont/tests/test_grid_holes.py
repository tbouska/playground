"""Contract tests for the breadboard hole-address grid (dupont/grid/holes.py).

These tests pin the hole-address contract: classifying an address into its
electrical base node (node_key) and its integer grid position (hole_coords),
independent of any renderer. Values are taken from the PRD contract, not from
running an implementation.
"""

import pytest

from dupont.grid.holes import (
    BANK_LOWER,
    BANK_UPPER,
    PITCH_MM,
    HoleAddr,
    hole_coords,
    node_key,
    parse_hole,
)


def test_pitch_mm_is_standard_2_54() -> None:
    assert PITCH_MM == 2.54


def test_bank_upper_and_lower_partition_grid_letters() -> None:
    assert BANK_UPPER == frozenset("ABCDE")
    assert BANK_LOWER == frozenset("FGHIJ")


@pytest.mark.parametrize(
    "address, expected",
    [
        ("B1", HoleAddr(kind="grid", line="B", column=1)),
        ("B-30", HoleAddr(kind="rail", line="B-", column=30)),
    ],
)
def test_parse_hole_classifies_grid_and_rail_addresses(
    address: str, expected: HoleAddr
) -> None:
    assert parse_hole(address) == expected


@pytest.mark.parametrize(
    "address, expected",
    [
        ("A1", ("bank", "upper", 1)),
        ("E1", ("bank", "upper", 1)),
        ("F1", ("bank", "lower", 1)),
        ("J13", ("bank", "lower", 13)),
    ],
)
def test_node_key_grid_address_resolves_to_bank_and_column(
    address: str, expected: tuple
) -> None:
    assert node_key(address) == expected


def test_upper_and_lower_banks_are_distinct_nodes_at_same_column() -> None:
    assert node_key("A1") == node_key("E1")
    assert node_key("F1") != node_key("A1")


@pytest.mark.parametrize(
    "address, expected",
    [
        ("B-30", ("rail", "B-")),
        ("T+1", ("rail", "T+")),
    ],
)
def test_node_key_rail_address_resolves_to_rail_line(
    address: str, expected: tuple
) -> None:
    assert node_key(address) == expected


@pytest.mark.parametrize(
    "address, expected",
    [
        ("B1", (1, 4)),
        ("I19", (19, 12)),
        ("E37", (37, 7)),
        ("T+1", (1, 0)),
        ("B-31", (31, 16)),
    ],
)
def test_hole_coords_maps_address_to_pitch_grid_position(
    address: str, expected: tuple[int, int]
) -> None:
    assert hole_coords(address) == expected


@pytest.mark.parametrize("address", ["Z9", "K1", ""])
def test_parse_hole_unknown_address_raises_value_error(address: str) -> None:
    with pytest.raises(ValueError):
        parse_hole(address)


@pytest.mark.parametrize("address", ["Z9", "K1", ""])
def test_node_key_unknown_address_raises_value_error(address: str) -> None:
    with pytest.raises(ValueError):
        node_key(address)


@pytest.mark.parametrize("address", ["Z9", "K1", ""])
def test_hole_coords_unknown_address_raises_value_error(address: str) -> None:
    with pytest.raises(ValueError):
        hole_coords(address)
