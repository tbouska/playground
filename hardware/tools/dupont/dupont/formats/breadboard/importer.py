from __future__ import annotations

from pathlib import Path

import yaml

from breadboard.model import Component as BreadboardComponent
from breadboard.model import Layout
from breadboard.parse import _component_from_dict, load_layout
from dupont.canon.ids import mint_ids
from dupont.canon.pins import normalize_pin_name
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef, Placement
from dupont.topology.nets import component_pins, extract_nets

_LED_POSITIONAL_PINS = {"1": "anode", "2": "cathode"}


def _layout_from_source(source: str | Path | dict) -> Layout:
    if isinstance(source, dict):
        data = source
    elif isinstance(source, Path):
        return load_layout(source)
    else:
        if "\n" not in source and Path(source).exists():
            return load_layout(Path(source))
        data = yaml.safe_load(source)
    return Layout(
        title=str(data.get("title", "Breadboard layout")),
        columns=int(data["breadboard"]["columns"]),
        components=tuple(_component_from_dict(c) for c in data["components"]),
        style=data.get("style"),
    )


def _coords_for(component: BreadboardComponent) -> dict:
    return {
        "kind": component.kind,
        "ref": component.ref,
        "label": component.label,
        "value": component.value,
        "legs": list(component.legs),
        "named_legs": dict(component.named_legs),
        "common": component.common,
        "color": component.color,
        "endpoints": list(component.endpoints),
        "span": list(component.span),
        "pins": [{"name": p.name, "hole": p.hole} for p in component.pins],
        "digits": component.digits,
    }


def _resistor_pin_remap(
    resistor: BreadboardComponent, module_ref: str, net_of: dict[tuple[str, str], Net]
) -> dict[str, str]:
    def touches_mcu(raw_pin: str) -> bool:
        net = net_of.get((resistor.ref, raw_pin))
        return net is not None and any(r.instance_id == module_ref for r in net.member_pin_refs)

    leg1_touches = touches_mcu("1")
    leg2_touches = touches_mcu("2")
    if leg2_touches and not leg1_touches:
        return {"2": "1", "1": "2"}
    return {"1": "1", "2": "2"}


def import_layout(source: str | Path | dict) -> Circuit:
    layout = _layout_from_source(source)
    raw_nets = extract_nets(layout)

    module = next(c for c in layout.components if c.kind == "module")
    led = next((c for c in layout.components if c.kind in ("led", "led-rgb")), None)
    led_kind = led.kind if led else None
    resistors = [c for c in layout.components if c.kind == "resistor"]

    mcu_id, *led_ids = mint_ids(["mcu"] + ([led_kind] if led else []))
    led_id = led_ids[0] if led else None

    net_of: dict[tuple[str, str], Net] = {}
    for net in raw_nets:
        for ref in net.member_pin_refs:
            net_of[(ref.instance_id, ref.pin)] = net

    remap: dict[tuple[str, str], tuple[str, str]] = {}
    for raw_pin, _hole in component_pins(module):
        remap[(module.ref, raw_pin)] = (mcu_id, raw_pin)

    if led is not None:
        for raw_pin, _hole in component_pins(led):
            canonical_pin = (
                normalize_pin_name(led_kind, raw_pin)
                if led_kind == "led-rgb"
                else _LED_POSITIONAL_PINS[raw_pin]
            )
            remap[(led.ref, raw_pin)] = (led_id, canonical_pin)

    for resistor in resistors:
        pin_remap = _resistor_pin_remap(resistor, module.ref, net_of)
        for raw_pin, canonical_pin in pin_remap.items():
            remap[(resistor.ref, raw_pin)] = (resistor.ref, canonical_pin)

    nets = tuple(
        Net(
            net.net_id,
            tuple(PinRef(*remap[(r.instance_id, r.pin)]) for r in net.member_pin_refs),
            net.provenance,
        )
        for net in raw_nets
    )

    mcu_component = Component(
        mcu_id,
        "mcu",
        tuple(
            Pin(name, name, "pin", index)
            for index, (name, _hole) in enumerate(component_pins(module))
        ),
        label=module.label,
    )
    resistor_components = [
        Component(
            resistor.ref,
            "resistor",
            (Pin("1", "1", "pin", 0), Pin("2", "2", "pin", 1)),
            value=(resistor.value or None),
        )
        for resistor in resistors
    ]
    components = [mcu_component, *resistor_components]
    if led is not None:
        led_pins = tuple(
            Pin(
                remap[(led.ref, raw_pin)][1],
                remap[(led.ref, raw_pin)][1],
                "pin",
                index,
            )
            for index, (raw_pin, _hole) in enumerate(component_pins(led))
        )
        components.append(
            Component(led_id, led_kind, led_pins, label=led.label, value=(led.value or None))
        )

    placements = []
    for component in layout.components:
        if component is module:
            component_ref = mcu_id
        elif component is led:
            component_ref = led_id
        else:
            component_ref = component.ref
        placements.append(
            Placement(
                component_ref,
                _coords_for(component),
                0.0,
                "breadboard",
                "breadboard/component",
            )
        )
    placements.append(
        Placement(
            "__board__",
            {"columns": layout.columns, "style": layout.style},
            0.0,
            "breadboard",
            "breadboard/board",
        )
    )

    return Circuit(
        title=layout.title,
        components=tuple(components),
        nets=nets,
        placements=tuple(placements),
    )
