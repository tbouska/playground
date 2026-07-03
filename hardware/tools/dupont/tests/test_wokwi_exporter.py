"""Tests for dupont.formats.wokwi.exporter.export_wokwi.

Written from the spec BEFORE the implementation exists (TDD red state):
`dev/local/designs/00009-format-interop-wokwi-geometry-v1-design.md`
(section `dupont/formats/wokwi/exporter.py`) and
`dev/local/prds/wip/00009-format-interop-wokwi-geometry-v1.md`.

All tests are black-box: they assert on the returned diagram.json dict and on
raised errors, never on internals.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dupont.formats.wokwi.exporter import export_wokwi
from dupont.formats.wokwi.importer import import_wokwi
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef, Placement

# ---------------------------------------------------------------------------
# Fixture path (relative to the hardware/ root, three levels above this file)
# ---------------------------------------------------------------------------

_HW = Path(__file__).resolve().parents[3]
_WOKWI_HELLO_WORLD = (
    _HW
    / "esp32"
    / "martin-maly-esp32-prakticky"
    / "ostatni"
    / "helloworld-idf"
    / "diagram.json"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _component(
    instance_id: str, kind: str, pin_names: list[str], value: str | None = None
) -> Component:
    pins = tuple(Pin(n, n, "passive", i) for i, n in enumerate(pin_names))
    return Component(instance_id, kind, pins, value=value)


def _net(net_id: str, members: list[tuple[str, str]]) -> Net:
    return Net(net_id, tuple(PinRef(i, p) for i, p in members), "test")


def _net_members(net: Net) -> frozenset[tuple[str, str]]:
    return frozenset((r.instance_id, r.pin) for r in net.member_pin_refs)


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


def test_returns_diagram_shape() -> None:
    circuit = Circuit(
        title="t", components=(_component("U1", "mcu", ["GPIO2", "GND"]),), nets=()
    )
    result = export_wokwi(circuit)
    assert result["version"] == 1
    assert result["dependencies"] == {}
    assert isinstance(result["parts"], list)
    assert isinstance(result["connections"], list)


# ---------------------------------------------------------------------------
# Part mapping: one per component, type + id, in circuit.components order
# ---------------------------------------------------------------------------


def test_one_part_per_component_with_mapped_type_and_lowercased_id() -> None:
    components = (
        _component("U1", "mcu", ["GPIO2", "GND"]),
        _component("D1", "led", ["anode", "cathode"]),
        _component("R1", "resistor", ["1", "2"], value="220"),
    )
    circuit = Circuit(title="t", components=components, nets=())
    result = export_wokwi(circuit)

    assert len(result["parts"]) == 3
    assert [p["id"] for p in result["parts"]] == ["u1", "d1", "r1"]
    assert [p["type"] for p in result["parts"]] == [
        "board-esp32-devkit-c-v4",
        "wokwi-led",
        "wokwi-resistor",
    ]


def test_unmapped_kind_raises_value_error() -> None:
    circuit = Circuit(
        title="t", components=(_component("X1", "buzzer", ["p1", "p2"]),), nets=()
    )
    with pytest.raises(ValueError):
        export_wokwi(circuit)


def test_resistor_attrs_carries_value() -> None:
    circuit = Circuit(
        title="t",
        components=(_component("R1", "resistor", ["1", "2"], value="4700"),),
        nets=(),
    )
    result = export_wokwi(circuit)
    assert result["parts"][0]["attrs"]["value"] == "4700"


# ---------------------------------------------------------------------------
# Placement -> top/left
# ---------------------------------------------------------------------------


def test_part_position_taken_from_placement_px() -> None:
    component = _component("R1", "resistor", ["1", "2"])
    placement = Placement("R1", {"px": (12.5, 34.5)}, 0.0, "test", "test")
    circuit = Circuit(
        title="t", components=(component,), nets=(), placements=(placement,)
    )
    part = export_wokwi(circuit)["parts"][0]
    assert part["left"] == 12.5
    assert part["top"] == 34.5


def test_part_without_placement_defaults_to_origin() -> None:
    circuit = Circuit(
        title="t", components=(_component("R1", "resistor", ["1", "2"]),), nets=()
    )
    part = export_wokwi(circuit)["parts"][0]
    assert part["left"] == 0.0
    assert part["top"] == 0.0


def test_part_position_from_hole_coords_uses_measured_scale() -> None:
    """A layout placement carrying grid/hole coords (no px) exports top/left via
    grid.geometry.to_px of its anchor hole, not the (0,0) default — PRD/design
    'map grid coords -> px via the measured scale'."""
    from dupont.grid.geometry import to_px

    component = _component("R1", "resistor", ["1", "2"])
    placement = Placement("R1", {"pins": [{"hole": "F12"}]}, 0.0, "breadboard", "test")
    circuit = Circuit(
        title="t", components=(component,), nets=(), placements=(placement,)
    )
    part = export_wokwi(circuit)["parts"][0]
    expected_x, expected_y = to_px("F12")
    assert (part["left"], part["top"]) == (expected_x, expected_y)
    assert (part["left"], part["top"]) != (0.0, 0.0)


# ---------------------------------------------------------------------------
# Connections: endpoint format, denormalized pins, spanning edges
# ---------------------------------------------------------------------------


def test_two_member_net_emits_one_edge_with_expected_endpoints() -> None:
    """{(U1,'GPIO2'),(R1,'2')} -> edge endpoints {'u1:2','r1:2'}."""
    u1 = _component("U1", "mcu", ["GPIO2", "GND"])
    r1 = _component("R1", "resistor", ["1", "2"])
    net = _net("n1", [("U1", "GPIO2"), ("R1", "2")])
    circuit = Circuit(title="t", components=(u1, r1), nets=(net,))

    connections = export_wokwi(circuit)["connections"]
    assert len(connections) == 1
    edge = connections[0]
    assert set(edge[:2]) == {"u1:2", "r1:2"}
    assert edge[2] == ""
    assert edge[3] == []


def test_led_cathode_and_mcu_ground_denormalize_to_wokwi_pins() -> None:
    """{(D1,'cathode'),(U1,'GND')} -> edge endpoints {'d1:C','u1:GND.0'}."""
    d1 = _component("D1", "led", ["anode", "cathode"])
    u1 = _component("U1", "mcu", ["GPIO2", "GND"])
    net = _net("n1", [("D1", "cathode"), ("U1", "GND")])
    circuit = Circuit(title="t", components=(d1, u1), nets=(net,))

    edge = export_wokwi(circuit)["connections"][0]
    assert set(edge[:2]) == {"d1:C", "u1:GND.0"}


def test_three_member_net_emits_spanning_set_connecting_all_members() -> None:
    """A net of 3 members emits exactly N-1=2 edges that connect all 3."""
    u1 = _component("U1", "mcu", ["GPIO2"])
    r1 = _component("R1", "resistor", ["1", "2"])
    r2 = _component("R2", "resistor", ["1", "2"])
    net = _net("n1", [("U1", "GPIO2"), ("R1", "2"), ("R2", "2")])
    circuit = Circuit(title="t", components=(u1, r1, r2), nets=(net,))

    connections = export_wokwi(circuit)["connections"]
    assert len(connections) == 2

    expected_endpoints = {"u1:2", "r1:2", "r2:2"}
    parent: dict[str, str] = {}

    def find(key: str) -> str:
        parent.setdefault(key, key)
        while parent[key] != key:
            key = parent[key]
        return key

    seen: set[str] = set()
    for a, b, _label, _extra in connections:
        seen.add(a)
        seen.add(b)
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    assert seen == expected_endpoints
    assert len({find(e) for e in expected_endpoints}) == 1


# ---------------------------------------------------------------------------
# Pin-set validation (fail loud)
# ---------------------------------------------------------------------------


def test_illegal_led_pin_raises_value_error() -> None:
    """canon_pin_to_wokwi('led', 'sideways') passes through as 'sideways',
    which is not in legal_pins('wokwi-led') == ('A', 'C')."""
    u1 = _component("U1", "mcu", ["GPIO2"])
    d1 = _component("D1", "led", ["sideways"])
    net = _net("n1", [("D1", "sideways"), ("U1", "GPIO2")])
    circuit = Circuit(title="t", components=(u1, d1), nets=(net,))

    with pytest.raises(ValueError):
        export_wokwi(circuit)


def test_board_pins_are_not_pin_set_validated() -> None:
    """board-esp32-devkit-c-v4 is not a key in PART_TYPE_PINS, so an unusual
    GPIO channel must not raise even though it is not a wokwi-led/-resistor/
    -pushbutton legal pin."""
    u1 = _component("U1", "mcu", ["GPIO99"])
    r1 = _component("R1", "resistor", ["1"])
    net = _net("n1", [("U1", "GPIO99"), ("R1", "1")])
    circuit = Circuit(title="t", components=(u1, r1), nets=(net,))

    connections = export_wokwi(circuit)["connections"]
    assert set(connections[0][:2]) == {"u1:99", "r1:1"}


def test_mcu_gpio_exception_pin_exports_board_label() -> None:
    """A net using an mcu alt-name GPIO (GPIO1) emits its board label 'TX', not
    the bare digit '1' — canon_pin_to_wokwi is the inverse of board_pin_to_canon."""
    u1 = _component("U1", "mcu", ["GPIO1"])
    r1 = _component("R1", "resistor", ["1"])
    net = _net("n1", [("U1", "GPIO1"), ("R1", "1")])
    circuit = Circuit(title="t", components=(u1, r1), nets=(net,))

    edge = export_wokwi(circuit)["connections"][0]
    assert set(edge[:2]) == {"u1:TX", "r1:1"}


# ---------------------------------------------------------------------------
# Round-trip through the real helloworld-idf fixture
# ---------------------------------------------------------------------------


def test_round_trip_preserves_nets() -> None:
    original = import_wokwi(_WOKWI_HELLO_WORLD)
    reimported = import_wokwi(export_wokwi(original))

    original_nets = {_net_members(n) for n in original.nets}
    reimported_nets = {_net_members(n) for n in reimported.nets}
    assert reimported_nets == original_nets
