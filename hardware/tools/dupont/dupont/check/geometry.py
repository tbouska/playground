from __future__ import annotations

from dataclasses import dataclass

from dupont.check.connectivity import _net_groups
from dupont.formats.wokwi.maps import KIND_TO_PART_TYPE, PART_TYPE_PINS, canon_pin_to_wokwi, legal_pins
from dupont.grid.geometry import compare_geometry
from dupont.model.entities import Circuit, Net


@dataclass(frozen=True)
class Finding3:
    severity: str
    kind: str
    entity: str
    present_in: tuple[str, ...]
    absent_in: tuple[str, ...]
    detail: str
    provenance: str


_FORMATS = ("schematic", "breadboard", "wokwi")


def check_three_format(
    schematic: Circuit,
    breadboard: Circuit,
    wokwi: Circuit,
    *,
    strict: bool = False,
) -> list[Finding3]:
    """Compute cross-format findings from three circuits.

    Rules: net_mismatch, missing_component, pin_name/part_type (wokwi-only),
    and geometry_drift.  Returns sorted by ``(kind, entity)``.
    """
    findings: list[Finding3] = []

    # -- RULE 1: net_mismatch ------------------------------------------
    g: dict[str, dict[frozenset, Net]] = {
        "schematic": _net_groups(schematic),
        "breadboard": _net_groups(breadboard),
        "wokwi": _net_groups(wokwi),
    }
    all_members: set[frozenset] = (
        set(g["schematic"].keys())
        | set(g["breadboard"].keys())
        | set(g["wokwi"].keys())
    )
    for members in all_members:
        present_in = tuple(fmt for fmt in _FORMATS if members in g[fmt])
        absent_in = tuple(fmt for fmt in _FORMATS if members not in g[fmt])
        if len(present_in) < 3:
            provenance = g[present_in[0]][members].provenance
            findings.append(
                Finding3(
                    severity="error",
                    kind="net_mismatch",
                    entity=repr(tuple(sorted(members))),
                    present_in=present_in,
                    absent_in=absent_in,
                    detail="",
                    provenance=provenance,
                )
            )

    # -- RULE 2: missing_component -------------------------------------
    circuits: dict[str, Circuit] = {
        "schematic": schematic,
        "breadboard": breadboard,
        "wokwi": wokwi,
    }
    all_ids: set[str] = set()
    for circ in circuits.values():
        for comp in circ.components:
            all_ids.add(comp.instance_id)
    for instance_id in all_ids:
        present_in = tuple(
            fmt for fmt in _FORMATS if instance_id in {c.instance_id for c in circuits[fmt].components}
        )
        absent_in = tuple(
            fmt for fmt in _FORMATS if instance_id not in {c.instance_id for c in circuits[fmt].components}
        )
        if len(present_in) < 3:
            findings.append(
                Finding3(
                    severity="error",
                    kind="missing_component",
                    entity=instance_id,
                    present_in=present_in,
                    absent_in=absent_in,
                    detail="",
                    provenance="",
                )
            )

    # -- RULE 3: pin_name / part_type (wokwi only) ----------------------
    for comp in wokwi.components:
        if comp.kind not in KIND_TO_PART_TYPE:
            findings.append(
                Finding3(
                    severity="error",
                    kind="part_type",
                    entity=comp.instance_id,
                    present_in=("wokwi",),
                    absent_in=(),
                    detail=comp.kind,
                    provenance="wokwi",
                )
            )
            continue
        part_type = KIND_TO_PART_TYPE[comp.kind]
        if part_type in PART_TYPE_PINS:
            for pin in comp.pins:
                wpin = canon_pin_to_wokwi(comp.kind, pin.name)
                if wpin not in legal_pins(part_type):
                    findings.append(
                        Finding3(
                            severity="error",
                            kind="pin_name",
                            entity=f"{comp.instance_id}:{pin.name}",
                            present_in=("wokwi",),
                            absent_in=(),
                            detail=wpin,
                            provenance="wokwi",
                        )
                    )

    # -- RULE 4: geometry_drift ----------------------------------------
    for gf in compare_geometry(breadboard, wokwi):
        severity = "error" if strict else "warning"
        findings.append(
            Finding3(
                severity=severity,
                kind="geometry_drift",
                entity=gf.component_ref,
                present_in=(),
                absent_in=(),
                detail=f"{gf.drift_mm:.1f}mm > 1.0mm",
                provenance="geometry",
            )
        )

    return sorted(findings, key=lambda f: (f.kind, f.entity))


def format_three_report(
    findings: list[Finding3], strict: bool = False
) -> tuple[list[dict], str]:
    """Build (records, human summary) from three-format findings."""
    records: list[dict] = []
    for f in findings:
        severity = "error" if (strict and f.severity == "warning") else f.severity
        records.append(
            {
                "severity": severity,
                "kind": f.kind,
                "entity": f.entity,
                "present_in": f.present_in,
                "absent_in": f.absent_in,
                "detail": f.detail,
                "provenance": f.provenance,
            }
        )

    error_count = sum(1 for r in records if r["severity"] == "error")
    warning_count = sum(1 for r in records if r["severity"] == "warning")

    lines: list[str] = [f"{error_count} errors, {warning_count} warnings"]
    lines += [f"[{r['severity']}]: {r['kind']}: {r['entity']}" for r in records]

    return records, "\n".join(lines)
