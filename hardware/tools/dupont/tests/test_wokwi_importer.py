"""Tests for dupont.formats.wokwi.importer.import_wokwi.

Written from the spec BEFORE the implementation exists (TDD red state):
`dev/local/designs/00009-format-interop-wokwi-geometry-v1-design.md`
(section `dupont/formats/wokwi/importer.py`) and
`dev/local/prds/wip/00009-format-interop-wokwi-geometry-v1.md`.

All tests are black-box: they assert on the returned Circuit (nets, components,
placements), never on internals.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dupont.formats.wokwi.importer import import_wokwi
from dupont.model.entities import Circuit, Net, Placement

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


def _net_members(net: Net) -> frozenset[tuple[str, str]]:
    return frozenset((r.instance_id, r.pin) for r in net.member_pin_refs)


def _multi_member_nets(circuit: Circuit) -> list[Net]:
    return [n for n in circuit.nets if len(n.member_pin_refs) >= 2]


def _net_by_members(circuit: Circuit, expected: frozenset[tuple[str, str]]) -> Net:
    for n in circuit.nets:
        if _net_members(n) == expected:
            return n
    raise KeyError(f"No net with members {expected}")


def _placement(circuit: Circuit, component_ref: str) -> Placement:
    for p in circuit.placements:
        if p.component_ref == component_ref:
            return p
    raise KeyError(f"No placement with component_ref {component_ref!r}")


def _board_part(part_id: str = "esp", top: float = 0.0, left: float = 0.0) -> dict:
    return {
        "type": "board-esp32-devkit-c-v4",
        "id": part_id,
        "top": top,
        "left": left,
        "attrs": {},
    }


def _resistor_part(part_id: str, top: float, left: float) -> dict:
    return {
        "type": "wokwi-resistor",
        "id": part_id,
        "top": top,
        "left": left,
        "attrs": {"value": "220"},
    }


def _diagram(parts: list[dict], connections: list[list]) -> dict:
    return {
        "version": 1,
        "author": "test",
        "editor": "wokwi",
        "parts": parts,
        "connections": connections,
        "dependencies": {},
    }


def _wire(a: str, b: str) -> list:
    return [a, b, "", []]


# ---------------------------------------------------------------------------
# Patterns 11-14: transitive closure over the flat connections list
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "resistor_ids, wires, expected_members",
    [
        pytest.param(
            ["ra", "rb", "rc"],
            [("ra:1", "rb:1"), ("rb:1", "rc:1")],
            frozenset({("R1", "1"), ("R2", "1"), ("R3", "1")}),
            id="pattern11-chained-a-b-b-c-shares-b",
        ),
        pytest.param(
            ["rh", "ra", "rb", "rc"],
            [("rh:1", "ra:1"), ("rh:1", "rb:1"), ("rh:1", "rc:1")],
            frozenset({("R1", "1"), ("R2", "1"), ("R3", "1"), ("R4", "1")}),
            id="pattern12-fan-out-hub",
        ),
        pytest.param(
            ["pa", "pb", "pc", "pd"],
            [("pa:1", "pb:1"), ("pb:1", "pc:1"), ("pc:1", "pd:1")],
            frozenset({("R1", "1"), ("R2", "1"), ("R3", "1"), ("R4", "1")}),
            id="pattern13-chained-across-four-parts",
        ),
        pytest.param(
            ["pa", "pb"],
            [("pa:1", "pb:1"), ("pa:1", "pb:1")],
            frozenset({("R1", "1"), ("R2", "1")}),
            id="pattern14-duplicate-connection-counted-once",
        ),
    ],
)
def test_transitive_closure_patterns(
    resistor_ids: list[str],
    wires: list[tuple[str, str]],
    expected_members: frozenset[tuple[str, str]],
) -> None:
    parts = [_board_part()] + [
        _resistor_part(rid, top=10.0 * i, left=10.0 * i)
        for i, rid in enumerate(resistor_ids, start=1)
    ]
    connections = [_wire(a, b) for a, b in wires]
    circuit = import_wokwi(_diagram(parts, connections))

    nets = _multi_member_nets(circuit)
    assert len(nets) == 1
    net = nets[0]
    assert _net_members(net) == expected_members
    # A duplicate/parallel wire must not double an entry in member_pin_refs.
    assert len(net.member_pin_refs) == len(expected_members)


def test_closure_net_provenance_is_wokwi_closure() -> None:
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    assert circuit.nets
    assert all(n.provenance == "wokwi/closure" for n in circuit.nets)


# ---------------------------------------------------------------------------
# Canonical ids + pin-name convergence (real helloworld-idf fixture)
# ---------------------------------------------------------------------------


def test_hello_world_canonical_ids() -> None:
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    ids = {c.instance_id for c in circuit.components}
    assert ids == {"U1", "D1", "R1"}


def test_board_bare_digit_pin_converges_to_canonical_gpio() -> None:
    """esp:2 -> (U1, "GPIO2") via board_pin_to_canon's bare-digit rule."""
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    _net_by_members(circuit, frozenset({("R1", "2"), ("U1", "GPIO2")}))


def test_board_ground_suffix_pin_collapses_to_canonical_gnd() -> None:
    """esp:GND.3 -> (U1, "GND") via board_pin_to_canon's ground-bus rule."""
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    _net_by_members(circuit, frozenset({("D1", "cathode"), ("U1", "GND")}))


def test_led_anode_pin_normalizes_from_bare_a() -> None:
    """led1:A -> (D1, "anode")."""
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    _net_by_members(circuit, frozenset({("D1", "anode"), ("R1", "1")}))


def test_led_cathode_pin_normalizes_from_bare_c() -> None:
    """led1:C -> (D1, "cathode")."""
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    _net_by_members(circuit, frozenset({("D1", "cathode"), ("U1", "GND")}))


# ---------------------------------------------------------------------------
# Virtual $ endpoints dropped
# ---------------------------------------------------------------------------


def test_virtual_serial_monitor_endpoints_dropped() -> None:
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    assert not any(c.instance_id.startswith("$") for c in circuit.components)

    # esp:TX / esp:RX are wired only to $serialMonitor; the dropped virtual
    # endpoint must leave them out of every net entirely.
    all_members = {m for n in circuit.nets for m in _net_members(n)}
    assert ("U1", "GPIO1") not in all_members  # TX
    assert ("U1", "GPIO3") not in all_members  # RX


# ---------------------------------------------------------------------------
# Re-origin to the reference frame (board-relative, no non-negativity)
# ---------------------------------------------------------------------------


def test_board_reference_lands_at_origin() -> None:
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    placement = _placement(circuit, "U1")
    assert placement.coords["px"] == (0.0, 0.0)
    assert placement.source == "wokwi"


def test_part_above_board_reorigins_to_negative_y() -> None:
    """led1 (top -3.33) sits above the devkit (top 38.4): board-relative y is
    negative (~-41.73). Non-negativity is explicitly NOT part of the contract."""
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    placement = _placement(circuit, "D1")
    x, y = placement.coords["px"]
    assert x == pytest.approx(153.33 - 4.84)
    assert y == pytest.approx(-3.33 - 38.4)
    assert placement.source == "wokwi"


def test_devkit_anchored_diagram_has_no_breadboard_sentinel() -> None:
    circuit = import_wokwi(_WOKWI_HELLO_WORLD)
    assert not any(p.component_ref == "__wokwi_breadboard__" for p in circuit.placements)


def test_breadboard_carrying_diagram_gets_sentinel_placement() -> None:
    diagram = _diagram(
        parts=[
            {"type": "wokwi-breadboard", "id": "bb1", "top": 0.0, "left": 0.0, "attrs": {}},
            _resistor_part("r1", top=10.0, left=10.0),
        ],
        connections=[],
    )
    circuit = import_wokwi(diagram)
    sentinel = _placement(circuit, "__wokwi_breadboard__")
    assert sentinel.coords == {"px": (0.0, 0.0)}
    assert sentinel.rotation == 0.0
    assert sentinel.source == "wokwi"
    assert sentinel.provenance == "wokwi/breadboard-origin"


# ---------------------------------------------------------------------------
# Fail-loud: unmapped part_type, ambiguous/absent re-origin reference
# ---------------------------------------------------------------------------


def test_unmapped_part_type_raises_value_error() -> None:
    diagram = _diagram(
        parts=[
            _board_part(),
            {
                "type": "wokwi-mystery-widget",
                "id": "x1",
                "top": 5.0,
                "left": 5.0,
                "attrs": {},
            },
        ],
        connections=[],
    )
    with pytest.raises(ValueError):
        import_wokwi(diagram)


def test_ambiguous_reference_raises_value_error_with_two_boards_and_no_breadboard() -> None:
    diagram = _diagram(
        parts=[_board_part("esp1"), _board_part("esp2", top=50.0, left=50.0)],
        connections=[],
    )
    with pytest.raises(ValueError):
        import_wokwi(diagram)


def test_absent_reference_raises_value_error_with_no_board_or_breadboard() -> None:
    diagram = _diagram(parts=[_resistor_part("r1", top=0.0, left=0.0)], connections=[])
    with pytest.raises(ValueError):
        import_wokwi(diagram)


# ---------------------------------------------------------------------------
# Source polymorphism: dict and Path both accepted, produce equal nets
# ---------------------------------------------------------------------------


def test_dict_and_path_sources_produce_equal_nets() -> None:
    from_path = import_wokwi(_WOKWI_HELLO_WORLD)
    data = json.loads(_WOKWI_HELLO_WORLD.read_text())
    from_dict = import_wokwi(data)

    path_nets = {_net_members(n) for n in from_path.nets}
    dict_nets = {_net_members(n) for n in from_dict.nets}
    assert path_nets == dict_nets
