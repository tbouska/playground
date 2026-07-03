from __future__ import annotations

from dupont.formats.wokwi.maps import (
    KIND_TO_PART_TYPE,
    PART_TYPE_PINS,
    canon_pin_to_wokwi,
    legal_pins,
)
from dupont.grid.geometry import to_px
from dupont.model.entities import Circuit, PinRef, Placement


def _placement_position(placement: Placement | None) -> tuple[float, float]:
    """Top/left px for a component placement.

    Use px coords directly; otherwise map the anchor hole (first pin) through the
    measured scale via grid.geometry.to_px; otherwise default to the origin.
    """
    if placement is None:
        return (0.0, 0.0)
    coords = placement.coords
    if "px" in coords:
        return (float(coords["px"][0]), float(coords["px"][1]))
    pins = coords.get("pins", [])
    if pins and "hole" in pins[0]:
        return to_px(pins[0]["hole"])
    return (0.0, 0.0)


def _build_parts(circuit: Circuit) -> list[dict]:
    placement_map = {p.component_ref: p for p in circuit.placements}
    parts = []
    for comp in circuit.components:
        if comp.kind not in KIND_TO_PART_TYPE:
            raise ValueError(f"unmapped kind: {comp.kind!r}")
        left, top = _placement_position(placement_map.get(comp.instance_id))
        attrs = {"value": comp.value} if comp.kind == "resistor" else {}
        parts.append({
            "type": KIND_TO_PART_TYPE[comp.kind],
            "id": comp.instance_id.lower(),
            "top": top,
            "left": left,
            "attrs": attrs,
        })
    return parts


def _endpoint(kind_of: dict[str, str], ref: PinRef) -> str:
    """Build the validated ``id:wokwipin`` endpoint string for a pin ref.

    Fails loud if the denormalized pin is not legal for its part_type.
    """
    kind = kind_of[ref.instance_id]
    part_type = KIND_TO_PART_TYPE[kind]
    wokwi_pin = canon_pin_to_wokwi(kind, ref.pin)
    if part_type in PART_TYPE_PINS and wokwi_pin not in legal_pins(part_type):
        raise ValueError(
            f"pin {ref.pin!r} of {ref.instance_id!r} "
            f"maps to wokwi pin {wokwi_pin!r}, not in {legal_pins(part_type)}"
        )
    return f"{ref.instance_id.lower()}:{wokwi_pin}"


def _build_connections(circuit: Circuit) -> list[list]:
    kind_of = {c.instance_id: c.kind for c in circuit.components}
    connections = []
    for net in circuit.nets:
        members = net.member_pin_refs
        for i in range(len(members) - 1):
            connections.append([
                _endpoint(kind_of, members[i]),
                _endpoint(kind_of, members[i + 1]),
                "",
                [],
            ])
    return connections


def export_wokwi(circuit: Circuit) -> dict:
    return {
        "version": 1,
        "parts": _build_parts(circuit),
        "connections": _build_connections(circuit),
        "dependencies": {},
    }
