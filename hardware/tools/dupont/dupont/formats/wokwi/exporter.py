from __future__ import annotations

from dupont.formats.wokwi.maps import (
    KIND_TO_PART_TYPE,
    PART_TYPE_PINS,
    canon_pin_to_wokwi,
    legal_pins,
)
from dupont.model.entities import Circuit


def export_wokwi(circuit: Circuit) -> dict:
    kind_of = {c.instance_id: c.kind for c in circuit.components}
    placement_map = {p.component_ref: p for p in circuit.placements}

    parts = []
    for comp in circuit.components:
        if comp.kind not in KIND_TO_PART_TYPE:
            raise ValueError(f"unmapped kind: {comp.kind!r}")
        part_type = KIND_TO_PART_TYPE[comp.kind]

        placement = placement_map.get(comp.instance_id)
        if placement and "px" in placement.coords:
            left = float(placement.coords["px"][0])
            top = float(placement.coords["px"][1])
        else:
            left = 0.0
            top = 0.0

        attrs = {"value": comp.value} if comp.kind == "resistor" else {}
        parts.append({
            "type": part_type,
            "id": comp.instance_id.lower(),
            "top": top,
            "left": left,
            "attrs": attrs,
        })

    connections = []
    for net in circuit.nets:
        members = net.member_pin_refs
        for i in range(len(members) - 1):
            a_ref = members[i]
            b_ref = members[i + 1]

            a_part_type = KIND_TO_PART_TYPE[kind_of[a_ref.instance_id]]
            b_part_type = KIND_TO_PART_TYPE[kind_of[b_ref.instance_id]]

            a_wokwi = canon_pin_to_wokwi(kind_of[a_ref.instance_id], a_ref.pin)
            b_wokwi = canon_pin_to_wokwi(kind_of[b_ref.instance_id], b_ref.pin)

            if a_part_type in PART_TYPE_PINS:
                if a_wokwi not in legal_pins(a_part_type):
                    raise ValueError(
                        f"pin {a_ref.pin!r} of {a_ref.instance_id!r} "
                        f"maps to wokwi pin {a_wokwi!r}, not in {legal_pins(a_part_type)}"
                    )
            if b_part_type in PART_TYPE_PINS:
                if b_wokwi not in legal_pins(b_part_type):
                    raise ValueError(
                        f"pin {b_ref.pin!r} of {b_ref.instance_id!r} "
                        f"maps to wokwi pin {b_wokwi!r}, not in {legal_pins(b_part_type)}"
                    )

            connections.append([
                f"{a_ref.instance_id.lower()}:{a_wokwi}",
                f"{b_ref.instance_id.lower()}:{b_wokwi}",
                "",
                [],
            ])

    return {
        "version": 1,
        "parts": parts,
        "connections": connections,
        "dependencies": {},
    }
