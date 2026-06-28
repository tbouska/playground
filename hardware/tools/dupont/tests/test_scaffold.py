"""Scaffold tests for the consolidated ``dupont`` package.

These tests pin the public contract of the schematic side of the package after
both renderers are consolidated into ``dupont``:

- The frozen-dataclass circuit schema is importable with exact field names.
- ``dupont.render.schematic`` exposes the draw entry points.
- ``load_circuit`` parses the existing project ``circuit.yaml`` files into the
  expected ``Schematic`` shape.
- ``render`` writes an ``.svg`` and a ``.png`` for a parsed schematic.

The breadboard renderer's golden-parity suite moves with the package and is out
of scope here.
"""

import dataclasses
from pathlib import Path

import pytest

from dupont.formats.circuit.schema import (
    Button,
    Channel,
    Load,
    Mcu,
    PowerPin,
    Resistor,
    Schematic,
    TerminalPin,
)
from dupont.render.schematic import build_drawing, load_circuit, render

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Expected field names, in declaration order, for every schema dataclass.
_SCHEMA_FIELDS = {
    Resistor: ("ref", "value"),
    Channel: ("gpio", "load_pin", "resistor"),
    Button: ("ref", "gpio", "net"),
    PowerPin: ("pin", "net"),
    TerminalPin: ("pin", "net"),
    Mcu: ("label", "power"),
    Load: ("label", "common"),
    Schematic: ("title", "mcu", "load", "channels", "buttons"),
}

# One constructed instance of each schema type. Building these proves the
# kwargs above are accepted, and gives the frozen-ness test concrete targets.
_RESISTOR = Resistor(ref="R1", value="220Ω")
_POWER_PIN = PowerPin(pin="GND", net="GND")
_TERMINAL_PIN = TerminalPin(pin="K", net="GND")
_CHANNEL = Channel(gpio="GPIO2", load_pin="A", resistor=_RESISTOR)
_BUTTON = Button(ref="SW1", gpio="GPIO14", net="GND")
_MCU = Mcu(label="ESP32", power=(_POWER_PIN,))
_LOAD = Load(label="LED", common=_TERMINAL_PIN)
_SCHEMATIC = Schematic(
    title="T",
    mcu=_MCU,
    load=_LOAD,
    channels=(_CHANNEL,),
    buttons=(_BUTTON,),
)

_INSTANCES = [
    _RESISTOR,
    _POWER_PIN,
    _TERMINAL_PIN,
    _CHANNEL,
    _BUTTON,
    _MCU,
    _LOAD,
    _SCHEMATIC,
]


@pytest.fixture
def hello_world_circuit_path() -> Path:
    path = (
        _REPO_ROOT
        / "hardware"
        / "arduino-ide-sketchbook"
        / "espx"
        / "espx-1-1-2-hello-world"
        / "circuit.yaml"
    )
    assert path.exists(), f"hello-world circuit not found at {path}"
    return path


@pytest.fixture
def rgb_modes_circuit_path() -> Path:
    path = (
        _REPO_ROOT
        / "hardware"
        / "arduino-ide-sketchbook"
        / "keyestudio-esp32-learning-kit-basic-edition"
        / "rgb-modes"
        / "circuit.yaml"
    )
    assert path.exists(), f"rgb-modes circuit not found at {path}"
    return path


def test_package_exposes_schema_and_draw_entry_points() -> None:
    assert dataclasses.is_dataclass(Schematic)
    assert callable(load_circuit)
    assert callable(build_drawing)
    assert callable(render)


@pytest.mark.parametrize(
    "cls, expected_fields",
    list(_SCHEMA_FIELDS.items()),
    ids=lambda value: value.__name__ if isinstance(value, type) else "",
)
def test_schema_classes_are_dataclasses_with_expected_fields(
    cls: type, expected_fields: tuple[str, ...]
) -> None:
    assert dataclasses.is_dataclass(cls)
    assert tuple(f.name for f in dataclasses.fields(cls)) == expected_fields


@pytest.mark.parametrize(
    "instance", _INSTANCES, ids=lambda inst: type(inst).__name__
)
def test_schema_instances_are_frozen(instance: object) -> None:
    field_name = dataclasses.fields(instance)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, field_name, "mutated")


def test_resistor_construction_round_trips() -> None:
    resistor = Resistor(ref="R1", value="220")
    assert resistor.ref == "R1"
    assert resistor.value == "220"


def test_load_circuit_parses_hello_world_metadata(
    hello_world_circuit_path: Path,
) -> None:
    schematic = load_circuit(hello_world_circuit_path)
    assert isinstance(schematic, Schematic)
    assert schematic.title == "ESP32 Hello World"
    assert schematic.mcu.label == "ESP32-WROOM-32 DevKit"
    assert schematic.mcu.power == (PowerPin(pin="GND", net="GND"),)
    assert schematic.load.common == TerminalPin(pin="K", net="GND")


def test_load_circuit_parses_hello_world_channel(
    hello_world_circuit_path: Path,
) -> None:
    schematic = load_circuit(hello_world_circuit_path)
    assert schematic.channels == (
        Channel(
            gpio="GPIO2",
            load_pin="A",
            resistor=Resistor(ref="R1", value="220Ω"),
        ),
    )
    assert schematic.buttons == ()


def test_load_circuit_parses_rgb_modes_channels(
    rgb_modes_circuit_path: Path,
) -> None:
    schematic = load_circuit(rgb_modes_circuit_path)
    assert len(schematic.channels) == 3
    assert tuple(ch.load_pin for ch in schematic.channels) == ("R", "G", "B")
    assert len(schematic.mcu.power) == 2


def test_load_circuit_parses_rgb_modes_button(
    rgb_modes_circuit_path: Path,
) -> None:
    schematic = load_circuit(rgb_modes_circuit_path)
    assert schematic.buttons == (
        Button(ref="SW1", gpio="GPIO14", net="GND"),
    )


def test_render_writes_svg_and_png(
    hello_world_circuit_path: Path, tmp_path: Path
) -> None:
    out_stem = tmp_path / "out"
    render(load_circuit(hello_world_circuit_path), out_stem)

    svg_path = out_stem.with_suffix(".svg")
    png_path = out_stem.with_suffix(".png")
    assert svg_path.exists(), f"render() did not write {svg_path}"
    assert png_path.exists(), f"render() did not write {png_path}"
    assert svg_path.stat().st_size > 0
    assert png_path.stat().st_size > 0
