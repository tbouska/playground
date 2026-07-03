from __future__ import annotations

from pathlib import Path

import yaml

from breadboard.model import Component as BreadboardComponent
from breadboard.model import Layout
from breadboard.parse import load_layout, parse_layout_data
from dupont.canon.ids import mint_ids
from dupont.canon.pins import normalize_pin_name
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef, Placement
from dupont.topology.nets import component_pins, extract_nets

_LED_POSITIONAL_PINS = {"1": "anode", "2": "cathode"}


def _layout_from_source(source: str | Path | dict) -> Layout:
    if isinstance(source, dict):
        return parse_layout_data(source)
    if isinstance(source, Path):
        return load_layout(source)
    if "\n" not in source and Path(source).exists():
        return load_layout(Path(source))
    return parse_layout_data(yaml.safe_load(source))


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


def _build_remap(
    module: BreadboardComponent,
    led: BreadboardComponent | None,
    led_id: str | None,
    mcu_id: str,
    resistors: list[BreadboardComponent],
    buttons: list[BreadboardComponent],
    raw_nets: tuple[Net, ...],
) -> dict[tuple[str, str], tuple[str, str]]:
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
                normalize_pin_name(led.kind, raw_pin)
                if led.kind == "led-rgb"
                else _LED_POSITIONAL_PINS[raw_pin]
            )
            remap[(led.ref, raw_pin)] = (led_id, canonical_pin)

    for resistor in resistors:
        pin_remap = _resistor_pin_remap(resistor, module.ref, net_of)
        for raw_pin, canonical_pin in pin_remap.items():
            remap[(resistor.ref, raw_pin)] = (resistor.ref, canonical_pin)

    for button in buttons:
        for raw_pin, _hole in component_pins(button):
            remap[(button.ref, raw_pin)] = (button.ref, raw_pin)
    return remap


def _led_component(
    led: BreadboardComponent,
    led_id: str,
    remap: dict[tuple[str, str], tuple[str, str]],
) -> Component:
    led_pin_names = [remap[(led.ref, raw_pin)][1] for raw_pin, _hole in component_pins(led)]
    led_pins = tuple(
        Pin(name, name, "passive", index) for index, name in enumerate(led_pin_names)
    )
    return Component(led_id, led.kind, led_pins, label=led.label, value=(led.value or None))


def _build_components(
    module: BreadboardComponent,
    led: BreadboardComponent | None,
    led_id: str | None,
    mcu_id: str,
    resistors: list[BreadboardComponent],
    buttons: list[BreadboardComponent],
    remap: dict[tuple[str, str], tuple[str, str]],
) -> list[Component]:
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
            (Pin("1", "1", "passive", 0), Pin("2", "2", "passive", 1)),
            value=(resistor.value or None),
        )
        for resistor in resistors
    ]
    button_components = [
        Component(
            button.ref,
            "button",
            tuple(
                Pin(name, name, "passive", index)
                for index, (name, _hole) in enumerate(component_pins(button))
            ),
            label=button.label,
            value=(button.value or None),
        )
        for button in buttons
    ]
    components = [mcu_component, *resistor_components, *button_components]
    if led is not None:
        components.append(_led_component(led, led_id, remap))
    return components


def _build_placements(
    layout: Layout,
    module: BreadboardComponent,
    led: BreadboardComponent | None,
    mcu_id: str,
    led_id: str | None,
) -> list[Placement]:
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
    return placements


def import_layout(source: str | Path | dict) -> Circuit:
    layout = _layout_from_source(source)
    raw_nets = extract_nets(layout)

    modules = [c for c in layout.components if c.kind == "module"]
    if len(modules) != 1:
        raise ValueError(f"expected exactly one 'module' (MCU) component, found {len(modules)}")
    module = modules[0]
    leds = [c for c in layout.components if c.kind in ("led", "led-rgb")]
    if len(leds) > 1:
        raise ValueError(f"expected at most one led/led-rgb component, found {len(leds)}")
    led = leds[0] if leds else None
    led_kind = led.kind if led else None
    resistors = [c for c in layout.components if c.kind == "resistor"]
    buttons = [c for c in layout.components if c.kind == "button"]

    mcu_id, *led_ids = mint_ids(["mcu"] + ([led_kind] if led else []))
    led_id = led_ids[0] if led else None

    remap = _build_remap(module, led, led_id, mcu_id, resistors, buttons, raw_nets)

    nets = tuple(
        Net(
            net.net_id,
            tuple(PinRef(*remap[(r.instance_id, r.pin)]) for r in net.member_pin_refs),
            net.provenance,
        )
        for net in raw_nets
    )

    components = _build_components(module, led, led_id, mcu_id, resistors, buttons, remap)
    placements = _build_placements(layout, module, led, mcu_id, led_id)

    return Circuit(
        title=layout.title,
        components=tuple(components),
        nets=nets,
        placements=tuple(placements),
    )
