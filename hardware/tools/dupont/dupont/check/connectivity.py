from __future__ import annotations

import re
from dataclasses import dataclass

from dupont.model.entities import Circuit, Net

_TRAILING_UNIT_RE = re.compile(r"(ohm|Ω)\Z", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    severity: str
    kind: str
    entity: str
    schematic_value: str
    breadboard_value: str
    schematic_provenance: str
    breadboard_provenance: str


def _component_findings(schematic: Circuit, breadboard: Circuit) -> list[Finding]:
    schematic_ids = {c.instance_id for c in schematic.components}
    breadboard_ids = {c.instance_id for c in breadboard.components}

    findings = []
    for instance_id in schematic_ids - breadboard_ids:
        findings.append(
            Finding(
                severity="error",
                kind="missing_component",
                entity=instance_id,
                schematic_value="present",
                breadboard_value="absent",
                schematic_provenance="",
                breadboard_provenance="",
            )
        )
    for instance_id in breadboard_ids - schematic_ids:
        findings.append(
            Finding(
                severity="error",
                kind="extra_component",
                entity=instance_id,
                schematic_value="absent",
                breadboard_value="present",
                schematic_provenance="",
                breadboard_provenance="",
            )
        )
    return findings


def _net_groups(circuit: Circuit) -> dict[frozenset, Net]:
    groups = {}
    for net in circuit.nets:
        members = frozenset((ref.instance_id, ref.pin) for ref in net.member_pin_refs)
        if len(members) >= 2:
            groups[members] = net
    return groups


def _net_entity(net: Net) -> str:
    return repr(tuple(sorted((ref.instance_id, ref.pin) for ref in net.member_pin_refs)))


def _net_mismatch_findings(schematic: Circuit, breadboard: Circuit) -> list[Finding]:
    schematic_groups = _net_groups(schematic)
    breadboard_groups = _net_groups(breadboard)

    findings = []
    for members in schematic_groups.keys() - breadboard_groups.keys():
        net = schematic_groups[members]
        entity = _net_entity(net)
        findings.append(
            Finding(
                severity="error",
                kind="net_mismatch",
                entity=entity,
                schematic_value=entity,
                breadboard_value="",
                schematic_provenance=net.provenance,
                breadboard_provenance="",
            )
        )
    for members in breadboard_groups.keys() - schematic_groups.keys():
        net = breadboard_groups[members]
        entity = _net_entity(net)
        findings.append(
            Finding(
                severity="error",
                kind="net_mismatch",
                entity=entity,
                schematic_value="",
                breadboard_value=entity,
                schematic_provenance="",
                breadboard_provenance=net.provenance,
            )
        )
    return findings


def _normalize_value(value: str | None) -> str:
    text = (value or "").strip()
    text = _TRAILING_UNIT_RE.sub("", text, count=1)
    return text.strip()


def _value_mismatch_findings(schematic: Circuit, breadboard: Circuit) -> list[Finding]:
    schematic_by_id = {c.instance_id: c for c in schematic.components}
    breadboard_by_id = {c.instance_id: c for c in breadboard.components}

    findings = []
    for instance_id in schematic_by_id.keys() & breadboard_by_id.keys():
        schematic_component = schematic_by_id[instance_id]
        breadboard_component = breadboard_by_id[instance_id]
        if _normalize_value(schematic_component.value) != _normalize_value(breadboard_component.value):
            findings.append(
                Finding(
                    severity="warning",
                    kind="value_mismatch",
                    entity=instance_id,
                    schematic_value=schematic_component.value or "",
                    breadboard_value=breadboard_component.value or "",
                    schematic_provenance="",
                    breadboard_provenance="",
                )
            )
    return findings


def _uncanonical_component_findings(schematic: Circuit, breadboard: Circuit) -> list[Finding]:
    known_ids = {c.instance_id for c in schematic.components} | {c.instance_id for c in breadboard.components}

    referenced_ids = set()
    for circuit in (schematic, breadboard):
        for net in circuit.nets:
            for ref in net.member_pin_refs:
                referenced_ids.add(ref.instance_id)

    findings = []
    for instance_id in referenced_ids - known_ids:
        findings.append(
            Finding(
                severity="error",
                kind="uncanonical_component",
                entity=instance_id,
                schematic_value="",
                breadboard_value="",
                schematic_provenance="",
                breadboard_provenance="",
            )
        )
    return findings


def check_connectivity(schematic: Circuit, breadboard: Circuit) -> list[Finding]:
    """Compare two canonicalized Circuits and return Findings sorted by (kind, entity)."""
    findings = [
        *_component_findings(schematic, breadboard),
        *_net_mismatch_findings(schematic, breadboard),
        *_value_mismatch_findings(schematic, breadboard),
        *_uncanonical_component_findings(schematic, breadboard),
    ]
    return sorted(findings, key=lambda f: (f.kind, f.entity))
