from __future__ import annotations

from pathlib import Path

import yaml

from dupont.canon.ids import mint_ids
from dupont.canon.pins import normalize_pin_name
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef, Role


def import_circuit(source: str | Path | dict) -> Circuit:
    if isinstance(source, dict):
        data = source
    elif isinstance(source, Path):
        data = yaml.safe_load(source.read_text())
    else:
        if "\n" not in source and Path(source).exists():
            data = yaml.safe_load(Path(source).read_text())
        else:
            data = yaml.safe_load(source)

    for key in ("mcu", "load", "channels"):
        if key not in data:
            raise ValueError(f"missing required key: {key!r}")
    if "common" not in data["load"]:
        raise ValueError("missing required key: 'common'")

    title = data["title"]
    mcu_data = data["mcu"]
    load_data = data["load"]
    channels = data["channels"]
    buttons = data.get("buttons", [])

    led_kind = "led" if len(channels) == 1 else "led-rgb"
    u1_id, d1_id = mint_ids(["mcu", led_kind])

    # MCU component
    power_entries = mcu_data.get("power", [])
    _mcu_pin_spec = (
        [(e["pin"], "power") for e in power_entries]
        + [(ch["gpio"], "gpio") for ch in channels]
        + [(btn["gpio"], "gpio") for btn in buttons]
    )
    mcu_pins = [Pin(n, n, t, i) for i, (n, t) in enumerate(_mcu_pin_spec)]
    u1 = Component(u1_id, "mcu", tuple(mcu_pins), label=mcu_data["label"])

    # Resistor components
    resistors = [
        Component(
            ch["resistor"]["ref"],
            "resistor",
            (Pin("1", "1", "passive", 0), Pin("2", "2", "passive", 1)),
            value=ch["resistor"]["value"],
        )
        for ch in channels
    ]

    # LED component
    common_pin_name = normalize_pin_name(led_kind, load_data["common"]["pin"])
    _led_names = [
        normalize_pin_name(led_kind, ch["load_pin"]) for ch in channels
    ] + [common_pin_name]
    led_pins = [Pin(n, n, "passive", i) for i, n in enumerate(_led_names)]
    d1 = Component(d1_id, led_kind, tuple(led_pins), label=load_data.get("label", ""))

    # Button components
    button_components = [
        Component(
            btn["ref"],
            "button",
            (Pin("1", "1", "passive", 0), Pin("2", "2", "passive", 1)),
        )
        for btn in buttons
    ]

    # Nets
    nets = []
    _counter = 0

    def _next_net_id() -> str:
        nonlocal _counter
        _counter += 1
        return f"_net{_counter}"

    # Channel nets: 2 per channel
    for ch in channels:
        r_ref = ch["resistor"]["ref"]
        anode_name = normalize_pin_name(led_kind, ch["load_pin"])
        nets.append(Net(
            _next_net_id(),
            (PinRef(u1_id, ch["gpio"]), PinRef(r_ref, "1")),
            "schematic/channel",
        ))
        nets.append(Net(
            _next_net_id(),
            (PinRef(r_ref, "2"), PinRef(d1_id, anode_name)),
            "schematic/channel",
        ))

    # Button gpio nets
    for btn in buttons:
        nets.append(Net(
            _next_net_id(),
            (PinRef(u1_id, btn["gpio"]), PinRef(btn["ref"], "1")),
            "schematic/button",
        ))

    # Named nets: group by net name
    common_net_name = load_data["common"]["net"]
    power_net_names = {entry["net"] for entry in power_entries}

    named: dict[str, list[PinRef]] = {}
    named.setdefault(common_net_name, []).append(PinRef(d1_id, common_pin_name))
    for entry in power_entries:
        named.setdefault(entry["net"], []).append(PinRef(u1_id, entry["pin"]))
    for btn in buttons:
        named.setdefault(btn["net"], []).append(PinRef(btn["ref"], "2"))

    for net_name, refs in named.items():
        if net_name == common_net_name:
            provenance = "schematic/common"
        elif net_name in power_net_names:
            provenance = "schematic/power"
        else:
            provenance = "schematic/button"
        nets.append(Net(net_name, tuple(refs), provenance))

    # Roles
    roles: list[Role] = [Role(u1_id, "mcu", "inferred")]
    for r in resistors:
        roles.append(Role(r.instance_id, "series_resistor", "inferred"))
    roles.append(Role(d1_id, "load", "inferred"))
    roles.append(Role(common_net_name, "common_net", "inferred"))
    seen_power: set[str] = set()
    for entry in power_entries:
        net_name = entry["net"]
        if net_name != common_net_name and net_name not in seen_power:
            seen_power.add(net_name)
            roles.append(Role(net_name, "power_net", "inferred"))

    return Circuit(
        title=title,
        components=tuple([u1] + resistors + [d1] + button_components),
        nets=tuple(nets),
        roles=tuple(roles),
    )
