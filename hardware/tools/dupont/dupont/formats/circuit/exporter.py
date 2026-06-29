from dupont.model.entities import Circuit
from dupont.formats.circuit.schema import Schematic, Mcu, Load, Channel, Button, Resistor, PowerPin, TerminalPin
from dupont.canon.pins import denormalize_pin_name


def collapse_to_schematic(circuit: Circuit) -> Schematic:
    net_id_of = {}
    for net in circuit.nets:
        for pin_ref in net.member_pin_refs:
            net_id_of[(pin_ref.instance_id, pin_ref.pin)] = net.net_id

    mcu = None
    for component in circuit.components:
        if component.kind == "mcu":
            mcu = component
            break
    
    if mcu is None:
        raise ValueError("no mcu component to collapse")

    mcu_power_pins = []
    for pin in mcu.pins:
        if pin.type == "power":
            net_id = net_id_of.get((mcu.instance_id, pin.name))
            if net_id is not None:
                mcu_power_pins.append(PowerPin(pin.name, net_id))
    
    mcu_obj = Mcu(label=mcu.label, power=tuple(mcu_power_pins))

    load = None
    load_kind = None
    for component in circuit.components:
        if component.kind in {"led", "led-rgb"}:
            load = component
            load_kind = component.kind
            break
    
    if load is None:
        raise ValueError("no load/led component to collapse")

    cathode_pin_name = None
    for pin in load.pins:
        if pin.name == "cathode":
            cathode_pin_name = pin.name
            break
    
    if cathode_pin_name is None:
        raise ValueError("no cathode pin found on load component")

    cathode_net_id = net_id_of.get((load.instance_id, cathode_pin_name))
    if cathode_net_id is None:
        raise ValueError("cathode pin not connected to any net")
        
    load_obj = Load(label=load.label, common=TerminalPin(denormalize_pin_name(load_kind, "cathode"), cathode_net_id))

    channels = []
    resistor_components = [c for c in circuit.components if c.kind == "resistor"]
    
    for resistor in resistor_components:
        resistor_nets = []
        for net in circuit.nets:
            for pin_ref in net.member_pin_refs:
                if pin_ref.instance_id == resistor.instance_id:
                    resistor_nets.append(net)
                    break
        
        if len(resistor_nets) != 2:
            raise ValueError(f"resistor {resistor.instance_id} does not have exactly 2 nets")

        gpio_pin = None
        load_anode_pin = None

        for net in resistor_nets:
            for pin_ref in net.member_pin_refs:
                if pin_ref.instance_id == mcu.instance_id and pin_ref.pin in [p.name for p in mcu.pins if p.type == "gpio"]:
                    if gpio_pin is not None:
                        raise ValueError(f"resistor {resistor.instance_id} connects to multiple MCU GPIOs")
                    gpio_pin = pin_ref.pin
                elif pin_ref.instance_id == load.instance_id and pin_ref.pin != cathode_pin_name:
                    if load_anode_pin is not None:
                        raise ValueError(f"resistor {resistor.instance_id} connects to multiple load anodes")
                    load_anode_pin = pin_ref.pin
        
        if gpio_pin is None or load_anode_pin is None:
            raise ValueError(f"resistor {resistor.instance_id} nets do not form a (gpio, load) channel")

        load_pin = denormalize_pin_name(load_kind, load_anode_pin)
        resistor_obj = Resistor(resistor.instance_id, resistor.value)
        channel = Channel(gpio_pin, load_pin, resistor_obj)
        channels.append(channel)

    buttons = []
    button_components = [c for c in circuit.components if c.kind == "button"]
    
    for button in button_components:
        button_nets = []
        for net in circuit.nets:
            for pin_ref in net.member_pin_refs:
                if pin_ref.instance_id == button.instance_id:
                    button_nets.append(net)
                    break
        
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

        button_obj = Button(button.instance_id, gpio_pin, far_leg_net.net_id)
        buttons.append(button_obj)
    
    return Schematic(circuit.title, mcu_obj, load_obj, tuple(channels), tuple(buttons))


def export_circuit(circuit: Circuit) -> str:
    from yaml import safe_dump

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
    
    return safe_dump(result, sort_keys=False, allow_unicode=True)