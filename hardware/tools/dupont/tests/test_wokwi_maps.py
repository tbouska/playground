from __future__ import annotations

import pytest

from dupont.formats.wokwi.maps import (
    BOARD_TO_KIND,
    CANON_TO_WOKWI_PIN,
    GPIO_TO_PIN,
    KIND_TO_PART_TYPE,
    MAPS,
    PART_TYPE_PINS,
    PIN_TO_GPIO,
    WOKWI_PIN_TO_CANON,
    board_pin_to_canon,
    canon_pin_to_wokwi,
    legal_pins,
    wokwi_pin_to_canon,
)


def test_board_to_kind_maps_esp32_devkit_to_mcu() -> None:
    assert BOARD_TO_KIND["board-esp32-devkit-c-v4"] == "mcu"


@pytest.mark.parametrize(
    "gpio, pin",
    [("GPIO36", "VP"), ("GPIO39", "VN"), ("GPIO1", "TX"), ("GPIO3", "RX")],
    ids=["gpio36-vp", "gpio39-vn", "gpio1-tx", "gpio3-rx"],
)
def test_gpio_to_pin_has_expected_exceptions(gpio: str, pin: str) -> None:
    assert GPIO_TO_PIN[gpio] == pin


def test_pin_to_gpio_is_exact_inverse_of_gpio_to_pin() -> None:
    assert PIN_TO_GPIO == {pin: gpio for gpio, pin in GPIO_TO_PIN.items()}


@pytest.mark.parametrize(
    "kind, part_type",
    [
        ("mcu", "board-esp32-devkit-c-v4"),
        ("led", "wokwi-led"),
        ("led-rgb", "wokwi-rgb-led"),
        ("resistor", "wokwi-resistor"),
        ("button", "wokwi-pushbutton"),
    ],
    ids=["mcu", "led", "led-rgb", "resistor", "button"],
)
def test_kind_to_part_type_covers_hello_world_parts(kind: str, part_type: str) -> None:
    assert KIND_TO_PART_TYPE[kind] == part_type


@pytest.mark.parametrize(
    "part_type, pins",
    [
        ("wokwi-led", ("A", "C")),
        ("wokwi-rgb-led", ("R", "G", "B", "COM")),
        ("wokwi-resistor", ("1", "2")),
        ("wokwi-pushbutton", ("1.l", "2.l", "1.r", "2.r")),
    ],
    ids=["led", "rgb-led", "resistor", "pushbutton"],
)
def test_part_type_pins_has_canonical_order(part_type: str, pins: tuple[str, ...]) -> None:
    assert PART_TYPE_PINS[part_type] == pins


def test_wokwi_pin_to_canon_table_maps_led_anode_and_cathode() -> None:
    assert WOKWI_PIN_TO_CANON["led"] == {"A": "anode", "C": "cathode"}


def test_wokwi_pin_to_canon_table_maps_rgb_led_common_to_cathode() -> None:
    assert WOKWI_PIN_TO_CANON["led-rgb"]["COM"] == "cathode"


def test_canon_to_wokwi_pin_is_inverse_of_wokwi_pin_to_canon_per_kind() -> None:
    for kind, pin_map in WOKWI_PIN_TO_CANON.items():
        assert CANON_TO_WOKWI_PIN[kind] == {canon: wokwi for wokwi, canon in pin_map.items()}


def test_maps_aggregates_the_four_tables() -> None:
    assert MAPS == {
        "board_to_kind": BOARD_TO_KIND,
        "gpio_to_pin": GPIO_TO_PIN,
        "kind_to_part_type": KIND_TO_PART_TYPE,
        "part_type_pins": PART_TYPE_PINS,
    }


@pytest.mark.parametrize(
    "wokwi_pin, gpio",
    [("TX", "GPIO1"), ("RX", "GPIO3"), ("VP", "GPIO36"), ("VN", "GPIO39")],
    ids=["tx", "rx", "vp", "vn"],
)
def test_board_pin_to_canon_maps_named_exceptions_to_gpio(wokwi_pin: str, gpio: str) -> None:
    assert board_pin_to_canon(wokwi_pin) == gpio


@pytest.mark.parametrize(
    "wokwi_pin, gpio",
    [("2", "GPIO2"), ("23", "GPIO23")],
    ids=["single-digit", "multi-digit"],
)
def test_board_pin_to_canon_maps_bare_digit_to_gpio(wokwi_pin: str, gpio: str) -> None:
    assert board_pin_to_canon(wokwi_pin) == gpio


@pytest.mark.parametrize(
    "wokwi_pin",
    ["GND", "GND.3", "GND.0"],
    ids=["bare", "suffix-3", "suffix-0"],
)
def test_board_pin_to_canon_collapses_ground_bus_to_gnd(wokwi_pin: str) -> None:
    assert board_pin_to_canon(wokwi_pin) == "GND"


@pytest.mark.parametrize("wokwi_pin", ["3V3", "5V"], ids=["3v3", "5v"])
def test_board_pin_to_canon_passes_through_power_rails(wokwi_pin: str) -> None:
    assert board_pin_to_canon(wokwi_pin) == wokwi_pin


def test_board_pin_to_canon_raises_on_unmapped_pin() -> None:
    with pytest.raises(ValueError):
        board_pin_to_canon("FOO")


def test_wokwi_pin_to_canon_delegates_mcu_kind_to_board_pin_to_canon() -> None:
    assert wokwi_pin_to_canon("mcu", "TX") == "GPIO1"
    assert wokwi_pin_to_canon("mcu", "2") == "GPIO2"


@pytest.mark.parametrize(
    "kind, wokwi_pin, canon",
    [("led", "A", "anode"), ("led", "C", "cathode"), ("led-rgb", "COM", "cathode")],
    ids=["led-anode", "led-cathode", "rgb-common"],
)
def test_wokwi_pin_to_canon_applies_wokwi_local_aliasing(kind: str, wokwi_pin: str, canon: str) -> None:
    assert wokwi_pin_to_canon(kind, wokwi_pin) == canon


@pytest.mark.parametrize(
    "kind, wokwi_pin",
    [
        ("resistor", "1"),
        ("resistor", "2"),
        ("led-rgb", "R"),
        ("led-rgb", "G"),
        ("led-rgb", "B"),
        ("button", "1.l"),
    ],
    ids=["resistor-1", "resistor-2", "rgb-r", "rgb-g", "rgb-b", "button-1l"],
)
def test_wokwi_pin_to_canon_passes_through_unmapped_kinds_and_pins(kind: str, wokwi_pin: str) -> None:
    assert wokwi_pin_to_canon(kind, wokwi_pin) == wokwi_pin


@pytest.mark.parametrize(
    "kind, wokwi_pin",
    [("led", "A"), ("led", "C")],
    ids=["led-anode", "led-cathode"],
)
def test_canon_pin_to_wokwi_round_trips_led_pins(kind: str, wokwi_pin: str) -> None:
    canon = wokwi_pin_to_canon(kind, wokwi_pin)
    assert canon_pin_to_wokwi(kind, canon) == wokwi_pin


def test_canon_pin_to_wokwi_maps_gpio_number_to_bare_digit() -> None:
    assert canon_pin_to_wokwi("mcu", "GPIO2") == "2"


def test_canon_pin_to_wokwi_maps_gnd_to_gnd_zero() -> None:
    assert canon_pin_to_wokwi("mcu", "GND") == "GND.0"


@pytest.mark.parametrize(
    "gpio, label",
    [("GPIO1", "TX"), ("GPIO3", "RX"), ("GPIO36", "VP"), ("GPIO39", "VN")],
    ids=["gpio1-tx", "gpio3-rx", "gpio36-vp", "gpio39-vn"],
)
def test_canon_pin_to_wokwi_emits_gpio_board_label_exceptions(gpio: str, label: str) -> None:
    # Export must be the exact inverse of board_pin_to_canon: the alt-name GPIOs
    # emit their board label (TX/RX/VP/VN), not the bare digit, or the exported
    # diagram carries illegal board pins.
    assert canon_pin_to_wokwi("mcu", gpio) == label
    assert board_pin_to_canon(label) == gpio


@pytest.mark.parametrize(
    "part_type, pins",
    [
        ("wokwi-led", ("A", "C")),
        ("wokwi-rgb-led", ("R", "G", "B", "COM")),
        ("wokwi-resistor", ("1", "2")),
        ("wokwi-pushbutton", ("1.l", "2.l", "1.r", "2.r")),
    ],
    ids=["led", "rgb-led", "resistor", "pushbutton"],
)
def test_legal_pins_returns_part_type_pins_entry(part_type: str, pins: tuple[str, ...]) -> None:
    assert legal_pins(part_type) == pins


def test_legal_pins_raises_on_unmapped_part_type() -> None:
    with pytest.raises(ValueError):
        legal_pins("nonsense")
