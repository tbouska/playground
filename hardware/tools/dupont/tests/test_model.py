"""Tests for dupont.model.entities and dupont.model.serialize (Phase 0).

Covers acceptance criteria:
1. Every entity dataclass has exactly the pinned fields in declaration order.
2. All entity instances are frozen (FrozenInstanceError on mutation).
3. The hello-world Circuit constructs from the dataclasses without error.
4. Every Net in the hello-world Circuit has a non-empty provenance string.
5. Component.value ("220Ω") survives a serialize round-trip.
6. load_model(dump_model(c)) == c for the full hello-world Circuit.
7. dump_model returns str; load_model accepts both str and Path.
"""

import dataclasses
from pathlib import Path

import pytest

from dupont.model.entities import (
    Circuit,
    Component,
    Net,
    Pin,
    Placement,
    PinRef,
    Role,
)
from dupont.model.serialize import dump_model, load_model

# Expected fields in declaration order for every model entity.
_MODEL_FIELDS = {
    Pin: ("pin_id", "name", "type", "physical_index"),
    Component: ("instance_id", "kind", "pins", "part_type", "variant", "label", "value"),
    PinRef: ("instance_id", "pin"),
    Net: ("net_id", "member_pin_refs", "provenance"),
    Placement: ("component_ref", "coords", "rotation", "source", "provenance"),
    Role: ("target", "tag", "source"),
    Circuit: ("title", "components", "nets", "placements", "roles"),
}

# One instance of each entity — proves construction and gives frozen-ness tests concrete targets.
_PIN = Pin(pin_id="GND", name="GND", type="power", physical_index=0)
_COMPONENT = Component(instance_id="U1", kind="mcu", pins=(_PIN,))
_PIN_REF = PinRef(instance_id="U1", pin="GND")
_NET = Net(net_id="GND", member_pin_refs=(_PIN_REF,), provenance="schematic/common")
_PLACEMENT = Placement(
    component_ref="U1",
    coords={},
    rotation=0.0,
    source="breadboard",
    provenance="breadboard/layout",
)
_ROLE = Role(target="U1", tag="mcu", source="inferred")
_CIRCUIT = Circuit(title="T", components=(_COMPONENT,), nets=(_NET,))

_INSTANCES = [_PIN, _COMPONENT, _PIN_REF, _NET, _PLACEMENT, _ROLE, _CIRCUIT]


@pytest.fixture
def hello_world_circuit() -> Circuit:
    return Circuit(
        title="Hello World",
        components=(
            Component(
                instance_id="U1",
                kind="mcu",
                pins=(
                    Pin("GND", "GND", "power", 0),
                    Pin("GPIO2", "GPIO2", "gpio", 1),
                ),
                label="ESP32-WROOM-32 DevKit",
            ),
            Component(
                instance_id="R1",
                kind="resistor",
                pins=(
                    Pin("1", "1", "passive", 0),
                    Pin("2", "2", "passive", 1),
                ),
                value="220Ω",
            ),
            Component(
                instance_id="D1",
                kind="led",
                pins=(
                    Pin("anode", "anode", "passive", 0),
                    Pin("cathode", "cathode", "passive", 1),
                ),
            ),
        ),
        nets=(
            Net("n_gpio2", (PinRef("U1", "GPIO2"), PinRef("R1", "1")), "schematic/channel"),
            Net("n_r1_out", (PinRef("R1", "2"), PinRef("D1", "anode")), "schematic/channel"),
            Net("GND", (PinRef("U1", "GND"), PinRef("D1", "cathode")), "schematic/common"),
        ),
        roles=(
            Role("U1", "mcu", "inferred"),
            Role("R1", "series_resistor", "inferred"),
            Role("D1", "load", "inferred"),
            Role("GND", "common_net", "inferred"),
        ),
    )


@pytest.mark.parametrize(
    "cls, expected_fields",
    list(_MODEL_FIELDS.items()),
    ids=lambda value: value.__name__ if isinstance(value, type) else "",
)
def test_entity_classes_are_dataclasses_with_expected_fields(
    cls: type, expected_fields: tuple[str, ...]
) -> None:
    assert dataclasses.is_dataclass(cls)
    assert tuple(f.name for f in dataclasses.fields(cls)) == expected_fields


@pytest.mark.parametrize(
    "instance", _INSTANCES, ids=lambda inst: type(inst).__name__
)
def test_entity_instances_are_frozen(instance: object) -> None:
    field_name = dataclasses.fields(instance)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, field_name, "mutated")


def test_hello_world_circuit_constructs(hello_world_circuit: Circuit) -> None:
    assert hello_world_circuit.title == "Hello World"
    assert len(hello_world_circuit.components) == 3
    assert len(hello_world_circuit.nets) == 3
    assert hello_world_circuit.placements == ()
    # Spot-check a pin to confirm nested construction landed correctly.
    mcu = hello_world_circuit.components[0]
    assert mcu.instance_id == "U1"
    assert mcu.pins[1].pin_id == "GPIO2"


def test_every_net_has_non_empty_provenance(hello_world_circuit: Circuit) -> None:
    for net in hello_world_circuit.nets:
        assert isinstance(net.provenance, str) and net.provenance, (
            f"Net {net.net_id!r} has empty or missing provenance"
        )


def test_component_value_survives_round_trip(hello_world_circuit: Circuit) -> None:
    reloaded = load_model(dump_model(hello_world_circuit))
    resistor = next(c for c in reloaded.components if c.instance_id == "R1")
    assert resistor.value == "220Ω"


def test_round_trips_hello_world_circuit(hello_world_circuit: Circuit) -> None:
    assert load_model(dump_model(hello_world_circuit)) == hello_world_circuit


def test_dump_model_returns_str(hello_world_circuit: Circuit) -> None:
    result = dump_model(hello_world_circuit)
    assert isinstance(result, str) and result


def test_load_model_accepts_path(hello_world_circuit: Circuit, tmp_path: Path) -> None:
    yaml_path = tmp_path / "circuit.yaml"
    yaml_path.write_text(dump_model(hello_world_circuit), encoding="utf-8")
    assert load_model(yaml_path) == hello_world_circuit
