"""Tests for dupont.formats.circuit.exporter.

Verifies that collapse_to_schematic collapses the pin-level interchange Circuit
model back into the native Schematic value objects, and that export_circuit
serializes correctly with a stable round-trip through export + reimport.

All tests are black-box: they assert the published contract, not implementation
details.
"""

from pathlib import Path

import yaml
import pytest

from dupont.formats.circuit.importer import import_circuit
from dupont.formats.circuit.exporter import collapse_to_schematic, export_circuit
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
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef, Role

# ---------------------------------------------------------------------------
# Fixture paths (mirror test_importer convention)
# ---------------------------------------------------------------------------

_HW = Path(__file__).resolve().parents[3]
_HELLO_WORLD = _HW / "arduino-ide-sketchbook/espx/espx-1-1-2-hello-world/circuit.yaml"
_RGB_RAINBOW = (
    _HW
    / "arduino-ide-sketchbook"
    / "keyestudio-esp32-learning-kit-basic-edition"
    / "rgb-led-rainbow-cycle"
    / "circuit.yaml"
)
_RGB_MODES = (
    _HW
    / "arduino-ide-sketchbook"
    / "keyestudio-esp32-learning-kit-basic-edition"
    / "rgb-modes"
    / "circuit.yaml"
)

# ---------------------------------------------------------------------------
# Expected collapsed Schematics (authoritative round-trip targets)
# ---------------------------------------------------------------------------

_EXPECTED_HELLO_WORLD = Schematic(
    title="ESP32 Hello World",
    mcu=Mcu("ESP32-WROOM-32 DevKit", (PowerPin("GND", "GND"),)),
    load=Load("LED", TerminalPin("K", "GND")),
    channels=(Channel("GPIO2", "A", Resistor("R1", "220Ω")),),
    buttons=(),
)

_EXPECTED_RGB_RAINBOW = Schematic(
    title="ESP32 RGB LED",
    mcu=Mcu("ESP32-WROOM-32 DevKit", (PowerPin("VIN", "+5V"), PowerPin("GND", "GND"))),
    load=Load("RGB LED (common cathode)", TerminalPin("K", "GND")),
    channels=(
        Channel("GPIO0", "R", Resistor("R1", "220Ω")),
        Channel("GPIO2", "G", Resistor("R2", "220Ω")),
        Channel("GPIO15", "B", Resistor("R3", "220Ω")),
    ),
    buttons=(),
)

_EXPECTED_RGB_MODES = Schematic(
    title="ESP32 RGB LED modes",
    mcu=Mcu("ESP32-WROOM-32 DevKit", (PowerPin("VIN", "+5V"), PowerPin("GND", "GND"))),
    load=Load("RGB LED (common cathode)", TerminalPin("K", "GND")),
    channels=(
        Channel("GPIO0", "R", Resistor("R1", "220Ω")),
        Channel("GPIO2", "G", Resistor("R2", "220Ω")),
        Channel("GPIO15", "B", Resistor("R3", "220Ω")),
    ),
    buttons=(Button("SW1", "GPIO14", "GND"),),
)

# ---------------------------------------------------------------------------
# Minimal hand-built Circuit objects for fail-loud tests
# ---------------------------------------------------------------------------

# Case (a): mcu + series_resistor but NO led/load component or role.
_NO_LOAD_CIRCUIT = Circuit(
    title="No Load",
    components=(
        Component(
            "U1",
            "mcu",
            (Pin("GPIO2", "GPIO2", "gpio", 0),),
            label="MCU",
        ),
        Component(
            "R1",
            "resistor",
            (Pin("1", "1", "passive", 0), Pin("2", "2", "passive", 1)),
            value="220Ω",
        ),
    ),
    nets=(
        Net("_net1", (PinRef("U1", "GPIO2"), PinRef("R1", "1")), "schematic/channel"),
        Net("_net2", (PinRef("R1", "2"),), "schematic/channel"),
    ),
    roles=(
        Role("U1", "mcu", "inferred"),
        Role("R1", "series_resistor", "inferred"),
    ),
)

# Case (b): led/load component is present, but the series_resistor's two nets
# both carry only MCU gpio pins — no load anode pin on either net, so no
# channel can be formed.
_BAD_CHANNEL_CIRCUIT = Circuit(
    title="Bad Channel",
    components=(
        Component(
            "U1",
            "mcu",
            (
                Pin("GND", "GND", "power", 0),
                Pin("GPIO2", "GPIO2", "gpio", 1),
                Pin("GPIO4", "GPIO4", "gpio", 2),
            ),
            label="MCU",
        ),
        Component(
            "R1",
            "resistor",
            (Pin("1", "1", "passive", 0), Pin("2", "2", "passive", 1)),
            value="220Ω",
        ),
        Component(
            "D1",
            "led",
            (
                Pin("anode", "anode", "passive", 0),
                Pin("cathode", "cathode", "passive", 1),
            ),
            label="LED",
        ),
    ),
    nets=(
        Net("_net1", (PinRef("U1", "GPIO2"), PinRef("R1", "1")), "schematic/channel"),
        # Both sides of R1 connect to MCU gpio pins; no load anode pin on either.
        Net("_net2", (PinRef("U1", "GPIO4"), PinRef("R1", "2")), "schematic/channel"),
        Net("GND", (PinRef("U1", "GND"), PinRef("D1", "cathode")), "schematic/common"),
    ),
    roles=(
        Role("U1", "mcu", "inferred"),
        Role("R1", "series_resistor", "inferred"),
        Role("D1", "load", "inferred"),
        Role("GND", "common_net", "inferred"),
    ),
)


# ---------------------------------------------------------------------------
# 1-3: collapse_to_schematic produces correct Schematic for each fixture
# ---------------------------------------------------------------------------


def test_hello_world_collapse_produces_correct_schematic():
    """Single channel: title, mcu label+power, load label+common, channel, no buttons."""
    assert collapse_to_schematic(import_circuit(_HELLO_WORLD)) == _EXPECTED_HELLO_WORLD


def test_rgb_rainbow_collapse_produces_correct_schematic():
    """Three channels, two power pins (VIN + GND), no buttons."""
    assert collapse_to_schematic(import_circuit(_RGB_RAINBOW)) == _EXPECTED_RGB_RAINBOW


def test_rgb_modes_collapse_produces_correct_schematic():
    """Three channels plus one button; button gpio and far-leg net are correct."""
    assert collapse_to_schematic(import_circuit(_RGB_MODES)) == _EXPECTED_RGB_MODES


# ---------------------------------------------------------------------------
# 4: export_circuit for fixture A — non-empty string + re-parsed YAML content
# ---------------------------------------------------------------------------


def test_hello_world_export_yaml_content():
    """export_circuit returns a non-empty YAML string that re-parses to the
    source channel structure (comments dropped, values preserved)."""
    yaml_text = export_circuit(import_circuit(_HELLO_WORLD))
    assert isinstance(yaml_text, str) and yaml_text.strip()

    data = yaml.safe_load(yaml_text)
    assert data["title"] == "ESP32 Hello World"
    assert data["mcu"]["power"] == [{"pin": "GND", "net": "GND"}]
    assert data["load"]["common"] == {"pin": "K", "net": "GND"}
    assert len(data["channels"]) == 1
    ch = data["channels"][0]
    assert ch["gpio"] == "GPIO2"
    assert ch["load_pin"] == "A"
    assert ch["resistor"]["ref"] == "R1"
    assert ch["resistor"]["value"] == "220Ω"


# ---------------------------------------------------------------------------
# 5: round-trip model stability — import → export → reimport == import
# ---------------------------------------------------------------------------


def test_roundtrip_stability_hello_world():
    """Export then reimport gives the identical Circuit as a direct import."""
    original = import_circuit(_HELLO_WORLD)
    assert import_circuit(export_circuit(original)) == original


def test_roundtrip_stability_rgb_rainbow():
    """Three-channel export + reimport is stable."""
    original = import_circuit(_RGB_RAINBOW)
    assert import_circuit(export_circuit(original)) == original


def test_roundtrip_stability_rgb_modes():
    """Three-channel + button export + reimport is stable."""
    original = import_circuit(_RGB_MODES)
    assert import_circuit(export_circuit(original)) == original


# ---------------------------------------------------------------------------
# 6: channel ORDER is preserved (source declaration order, not sorted)
# ---------------------------------------------------------------------------


def test_channel_order_preserved_rgb_rainbow():
    """Channels are emitted in resistor declaration order: R1/GPIO0, R2/GPIO2, R3/GPIO15."""
    schematic = collapse_to_schematic(import_circuit(_RGB_RAINBOW))
    assert schematic.channels[0] == Channel("GPIO0", "R", Resistor("R1", "220Ω"))
    assert schematic.channels[1] == Channel("GPIO2", "G", Resistor("R2", "220Ω"))
    assert schematic.channels[2] == Channel("GPIO15", "B", Resistor("R3", "220Ω"))


def test_channel_order_preserved_rgb_modes():
    """Channel order is unaffected by the presence of a button."""
    schematic = collapse_to_schematic(import_circuit(_RGB_MODES))
    assert schematic.channels[0] == Channel("GPIO0", "R", Resistor("R1", "220Ω"))
    assert schematic.channels[1] == Channel("GPIO2", "G", Resistor("R2", "220Ω"))
    assert schematic.channels[2] == Channel("GPIO15", "B", Resistor("R3", "220Ω"))


# ---------------------------------------------------------------------------
# 7: fail-loud — ValueError when the netlist cannot collapse
# ---------------------------------------------------------------------------


def test_fail_loud_no_load_component():
    """ValueError when no led/load component or role exists in the Circuit."""
    with pytest.raises(ValueError):
        collapse_to_schematic(_NO_LOAD_CIRCUIT)


def test_fail_loud_resistor_nets_have_no_load_anode():
    """ValueError when both nets of a series_resistor connect only to MCU pins."""
    with pytest.raises(ValueError):
        collapse_to_schematic(_BAD_CHANNEL_CIRCUIT)
