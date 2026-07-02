"""Tests for dupont.formats.breadboard import/export (layout.yaml <-> Circuit).

Verifies the breadboard-side round-trip: import_layout canonicalizes a
breadboard.model.Layout into the interchange Circuit (component ids and pin
names matching what the schematic side's import_circuit produces for the same
physical circuit), and collapse_to_layout rebuilds the Layout from
Circuit.placements. All tests are black-box: they assert the published
contract, not any implementation detail.
"""

from pathlib import Path

import pytest
import yaml

from breadboard.parse import load_layout
from dupont.formats.breadboard.exporter import collapse_to_layout
from dupont.formats.breadboard.importer import import_layout
from dupont.model.entities import Circuit, Component, Net, Pin, Placement

# ---------------------------------------------------------------------------
# Fixture path (relative to the hardware/ root, three levels above this file)
# ---------------------------------------------------------------------------

_HW = Path(__file__).resolve().parents[3]
_HELLO_WORLD = _HW / "arduino-ide-sketchbook/espx/espx-1-1-2-hello-world/layout.yaml"

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


def _net_by_members(circuit: Circuit, expected: set[tuple[str, str]]) -> Net:
    for n in circuit.nets:
        if _net_members(n) == expected:
            return n
    raise KeyError(f"No net with members {expected}")


# ---------------------------------------------------------------------------
# Fixture — espx-1-1-2-hello-world breadboard layout
# ---------------------------------------------------------------------------


def test_hello_world_title():
    assert import_layout(_HELLO_WORLD).title == "ESP32 Hello World breadboard"


def test_hello_world_canonical_component_ids_kinds_and_resistor_value():
    circuit = import_layout(_HELLO_WORLD)
    assert {c.instance_id for c in circuit.components} == {"U1", "R1", "D1"}
    assert _component(circuit, "U1").kind == "mcu"
    assert _component(circuit, "R1").kind == "resistor"
    assert _component(circuit, "R1").value == "220"
    assert _component(circuit, "D1").kind == "led"


def test_hello_world_three_two_member_nets_by_gpio_resistor_led_chain():
    """The GPIO->resistor->LED->GND chain must canonicalize to exactly these
    three 2-member nets, with the resistor's MCU-adjacent leg named '1' and the
    LED's positional legs named anode/cathode."""
    circuit = import_layout(_HELLO_WORLD)
    expected_two_member_nets = [
        {("U1", "GPIO2"), ("R1", "1")},
        {("R1", "2"), ("D1", "anode")},
        {("U1", "GND"), ("D1", "cathode")},
    ]
    for members in expected_two_member_nets:
        _net_by_members(circuit, members)  # raises KeyError if absent


def test_hello_world_vin_singleton_net_exists():
    circuit = import_layout(_HELLO_WORLD)
    _net_by_members(circuit, {("U1", "VIN")})


def test_hello_world_roles_is_empty():
    assert import_layout(_HELLO_WORLD).roles == ()


def test_hello_world_board_placement_records_columns_and_style():
    circuit = import_layout(_HELLO_WORLD)
    board_placements = [p for p in circuit.placements if p.component_ref == "__board__"]
    assert len(board_placements) == 1
    board = board_placements[0]
    assert board.coords == {"columns": 50, "style": None}
    assert board.provenance == "breadboard/board"


def test_hello_world_placement_order_matches_layout_kind_order():
    """Exactly one non-board placement per drawable component (7 here), in
    layout declaration order, each tagged source='breadboard'."""
    circuit = import_layout(_HELLO_WORLD)
    non_board = [p for p in circuit.placements if p.component_ref != "__board__"]
    assert [p.coords["kind"] for p in non_board] == [
        "module",
        "wire",
        "resistor",
        "led",
        "wire",
        "wire",
        "wire",
    ]
    assert all(p.source == "breadboard" for p in non_board)


def test_hello_world_placement_coords_are_json_native_full_fields():
    """coords must be a plain-JSON serialization of the breadboard Component:
    lists (not tuples) for legs/endpoints/span/pins, plain dicts (not Pin
    objects) for each pin entry."""
    circuit = import_layout(_HELLO_WORLD)
    non_board = [p for p in circuit.placements if p.component_ref != "__board__"]
    module_coords = next(p.coords for p in non_board if p.coords["kind"] == "module")
    assert module_coords == {
        "kind": "module",
        "ref": "U1",
        "label": "ESP32-WROOM-32 DevKit",
        "value": "",
        "legs": [],
        "named_legs": {},
        "common": "cathode",
        "color": "black",
        "endpoints": ["", ""],
        "span": [1, 19],
        "pins": [
            {"name": "VIN", "hole": "B1"},
            {"name": "GND", "hole": "I19"},
            {"name": "GPIO2", "hole": "I5"},
        ],
        "digits": 1,
    }
    resistor_coords = next(p.coords for p in non_board if p.coords["kind"] == "resistor")
    assert resistor_coords["ref"] == "R1"
    assert resistor_coords["value"] == "220"
    assert resistor_coords["legs"] == ["G25", "G29"]


def test_hello_world_round_trip_equals_direct_parse():
    """The key invariant: collapse_to_layout(import_layout(p)) == load_layout(p)."""
    circuit = import_layout(_HELLO_WORLD)
    assert collapse_to_layout(circuit) == load_layout(_HELLO_WORLD)


# ---------------------------------------------------------------------------
# Source type acceptance: Path, YAML string, dict
# ---------------------------------------------------------------------------


def test_import_layout_accepts_path_and_returns_circuit():
    assert isinstance(import_layout(_HELLO_WORLD), Circuit)


def test_import_layout_accepts_yaml_string_and_parses_title():
    yaml_text = _HELLO_WORLD.read_text()
    assert import_layout(yaml_text).title == "ESP32 Hello World breadboard"


def test_import_layout_accepts_dict_and_returns_circuit():
    data = yaml.safe_load(_HELLO_WORLD.read_text())
    circuit = import_layout(data)
    assert isinstance(circuit, Circuit)
    assert circuit.title == "ESP32 Hello World breadboard"


# ---------------------------------------------------------------------------
# Fail-loud: unmapped component kind
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["capacitor", "diode", "banana"])
def test_import_layout_unmapped_kind_raises_value_error_naming_kind(kind):
    layout = {
        "title": "t",
        "breadboard": {"columns": 10},
        "components": [{"kind": kind, "ref": "C1", "legs": ["A1", "A2"]}],
    }
    with pytest.raises(ValueError, match=kind):
        import_layout(layout)


def test_import_layout_no_module_raises_value_error():
    """A layout with no MCU 'module' cannot be canonicalized - fail loud."""
    layout = {
        "title": "t",
        "breadboard": {"columns": 30},
        "components": [{"kind": "resistor", "ref": "R1", "legs": ["G10", "G14"]}],
    }
    with pytest.raises(ValueError, match="module"):
        import_layout(layout)


def test_import_layout_multiple_modules_raises_value_error():
    """Multi-module layouts are out of v1 scope - fail loud, not a cryptic KeyError."""
    layout = {
        "title": "t",
        "breadboard": {"columns": 30},
        "components": [
            {"kind": "module", "ref": "U1", "pins": [{"name": "GPIO2", "hole": "I5"}]},
            {"kind": "module", "ref": "U2", "pins": [{"name": "GPIO4", "hole": "I8"}]},
        ],
    }
    with pytest.raises(ValueError, match="module"):
        import_layout(layout)


# ---------------------------------------------------------------------------
# MCU-adjacency canonicalization is order-invariant
# ---------------------------------------------------------------------------


def test_resistor_pin_canon_is_order_invariant_by_mcu_adjacency():
    """Resistor legs authored with the GPIO-adjacent leg SECOND still
    canonicalize that leg to pin '1' - orientation is decided by which leg's
    net touches the MCU, not by YAML leg order."""
    layout = {
        "title": "t",
        "breadboard": {"columns": 30},
        "components": [
            {"kind": "module", "ref": "U1", "pins": [{"name": "GPIO2", "hole": "I5"}]},
            {"kind": "wire", "color": "green", "from": "I5", "to": "G20"},
            {"kind": "resistor", "ref": "R1", "value": "220", "legs": ["G10", "G20"]},
            {"kind": "led", "ref": "D1", "legs": ["F30", "F31"]},
        ],
    }
    circuit = import_layout(layout)
    _net_by_members(circuit, {("U1", "GPIO2"), ("R1", "1")})


# ---------------------------------------------------------------------------
# led-rgb: dict-form legs -> kind 'led-rgb'; K normalizes, R/G/B kept as-is
# ---------------------------------------------------------------------------


def test_led_rgb_dict_legs_kind_and_pin_normalization():
    layout = {
        "title": "t",
        "breadboard": {"columns": 30},
        "components": [
            {"kind": "module", "ref": "U1", "pins": [{"name": "GPIO2", "hole": "I5"}]},
            {
                "kind": "led-rgb",
                "ref": "D1",
                "legs": {"R": "A1", "G": "A2", "B": "A3", "K": "A4"},
            },
        ],
    }
    circuit = import_layout(layout)
    assert _component(circuit, "D1").kind == "led-rgb"
    _net_by_members(circuit, {("D1", "R")})
    _net_by_members(circuit, {("D1", "G")})
    _net_by_members(circuit, {("D1", "B")})
    _net_by_members(circuit, {("D1", "cathode")})


# ---------------------------------------------------------------------------
# collapse_to_layout: fail loud when board metadata is missing
# ---------------------------------------------------------------------------


def test_collapse_to_layout_raises_value_error_when_board_placement_missing():
    circuit = Circuit(
        title="t",
        components=(
            Component(
                instance_id="U1",
                kind="mcu",
                pins=(Pin("VIN", "VIN", "power", 0),),
            ),
        ),
        nets=(),
        placements=(
            Placement(
                component_ref="U1",
                coords={"kind": "module"},
                rotation=0.0,
                source="breadboard",
                provenance="breadboard/component",
            ),
        ),
    )
    with pytest.raises(ValueError):
        collapse_to_layout(circuit)
