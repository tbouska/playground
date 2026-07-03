"""Tests for dupont.check.report: the DEFAULT_SEVERITY matrix and format_report().

format_report() turns check_connectivity()'s Findings into plain-dict records
plus a human-readable summary string. All tests are black-box: they construct
Finding instances directly and assert on the published (records, summary)
contract, not on any implementation detail.
"""

import pytest

from dupont.check.connectivity import Finding
from dupont.check.report import DEFAULT_SEVERITY, format_report

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Deliberately not "error" or "warning": every test below constructs findings
# with this severity by default, so if format_report ever copied
# finding.severity verbatim instead of consulting DEFAULT_SEVERITY, this value
# would leak into the record and the test would catch it.
_UNUSED_SEVERITY = "unused-severity-field"


def _finding(
    kind,
    entity="R1",
    severity=_UNUSED_SEVERITY,
    schematic_value="sv",
    breadboard_value="bv",
    schematic_provenance="circuit.yaml",
    breadboard_provenance="layout.yaml",
):
    return Finding(
        severity=severity,
        kind=kind,
        entity=entity,
        schematic_value=schematic_value,
        breadboard_value=breadboard_value,
        schematic_provenance=schematic_provenance,
        breadboard_provenance=breadboard_provenance,
    )


# ---------------------------------------------------------------------------
# 1. DEFAULT_SEVERITY matrix contents
# ---------------------------------------------------------------------------


def test_default_severity_matrix_matches_pinned_values():
    assert DEFAULT_SEVERITY == {
        "missing_component": "error",
        "extra_component": "error",
        "net_mismatch": "error",
        "uncanonical_component": "error",
        "value_mismatch": "warning",
    }


# ---------------------------------------------------------------------------
# 2. Empty findings
# ---------------------------------------------------------------------------


def test_empty_findings_returns_empty_records_and_zero_summary():
    assert format_report([]) == ([], "0 errors, 0 warnings")


# ---------------------------------------------------------------------------
# 3. Each kind maps to its pinned severity in the record
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "expected_severity"),
    [
        ("missing_component", "error"),
        ("extra_component", "error"),
        ("net_mismatch", "error"),
        ("uncanonical_component", "error"),
        ("value_mismatch", "warning"),
    ],
)
def test_each_finding_kind_maps_to_pinned_default_severity(kind, expected_severity):
    records, _ = format_report([_finding(kind)])
    assert records[0]["severity"] == expected_severity


# ---------------------------------------------------------------------------
# 4. Record shape: exactly 7 keys, copied verbatim from the finding
# ---------------------------------------------------------------------------


def test_record_has_exactly_seven_keys_copied_from_finding():
    finding = _finding(
        "net_mismatch",
        entity="R1",
        schematic_value="net-a",
        breadboard_value="net-b",
        schematic_provenance="circuit.yaml:12",
        breadboard_provenance="layout.yaml:34",
    )
    records, _ = format_report([finding])
    assert len(records) == 1
    record = records[0]
    assert set(record.keys()) == {
        "severity",
        "kind",
        "entity",
        "schematic_value",
        "breadboard_value",
        "schematic_provenance",
        "breadboard_provenance",
    }
    assert record["kind"] == "net_mismatch"
    assert record["entity"] == "R1"
    assert record["schematic_value"] == "net-a"
    assert record["breadboard_value"] == "net-b"
    assert record["schematic_provenance"] == "circuit.yaml:12"
    assert record["breadboard_provenance"] == "layout.yaml:34"
    assert record["severity"] == "error"


# ---------------------------------------------------------------------------
# 5. strict=True promotes a warning-severity record to error
# ---------------------------------------------------------------------------


def test_strict_mode_promotes_warning_to_error_in_record_and_summary():
    finding = _finding("value_mismatch", entity="R1")

    strict_records, strict_summary = format_report([finding], strict=True)
    assert strict_records[0]["severity"] == "error"
    assert strict_summary.splitlines()[0] == "1 errors, 0 warnings"

    records, summary = format_report([finding], strict=False)
    assert records[0]["severity"] == "warning"
    assert summary.splitlines()[0] == "0 errors, 1 warnings"


# ---------------------------------------------------------------------------
# 6. Summary line 1: correct counts for a mixed, non-strict findings list
# ---------------------------------------------------------------------------


def test_summary_first_line_counts_errors_and_warnings_for_mixed_findings():
    findings = [
        _finding("missing_component", entity="D1"),
        _finding("value_mismatch", entity="R1"),
        _finding("net_mismatch", entity="R2"),
    ]
    _, summary = format_report(findings)
    assert summary.splitlines()[0] == "2 errors, 1 warnings"


# ---------------------------------------------------------------------------
# 7. Per-finding summary lines: pinned format, input order preserved
# ---------------------------------------------------------------------------


def test_summary_lines_follow_pinned_format_and_preserve_input_order():
    findings = [
        _finding("net_mismatch", entity="R2"),
        _finding("missing_component", entity="D1"),
        _finding("value_mismatch", entity="R1"),
    ]
    _, summary = format_report(findings)
    lines = summary.splitlines()
    assert lines[1] == "[error]: net_mismatch: R2"
    assert lines[2] == "[error]: missing_component: D1"
    assert lines[3] == "[warning]: value_mismatch: R1"


# ---------------------------------------------------------------------------
# 8. Purity: no files written
# ---------------------------------------------------------------------------


def test_format_report_is_pure_and_writes_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    format_report([_finding("value_mismatch")], strict=True)
    assert list(tmp_path.iterdir()) == []
