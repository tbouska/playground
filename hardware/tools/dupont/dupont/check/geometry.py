from __future__ import annotations

from dataclasses import dataclass

from dupont.check.connectivity import _net_groups
from dupont.formats.wokwi.maps import KIND_TO_PART_TYPE, PART_TYPE_PINS, canon_pin_to_wokwi, legal_pins
from dupont.grid.geometry import SNAP_TOLERANCE_MM, compare_geometry
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


def _net_mismatch_findings3(circuits: dict[str, Circuit]) -> list[Finding3]:
    """A canonicalized net group present in some formats but not all three."""
    g: dict[str, dict[frozenset, Net]] = {fmt: _net_groups(circuits[fmt]) for fmt in _FORMATS}
    all_members: set[frozenset] = set().union(*(g[fmt].keys() for fmt in _FORMATS))

    findings: list[Finding3] = []
    for members in all_members:
        present_in = tuple(fmt for fmt in _FORMATS if members in g[fmt])
        absent_in = tuple(fmt for fmt in _FORMATS if members not in g[fmt])
        if len(present_in) < 3:
            findings.append(
                Finding3(
                    severity="error",
                    kind="net_mismatch",
                    entity=repr(tuple(sorted(members))),
                    present_in=present_in,
                    absent_in=absent_in,
                    detail="",
                    provenance=g[present_in[0]][members].provenance,
                )
            )
    return findings


def _missing_component_findings3(circuits: dict[str, Circuit]) -> list[Finding3]:
    """A component instance present in some formats but not all three."""
    ids_by_fmt: dict[str, set[str]] = {
        fmt: {c.instance_id for c in circuits[fmt].components} for fmt in _FORMATS
    }
    all_ids: set[str] = set().union(*ids_by_fmt.values())

    findings: list[Finding3] = []
    for instance_id in all_ids:
        present_in = tuple(fmt for fmt in _FORMATS if instance_id in ids_by_fmt[fmt])
        absent_in = tuple(fmt for fmt in _FORMATS if instance_id not in ids_by_fmt[fmt])
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
    return findings


def _pin_mapping_findings3(wokwi: Circuit) -> list[Finding3]:
    """A wokwi part_type/pin that violates the mapping tables (wokwi-only rule)."""
    findings: list[Finding3] = []
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
    return findings


def _geometry_drift_findings3(
    breadboard: Circuit, wokwi: Circuit, strict: bool
) -> list[Finding3]:
    """Cross-coordinate drift beyond tolerance (advisory WARNING; ERROR under strict)."""
    findings: list[Finding3] = []
    for gf in compare_geometry(breadboard, wokwi):
        findings.append(
            Finding3(
                severity="error" if strict else "warning",
                kind="geometry_drift",
                entity=gf.component_ref,
                present_in=(),
                absent_in=(),
                detail=f"{gf.drift_mm:.1f}mm > {SNAP_TOLERANCE_MM:.1f}mm",
                provenance="geometry",
            )
        )
    return findings


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
    circuits: dict[str, Circuit] = {
        "schematic": schematic,
        "breadboard": breadboard,
        "wokwi": wokwi,
    }
    findings = (
        _net_mismatch_findings3(circuits)
        + _missing_component_findings3(circuits)
        + _pin_mapping_findings3(wokwi)
        + _geometry_drift_findings3(breadboard, wokwi, strict)
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
