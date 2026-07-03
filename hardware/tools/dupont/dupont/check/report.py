"""Turn check_connectivity() Findings into plain-dict records plus a summary."""

from __future__ import annotations

from dupont.check.connectivity import Finding

DEFAULT_SEVERITY: dict[str, str] = {
    "missing_component": "error",
    "extra_component": "error",
    "net_mismatch": "error",
    "uncanonical_component": "error",
    "value_mismatch": "warning",
}


def format_report(findings: list[Finding], strict: bool = False) -> tuple[list[dict], str]:
    records = []
    for finding in findings:
        severity = DEFAULT_SEVERITY[finding.kind]
        if strict and severity == "warning":
            severity = "error"
        records.append(
            {
                "severity": severity,
                "kind": finding.kind,
                "entity": finding.entity,
                "schematic_value": finding.schematic_value,
                "breadboard_value": finding.breadboard_value,
                "schematic_provenance": finding.schematic_provenance,
                "breadboard_provenance": finding.breadboard_provenance,
            }
        )

    error_count = sum(1 for record in records if record["severity"] == "error")
    warning_count = sum(1 for record in records if record["severity"] == "warning")

    lines = [f"{error_count} errors, {warning_count} warnings"]
    lines.extend(f"[{record['severity']}]: {record['kind']}: {record['entity']}" for record in records)

    return records, "\n".join(lines)
