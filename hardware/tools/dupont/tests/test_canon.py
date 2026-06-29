from __future__ import annotations

import pytest
from dupont.canon.ids import mint_id, mint_ids
from dupont.canon.pins import denormalize_pin_name, normalize_pin_name


# ── mint_id ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kind, ordinal, expected",
    [
        ("mcu", 1, "U1"),
        ("led", 1, "D1"),
        ("resistor", 2, "R2"),
        ("button", 1, "SW1"),  # multi-char prefix
        ("led-rgb", 3, "D3"),  # hyphenated kind, shares "D" prefix
    ],
    ids=["mcu-1", "led-1", "resistor-2", "button-1", "led-rgb-3"],
)
def test_mint_id_returns_prefix_and_ordinal(kind: str, ordinal: int, expected: str) -> None:
    assert mint_id(kind, ordinal) == expected


@pytest.mark.parametrize(
    "kind",
    ["capacitor", "diode"],
    ids=["capacitor", "diode"],
)
def test_mint_id_raises_on_unknown_kind(kind: str) -> None:
    with pytest.raises(ValueError):
        mint_id(kind, 1)


# ── mint_ids ──────────────────────────────────────────────────────────────────


def test_mint_ids_empty_list_returns_empty() -> None:
    assert mint_ids([]) == []


@pytest.mark.parametrize(
    "kinds, expected",
    [
        # basic mixed case — each prefix counts independently, not globally
        (["mcu", "resistor", "led"], ["U1", "R1", "D1"]),
        # two leds — counter increments within prefix
        (["led", "led"], ["D1", "D2"]),
        # interleaved kinds — declaration order governs, not kind-group order
        (["mcu", "led", "resistor", "led"], ["U1", "D1", "R1", "D2"]),
        # led and led-rgb share the "D" prefix counter
        (["led", "led-rgb"], ["D1", "D2"]),
    ],
    ids=["mixed-three", "two-leds", "interleaved-led", "led-and-led-rgb-share-D"],
)
def test_mint_ids_numbers_each_prefix_in_declaration_order(
    kinds: list[str], expected: list[str]
) -> None:
    assert mint_ids(kinds) == expected


def test_mint_ids_raises_on_unknown_kind_in_list() -> None:
    with pytest.raises(ValueError):
        mint_ids(["mcu", "capacitor", "led"])


# ── normalize_pin_name ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kind, raw_name, expected",
    [
        # led: named pins map to canonical names
        ("led", "A", "anode"),
        ("led", "K", "cathode"),
        # led-rgb: cathode maps; distinct anodes pass through unchanged
        ("led-rgb", "K", "cathode"),
        ("led-rgb", "R", "R"),
        ("led-rgb", "G", "G"),
        ("led-rgb", "B", "B"),
        # identity kinds
        ("mcu", "GPIO2", "GPIO2"),
        ("resistor", "1", "1"),
        ("button", "gpio", "gpio"),
    ],
    ids=[
        "led-A", "led-K",
        "led-rgb-K", "led-rgb-R", "led-rgb-G", "led-rgb-B",
        "mcu-GPIO2", "resistor-1", "button-gpio",
    ],
)
def test_normalize_pin_name_maps_correctly(
    kind: str, raw_name: str, expected: str
) -> None:
    assert normalize_pin_name(kind, raw_name) == expected


@pytest.mark.parametrize(
    "kind, raw_name",
    [
        ("led", "Z"),          # known kind, unknown pin
        ("capacitor", "+"),    # unknown kind entirely
    ],
    ids=["led-unknown-pin", "unknown-kind"],
)
def test_normalize_pin_name_returns_raw_for_unknown_pair(
    kind: str, raw_name: str
) -> None:
    assert normalize_pin_name(kind, raw_name) == raw_name


# ── denormalize_pin_name ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kind, canonical, expected",
    [
        ("led", "anode", "A"),
        ("led", "cathode", "K"),
        # led-rgb cathode inverts to "K"; anodes are identity
        ("led-rgb", "cathode", "K"),
        ("led-rgb", "R", "R"),
        # identity kind
        ("mcu", "GPIO2", "GPIO2"),
    ],
    ids=["led-anode", "led-cathode", "led-rgb-cathode", "led-rgb-R", "mcu-GPIO2"],
)
def test_denormalize_pin_name_inverts_correctly(
    kind: str, canonical: str, expected: str
) -> None:
    assert denormalize_pin_name(kind, canonical) == expected


# ── round-trip ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kind, raw_name",
    [
        ("led", "A"),
        ("led", "K"),
        ("led-rgb", "K"),
        ("led-rgb", "R"),
    ],
    ids=["led-A", "led-K", "led-rgb-K", "led-rgb-R"],
)
def test_normalize_then_denormalize_returns_original_raw_name(
    kind: str, raw_name: str
) -> None:
    assert denormalize_pin_name(kind, normalize_pin_name(kind, raw_name)) == raw_name
