from __future__ import annotations

BOARD_TO_KIND: dict[str, str] = {"board-esp32-devkit-c-v4": "mcu"}

GPIO_TO_PIN: dict[str, str] = {
    "GPIO36": "VP",
    "GPIO39": "VN",
    "GPIO1": "TX",
    "GPIO3": "RX",
}

PIN_TO_GPIO: dict[str, str] = {v: k for k, v in GPIO_TO_PIN.items()}

KIND_TO_PART_TYPE: dict[str, str] = {
    "mcu": "board-esp32-devkit-c-v4",
    "led": "wokwi-led",
    "led-rgb": "wokwi-rgb-led",
    "resistor": "wokwi-resistor",
    "button": "wokwi-pushbutton",
}

PART_TYPE_PINS: dict[str, tuple[str, ...]] = {
    "wokwi-led": ("A", "C"),
    "wokwi-rgb-led": ("R", "G", "B", "COM"),
    "wokwi-resistor": ("1", "2"),
    "wokwi-pushbutton": ("1.l", "2.l", "1.r", "2.r"),
}

WOKWI_PIN_TO_CANON: dict[str, dict[str, str]] = {
    "led": {"A": "anode", "C": "cathode"},
    "led-rgb": {"COM": "cathode"},
}

CANON_TO_WOKWI_PIN: dict[str, dict[str, str]] = {
    kind: {canon: wokwi for wokwi, canon in pin_map.items()}
    for kind, pin_map in WOKWI_PIN_TO_CANON.items()
}

MAPS: dict[str, dict] = {
    "board_to_kind": BOARD_TO_KIND,
    "gpio_to_pin": GPIO_TO_PIN,
    "kind_to_part_type": KIND_TO_PART_TYPE,
    "part_type_pins": PART_TYPE_PINS,
}


def board_pin_to_canon(wokwi_pin: str) -> str:
    if wokwi_pin in PIN_TO_GPIO:
        return PIN_TO_GPIO[wokwi_pin]
    if wokwi_pin.isdigit():
        return f"GPIO{wokwi_pin}"
    if wokwi_pin == "GND" or wokwi_pin.startswith("GND."):
        return "GND"
    if wokwi_pin in ("3V3", "5V"):
        return wokwi_pin
    raise ValueError(f"unmapped board pin: {wokwi_pin!r}")


def wokwi_pin_to_canon(kind: str, wokwi_pin: str) -> str:
    if kind == "mcu":
        return board_pin_to_canon(wokwi_pin)
    if kind in WOKWI_PIN_TO_CANON and wokwi_pin in WOKWI_PIN_TO_CANON[kind]:
        return WOKWI_PIN_TO_CANON[kind][wokwi_pin]
    return wokwi_pin


def canon_pin_to_wokwi(kind: str, canon_pin: str) -> str:
    if kind == "mcu":
        if canon_pin == "GND":
            return "GND.0"
        if canon_pin in GPIO_TO_PIN:
            return GPIO_TO_PIN[canon_pin]
        if canon_pin.startswith("GPIO"):
            return canon_pin[4:]
    if kind in CANON_TO_WOKWI_PIN and canon_pin in CANON_TO_WOKWI_PIN[kind]:
        return CANON_TO_WOKWI_PIN[kind][canon_pin]
    return canon_pin


def legal_pins(part_type: str) -> tuple[str, ...]:
    if part_type not in PART_TYPE_PINS:
        raise ValueError(f"unmapped part_type: {part_type!r}")
    return PART_TYPE_PINS[part_type]
