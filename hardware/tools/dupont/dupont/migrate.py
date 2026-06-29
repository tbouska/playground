"""Migrate project ``circuit.yaml`` files to the annotated interchange-model
schema, gated per file by round-trip checks.

Each file is migrated independently. Its model schema (``<project>.model.yaml``)
is written only when:

1. the model schema round-trips losslessly (``load_model(dump_model(c)) == c``),
   so the written artifact reloads to the exact source model; and
2. the channel structure round-trips deterministically through the exporter
   (``export_circuit`` reproduces the same ``circuit.yaml`` on re-import, and
   raises loud when a netlist has no collapsible channel/button/power shape).

A file that fails either gate is rolled back (its partial output removed) and
reported with the schema diff, so one unmigratable circuit never leaves a
half-written artifact or aborts the rest of the batch. Render parity is covered
separately by the golden gate in ``tests/test_schematic_parity.py`` (the render
is a pure function of the model, so model identity implies render identity).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from dupont.formats.circuit.exporter import export_circuit
from dupont.formats.circuit.importer import import_circuit
from dupont.model.serialize import dump_model, load_model


class MigrationError(Exception):
    """A ``circuit.yaml`` could not be migrated; its output was rolled back."""

    def __init__(self, source: Path, schema_diff: str) -> None:
        self.source = source
        self.schema_diff = schema_diff
        super().__init__(f"migration failed for {source}: {schema_diff}")


@dataclass(frozen=True)
class MigrationReport:
    """The result of a per-file migration batch.

    :ivar migrated: Paths of the ``.model.yaml`` artifacts written.
    :ivar failed: ``(source, reason)`` for each rolled-back file.
    """

    migrated: tuple[Path, ...]
    failed: tuple[tuple[Path, str], ...]


def _diff(label_a: str, a: str, label_b: str, b: str) -> str:
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            label_a,
            label_b,
        )
    )


def migrate_circuit(circuit_path: Path, out_dir: Path) -> Path:
    """Migrate one ``circuit.yaml`` to ``<out_dir>/<project>.model.yaml``.

    The output basename is the source's parent directory name, so circuits from
    different projects never collide in a shared ``out_dir``.

    :param circuit_path: The ``circuit.yaml`` to migrate.
    :param out_dir: The directory the ``.model.yaml`` is written into.
    :returns: The path of the written ``.model.yaml``.
    :raises MigrationError: If a round-trip gate fails. No file is left behind.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{circuit_path.parent.name}.model.yaml"
    try:
        circuit = import_circuit(circuit_path)

        schema = dump_model(circuit)
        if load_model(schema) != circuit:
            raise ValueError(
                "model schema round-trip is not identity:\n"
                + _diff("source", schema, "reloaded", dump_model(load_model(schema)))
            )

        round_trip = export_circuit(import_circuit(export_circuit(circuit)))
        baseline = export_circuit(circuit)
        if round_trip != baseline:
            raise ValueError(
                "round-trip did not reproduce the channel structure:\n"
                + _diff("source", baseline, "round-trip", round_trip)
            )

        output.write_text(schema, encoding="utf-8")
        if load_model(output) != circuit:
            raise ValueError("written .model.yaml did not reload to the source model")
        return output
    except (ValueError, KeyError) as exc:
        if output.exists():
            output.unlink()  # per-file rollback
        raise MigrationError(circuit_path, str(exc)) from exc


def migrate_circuits(circuit_paths: list[Path], out_dir: Path) -> MigrationReport:
    """Migrate many ``circuit.yaml`` files, rolling back each failure in place.

    A failure on one file rolls back only that file and is recorded in
    :attr:`MigrationReport.failed`; the remaining files still migrate.
    """
    migrated: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for path in circuit_paths:
        try:
            migrated.append(migrate_circuit(path, out_dir))
        except MigrationError as exc:
            failed.append((exc.source, exc.schema_diff))
    return MigrationReport(tuple(migrated), tuple(failed))
