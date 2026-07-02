from __future__ import annotations

import yaml

from dupont.canon.pins import denormalize_pin_name
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
from dupont.model.entities import Circuit, Component, Net


def _nets_for_instance(circuit: Circuit, instance_id: str) -> list[Net]:
    nets = []
    for net in circuit.nets:
        for pin_ref in net.member_pin_refs:
            if pin_ref.instance_id == instance_id:
                nets.append(net)
                break
    return nets


def _collapse_resistor_channel(
    circuit: Circuit,
    resistor: Component,
    mcu: Component,
    load: Component,
    load_kind: str,
    cathode_pin_name: str,
) -> Channel:
    resistor_nets = _nets_for_instance(circuit, resistor.instance_id)

    if len(resistor_nets) != 2:
        raise ValueError(f"resistor {resistor.instance_id} does not have exactly 2 nets")

    gpio_pin = None
    load_anode_pin = None

    for net in resistor_nets:
        for pin_ref in net.member_pin_refs:
            gpio_match = pin_ref.instance_id == mcu.instance_id and pin_ref.pin in [
                p.name for p in mcu.pins if p.type == "gpio"
            ]
            anode_match = pin_ref.instance_id == load.instance_id and pin_ref.pin != cathode_pin_name

            if gpio_match and gpio_pin is not None:
                raise ValueError(f"resistor {resistor.instance_id} connects to multiple MCU GPIOs")
            elif gpio_match:
                gpio_pin = pin_ref.pin
            elif anode_match and load_anode_pin is not None:
                raise ValueError(f"resistor {resistor.instance_id} connects to multiple load anodes")
            elif anode_match:
                load_anode_pin = pin_ref.pin

    if gpio_pin is None or load_anode_pin is None:
        raise ValueError(f"resistor {resistor.instance_id} nets do not form a (gpio, load) channel")

    load_pin = denormalize_pin_name(load_kind, load_anode_pin)
    resistor_obj = Resistor(resistor.instance_id, resistor.value)
    return Channel(gpio_pin, load_pin, resistor_obj)


def _collapse_button(circuit: Circuit, button: Component, mcu: Component) -> Button:
    button_nets = _nets_for_instance(circuit, button.instance_id)

    if len(button_nets) != 2:
        raise ValueError(f"button {button.instance_id} does not have exactly 2 nets")

    # Identify the gpio-side net: the net containing an MCU gpio pin
    mcu_gpio_names = {pin.name for pin in mcu.pins if pin.type == "gpio"}
    gpio_side_net = None
    gpio_pin = None

    for net in button_nets:
        for pin_ref in net.member_pin_refs:
            if pin_ref.instance_id == mcu.instance_id and pin_ref.pin in mcu_gpio_names:
                gpio_side_net = net
                gpio_pin = pin_ref.pin
                break
        if gpio_side_net is not None:
            break

    if gpio_side_net is None or gpio_pin is None:
        raise ValueError(f"button {button.instance_id} has no gpio-side net")

    far_leg_net = next(net for net in button_nets if net is not gpio_side_net)

    return Button(button.instance_id, gpio_pin, far_leg_net.net_id)


def collapse_to_schematic(circuit: Circuit) -> Schematic:
    net_id_of = {}
    for net in circuit.nets:
        for pin_ref in net.member_pin_refs:
            net_id_of[(pin_ref.instance_id, pin_ref.pin)] = net.net_id

    mcu = next((c for c in circuit.components if c.kind == "mcu"), None)
    if mcu is None:
        raise ValueError("no mcu component to collapse")

    mcu_power_pins = []
    for pin in mcu.pins:
        if pin.type == "power":
            net_id = net_id_of.get((mcu.instance_id, pin.name))
            if net_id is not None:
                mcu_power_pins.append(PowerPin(pin.name, net_id))

    mcu_obj = Mcu(label=mcu.label, power=tuple(mcu_power_pins))

    load = next((c for c in circuit.components if c.kind in {"led", "led-rgb"}), None)
    if load is None:
        raise ValueError("no load/led component to collapse")
    load_kind = load.kind

    cathode_pin_name = next((p.name for p in load.pins if p.name == "cathode"), None)
    if cathode_pin_name is None:
        raise ValueError("no cathode pin found on load component")

    cathode_net_id = net_id_of.get((load.instance_id, cathode_pin_name))
    if cathode_net_id is None:
        raise ValueError("cathode pin not connected to any net")

    load_obj = Load(label=load.label, common=TerminalPin(denormalize_pin_name(load_kind, "cathode"), cathode_net_id))

    resistor_components = [c for c in circuit.components if c.kind == "resistor"]
    channels = [
        _collapse_resistor_channel(circuit, resistor, mcu, load, load_kind, cathode_pin_name)
        for resistor in resistor_components
    ]

    button_components = [c for c in circuit.components if c.kind == "button"]
    buttons = [_collapse_button(circuit, button, mcu) for button in button_components]

    return Schematic(circuit.title, mcu_obj, load_obj, tuple(channels), tuple(buttons))


def export_circuit(circuit: Circuit) -> str:
    schematic = collapse_to_schematic(circuit)

    result = {
        "title": schematic.title,
        "mcu": {
            "label": schematic.mcu.label,
            "power": [{"pin": p.pin, "net": p.net} for p in schematic.mcu.power]
        },
        "load": {
            "label": schematic.load.label,
            "common": {"pin": schematic.load.common.pin, "net": schematic.load.common.net}
        },
        "channels": [
            {
                "gpio": c.gpio,
                "load_pin": c.load_pin,
                "resistor": {"ref": c.resistor.ref, "value": c.resistor.value}
            } for c in schematic.channels
        ]
    }

    if schematic.buttons:
        result["buttons"] = [
            {"ref": b.ref, "gpio": b.gpio, "net": b.net} for b in schematic.buttons
        ]

    return yaml.safe_dump(result, sort_keys=False, allow_unicode=True)
