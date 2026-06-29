"""Tests for dupont.formats.circuit.importer.import_circuit.

Verifies semantic expansion of compact circuit.yaml descriptions into pin-level
interchange Circuit models. All tests are black-box: they assert the published
contract, not any implementation detail.
"""

from pathlib import Path

import pytest

from dupont.formats.circuit.importer import import_circuit
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef, Role

# ---------------------------------------------------------------------------
# Fixture paths (relative to the hardware/ root, three levels above this file)
# ---------------------------------------------------------------------------

_HW = Path(__file__).resolve().parents[3]
_HELLO_WORLD = (
    _HW
    / "arduino-ide-sketchbook/espx/espx-1-1-2-hello-world/circuit.yaml"
)
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
# Helpers
# ---------------------------------------------------------------------------


def _net_members(net: Net) -> set[tuple[str, str]]:
    return {(r.instance_id, r.pin) for r in net.member_pin_refs}


def _component(circuit: Circuit, instance_id: str) -> Component:
    for c in circuit.components:
        if c.instance_id == instance_id:
            return c
    raise KeyError(f"No component with id {instance_id!r}")


def _net_by_id(circuit: Circuit, net_id: str) -> Net:
    for n in circuit.nets:
        if n.net_id == net_id:
            return n
    raise KeyError(f"No net with id {net_id!r}")


def _net_by_members(circuit: Circuit, expected: set[tuple[str, str]]) -> Net:
    for n in circuit.nets:
        if _net_members(n) == expected:
            return n
    raise KeyError(f"No net with members {expected}")


# ---------------------------------------------------------------------------
# Fixture A — espx-1-1-2-hello-world (single LED, single channel)
# ---------------------------------------------------------------------------


def test_hello_world_title():
    assert import_circuit(_HELLO_WORLD).title == "ESP32 Hello World"


def test_hello_world_mcu_component():
    circuit = import_circuit(_HELLO_WORLD)
    u1 = _component(circuit, "U1")
    assert u1.kind == "mcu"
    assert u1.label == "ESP32-WROOM-32 DevKit"
    assert u1.pins == (
        Pin("GND", "GND", "power", 0),
        Pin("GPIO2", "GPIO2", "gpio", 1),
    )


def test_hello_world_resistor_component():
    circuit = import_circuit(_HELLO_WORLD)
    r1 = _component(circuit, "R1")
    assert r1.kind == "resistor"
    assert r1.value == "220Ω"
    assert r1.pins == (
        Pin("1", "1", "passive", 0),
        Pin("2", "2", "passive", 1),
    )


def test_hello_world_led_kind_is_led_not_led_rgb():
    """Single channel must produce kind 'led', not 'led-rgb'."""
    d1 = _component(import_circuit(_HELLO_WORLD), "D1")
    assert d1.kind == "led"


def test_hello_world_led_pins_normalize_a_and_k():
    """'A' -> 'anode' and 'K' -> 'cathode' for a single-channel LED."""
    d1 = _component(import_circuit(_HELLO_WORLD), "D1")
    assert d1.pins == (
        Pin("anode", "anode", "passive", 0),
        Pin("cathode", "cathode", "passive", 1),
    )


def test_hello_world_exactly_three_nets():
    assert len(import_circuit(_HELLO_WORLD).nets) == 3


def test_hello_world_gpio_to_resistor_channel_net():
    circuit = import_circuit(_HELLO_WORLD)
    net = _net_by_members(circuit, {("U1", "GPIO2"), ("R1", "1")})
    assert net.provenance == "schematic/channel"


def test_hello_world_resistor_to_led_channel_net():
    circuit = import_circuit(_HELLO_WORLD)
    net = _net_by_members(circuit, {("R1", "2"), ("D1", "anode")})
    assert net.provenance == "schematic/channel"


def test_hello_world_gnd_named_net_id_and_members_and_provenance():
    """Named net uses the source net name as net_id; cathode and MCU GND merged."""
    circuit = import_circuit(_HELLO_WORLD)
    gnd = _net_by_id(circuit, "GND")
    assert _net_members(gnd) == {("U1", "GND"), ("D1", "cathode")}
    assert gnd.provenance == "schematic/common"


def test_hello_world_no_duplicate_gnd_net():
    """MCU power and LED common both reference GND - only one GND net may exist."""
    circuit = import_circuit(_HELLO_WORLD)
    assert sum(1 for n in circuit.nets if n.net_id == "GND") == 1


def test_hello_world_roles():
    roles = set(import_circuit(_HELLO_WORLD).roles)
    assert Role("U1", "mcu", "inferred") in roles
    assert Role("R1", "series_resistor", "inferred") in roles
    assert Role("D1", "load", "inferred") in roles
    assert Role("GND", "common_net", "inferred") in roles


def test_hello_world_no_power_net_role_when_power_equals_common_net():
    """GND is both the common net and the only power net; no power_net role emitted."""
    power_roles = [r for r in import_circuit(_HELLO_WORLD).roles if r.tag == "power_net"]
    assert power_roles == []


def test_hello_world_exactly_four_roles():
    """Exact role count: U1/mcu + R1/series_resistor + D1/load + GND/common_net."""
    assert len(import_circuit(_HELLO_WORLD).roles) == 4


# ---------------------------------------------------------------------------
# Fixture B - rgb-led-rainbow-cycle (RGB LED, 3 channels, no buttons)
# ---------------------------------------------------------------------------


def test_rgb_rainbow_title():
    assert import_circuit(_RGB_RAINBOW).title == "ESP32 RGB LED"


def test_rgb_rainbow_led_kind_is_led_rgb():
    """Three channels must produce kind 'led-rgb'."""
    d1 = _component(import_circuit(_RGB_RAINBOW), "D1")
    assert d1.kind == "led-rgb"


def test_rgb_rainbow_led_pins_keep_rgb_names_and_normalize_cathode():
    """For led-rgb, R/G/B are kept as-is; K -> 'cathode'; cathode is last."""
    d1 = _component(import_circuit(_RGB_RAINBOW), "D1")
    assert d1.pins == (
        Pin("R", "R", "passive", 0),
        Pin("G", "G", "passive", 1),
        Pin("B", "B", "passive", 2),
        Pin("cathode", "cathode", "passive", 3),
    )


def test_rgb_rainbow_mcu_pin_order_power_then_gpio():
    """Power pins first (declaration order), then channel GPIOs (channel order)."""
    u1 = _component(import_circuit(_RGB_RAINBOW), "U1")
    assert u1.pins == (
        Pin("VIN", "VIN", "power", 0),
        Pin("GND", "GND", "power", 1),
        Pin("GPIO0", "GPIO0", "gpio", 2),
        Pin("GPIO2", "GPIO2", "gpio", 3),
        Pin("GPIO15", "GPIO15", "gpio", 4),
    )


def test_rgb_rainbow_exactly_eight_nets():
    assert len(import_circuit(_RGB_RAINBOW).nets) == 8


def test_rgb_rainbow_six_channel_nets():
    circuit = import_circuit(_RGB_RAINBOW)
    expected_channel_members = [
        {("U1", "GPIO0"), ("R1", "1")},
        {("R1", "2"), ("D1", "R")},
        {("U1", "GPIO2"), ("R2", "1")},
        {("R2", "2"), ("D1", "G")},
        {("U1", "GPIO15"), ("R3", "1")},
        {("R3", "2"), ("D1", "B")},
    ]
    for members in expected_channel_members:
        net = _net_by_members(circuit, members)
        assert net.provenance == "schematic/channel"


def test_rgb_rainbow_gnd_net_members_and_provenance():
    circuit = import_circuit(_RGB_RAINBOW)
    gnd = _net_by_id(circuit, "GND")
    assert _net_members(gnd) == {("U1", "GND"), ("D1", "cathode")}
    assert gnd.provenance == "schematic/common"


def test_rgb_rainbow_plus5v_net_id_and_members_and_provenance():
    """+5V net contains only the VIN pin; must not be merged with any other net."""
    circuit = import_circuit(_RGB_RAINBOW)
    net = _net_by_id(circuit, "+5V")
    assert _net_members(net) == {("U1", "VIN")}
    assert net.provenance == "schematic/power"


def test_rgb_rainbow_roles():
    roles = set(import_circuit(_RGB_RAINBOW).roles)
    assert Role("U1", "mcu", "inferred") in roles
    for ref in ("R1", "R2", "R3"):
        assert Role(ref, "series_resistor", "inferred") in roles
    assert Role("D1", "load", "inferred") in roles
    assert Role("GND", "common_net", "inferred") in roles
    assert Role("+5V", "power_net", "inferred") in roles


def test_rgb_rainbow_exactly_seven_roles():
    """U1 + R1/R2/R3 + D1 + GND + +5V = 7 roles."""
    assert len(import_circuit(_RGB_RAINBOW).roles) == 7


# ---------------------------------------------------------------------------
# Fixture C - rgb-modes (RGB LED, 3 channels, 1 button)
# ---------------------------------------------------------------------------


def test_rgb_modes_title():
    assert import_circuit(_RGB_MODES).title == "ESP32 RGB LED modes"


def test_rgb_modes_mcu_pin_order_includes_button_gpio_last():
    """Button GPIOs appended after channel GPIOs in declaration order."""
    u1 = _component(import_circuit(_RGB_MODES), "U1")
    assert u1.pins == (
        Pin("VIN", "VIN", "power", 0),
        Pin("GND", "GND", "power", 1),
        Pin("GPIO0", "GPIO0", "gpio", 2),
        Pin("GPIO2", "GPIO2", "gpio", 3),
        Pin("GPIO15", "GPIO15", "gpio", 4),
        Pin("GPIO14", "GPIO14", "gpio", 5),
    )


def test_rgb_modes_button_component_kind_and_pins():
    circuit = import_circuit(_RGB_MODES)
    sw1 = _component(circuit, "SW1")
    assert sw1.kind == "button"
    assert sw1.pins == (
        Pin("1", "1", "passive", 0),
        Pin("2", "2", "passive", 1),
    )


def test_rgb_modes_exactly_nine_nets():
    assert len(import_circuit(_RGB_MODES).nets) == 9


def test_rgb_modes_button_net_members_and_provenance():
    """Near leg (pin 1) connects to MCU GPIO; far leg (pin 2) goes to GND net."""
    circuit = import_circuit(_RGB_MODES)
    net = _net_by_members(circuit, {("U1", "GPIO14"), ("SW1", "1")})
    assert net.provenance == "schematic/button"


def test_rgb_modes_gnd_includes_button_far_leg():
    """Button far leg (pin 2) must land in the named GND net - not be omitted."""
    circuit = import_circuit(_RGB_MODES)
    gnd = _net_by_id(circuit, "GND")
    assert ("SW1", "2") in _net_members(gnd)


def test_rgb_modes_gnd_net_full_membership_and_provenance():
    """GND merges MCU power, LED cathode, and button far leg. schematic/common wins."""
    circuit = import_circuit(_RGB_MODES)
    gnd = _net_by_id(circuit, "GND")
    assert _net_members(gnd) == {("U1", "GND"), ("D1", "cathode"), ("SW1", "2")}
    assert gnd.provenance == "schematic/common"


def test_rgb_modes_no_duplicate_gnd_net():
    """Button, MCU power, and LED common all reference GND - only one GND net allowed."""
    circuit = import_circuit(_RGB_MODES)
    assert sum(1 for n in circuit.nets if n.net_id == "GND") == 1


def test_rgb_modes_no_button_role_emitted():
    """Buttons produce no Role entry."""
    circuit = import_circuit(_RGB_MODES)
    assert not any(r.target == "SW1" for r in circuit.roles)


def test_rgb_modes_roles():
    roles = set(import_circuit(_RGB_MODES).roles)
    assert Role("U1", "mcu", "inferred") in roles
    for ref in ("R1", "R2", "R3"):
        assert Role(ref, "series_resistor", "inferred") in roles
    assert Role("D1", "load", "inferred") in roles
    assert Role("GND", "common_net", "inferred") in roles
    assert Role("+5V", "power_net", "inferred") in roles


def test_rgb_modes_exactly_seven_roles():
    """U1 + R1/R2/R3 + D1 + GND + +5V = 7 roles (no SW1 role)."""
    assert len(import_circuit(_RGB_MODES).roles) == 7


def test_rgb_modes_each_pin_appears_in_at_most_one_net():
    """No (instance_id, pin) pair is listed in more than one net."""
    circuit = import_circuit(_RGB_MODES)
    all_refs = [
        (ref.instance_id, ref.pin)
        for net in circuit.nets
        for ref in net.member_pin_refs
    ]
    assert len(all_refs) == len(set(all_refs))


# ---------------------------------------------------------------------------
# Fail-loud: ValueError naming the missing key
# ---------------------------------------------------------------------------


def test_fail_loud_missing_mcu_key():
    with pytest.raises(ValueError, match="mcu"):
        import_circuit(
            {
                "title": "T",
                "load": {"common": {"pin": "K", "net": "GND"}},
                "channels": [
                    {"gpio": "GPIO1", "load_pin": "A", "resistor": {"ref": "R1", "value": "100Ω"}}
                ],
            }
        )


def test_fail_loud_missing_load_key():
    with pytest.raises(ValueError, match="load"):
        import_circuit(
            {
                "title": "T",
                "mcu": {"label": "X", "power": [{"pin": "GND", "net": "GND"}]},
                "channels": [
                    {"gpio": "GPIO1", "load_pin": "A", "resistor": {"ref": "R1", "value": "100Ω"}}
                ],
            }
        )


def test_fail_loud_missing_channels_key():
    with pytest.raises(ValueError, match="channels"):
        import_circuit(
            {
                "title": "T",
                "mcu": {"label": "X", "power": [{"pin": "GND", "net": "GND"}]},
                "load": {"common": {"pin": "K", "net": "GND"}},
            }
        )


def test_fail_loud_load_without_common_key():
    with pytest.raises(ValueError, match="common"):
        import_circuit(
            {
                "title": "T",
                "mcu": {"label": "X", "power": [{"pin": "GND", "net": "GND"}]},
                "load": {"label": "LED"},
                "channels": [
                    {"gpio": "GPIO1", "load_pin": "A", "resistor": {"ref": "R1", "value": "100Ω"}}
                ],
            }
        )


# ---------------------------------------------------------------------------
# Source type acceptance: Path, YAML string, dict
# ---------------------------------------------------------------------------


def test_accepts_path_object_returns_circuit():
    circuit = import_circuit(_HELLO_WORLD)
    assert isinstance(circuit, Circuit)


def test_accepts_yaml_string_and_parses_title():
    yaml_text = _HELLO_WORLD.read_text()
    circuit = import_circuit(yaml_text)
    assert circuit.title == "ESP32 Hello World"


def test_accepts_dict_and_returns_circuit():
    data = {
        "title": "Dict Input Test",
        "mcu": {"label": "MCU", "power": [{"pin": "GND", "net": "GND"}]},
        "load": {"common": {"pin": "K", "net": "GND"}},
        "channels": [
            {"gpio": "GPIO1", "load_pin": "A", "resistor": {"ref": "R1", "value": "100Ω"}}
        ],
    }
    circuit = import_circuit(data)
    assert circuit.title == "Dict Input Test"
