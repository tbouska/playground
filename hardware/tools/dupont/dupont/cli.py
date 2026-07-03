"""dupont CLI: convert between ``circuit.yaml`` and the interchange model.

Supports circuit<->circuit round-trip, circuit->model-schema conversion,
``--format layout`` import/export, and schematic<->breadboard consistency
checking::

    dupont import  --project <dir>                 # circuit.yaml -> <dir>.model.yaml
    dupont export  --project <dir>                 # *.model.yaml -> <name>.circuit.yaml
    dupont convert --project <dir>                 # circuit.yaml -> <dir>.convert.yaml
    dupont import  --project <dir> --format layout # layout.yaml -> <dir>.layout.model.yaml
    dupont export  --project <dir> --format layout # *.layout.model.yaml -> <name>.layout.svg
    dupont check   --project <dir> [--strict]      # circuit.yaml + layout.yaml -> report

``--project`` is scanned recursively. Any other direction or ``--format`` fails
loud listing the supported set, so remaining surfaces (wokwi) report an
explicit "not supported" error rather than silently doing nothing. All outputs
are written beside their source under new names; no source file is overwritten.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dupont.check.connectivity import check_connectivity
from dupont.check.geometry import check_three_format, format_three_report
from dupont.check.report import format_report
from dupont.formats.breadboard.importer import import_layout
from dupont.formats.circuit.exporter import export_circuit
from dupont.formats.circuit.importer import import_circuit
from dupont.formats.wokwi.importer import import_wokwi
from dupont.migrate import MigrationError, migrate_circuit, migrate_layout
from dupont.model.serialize import load_model
from dupont.render.breadboard import render_breadboard

_DIRECTIONS = ("import", "export", "convert", "check")
_FORMATS = ("circuit", "layout")


def main(argv: list[str] | None = None) -> int:
    """Dispatch a dupont CLI invocation. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="dupont", description=__doc__)
    parser.add_argument("direction", help="import | export | convert | check")
    parser.add_argument(
        "--project", required=True, type=Path, help="directory scanned recursively"
    )
    parser.add_argument(
        "--format", default="circuit", help="source format (A1 supports: circuit)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="promote warning-severity findings to errors"
    )
    args = parser.parse_args(argv)

    if args.direction not in _DIRECTIONS:
        print(
            f"unsupported direction {args.direction!r}; "
            f"supported: {', '.join(_DIRECTIONS)}",
            file=sys.stderr,
        )
        return 2
    if args.format not in _FORMATS:
        print(
            f"unsupported format {args.format!r}; supported: {', '.join(_FORMATS)}",
            file=sys.stderr,
        )
        return 2
    if not args.project.is_dir():
        print(f"--project is not a directory: {args.project}", file=sys.stderr)
        return 2

    if args.direction == "import":
        if args.format == "layout":
            return _do_import_layout(args.project)
        return _do_import(args.project)
    if args.direction == "convert":
        return _do_convert(args.project)
    if args.direction == "check":
        return _do_check(args.project, args.strict)
    if args.format == "layout":
        return _do_export_layout(args.project)
    return _do_export(args.project)


def _do_import(project: Path) -> int:
    circuits = sorted(project.rglob("circuit.yaml"))
    if not circuits:
        print(f"no circuit.yaml found under {project}", file=sys.stderr)
        return 1
    failed = False
    for source in circuits:
        try:
            written = migrate_circuit(source, source.parent)
            print(f"imported {written}")
        except MigrationError as exc:
            failed = True
            print(f"FAILED {exc.source}: {exc.schema_diff}", file=sys.stderr)
    return 1 if failed else 0


def _do_import_layout(project: Path) -> int:
    layouts = sorted(project.rglob("layout.yaml"))
    if not layouts:
        print(f"no layout.yaml found under {project}", file=sys.stderr)
        return 1
    failed = False
    for source in layouts:
        try:
            written = migrate_layout(source, source.parent)
            print(f"imported {written}")
        except MigrationError as exc:
            failed = True
            print(f"FAILED {exc.source}: {exc.schema_diff}", file=sys.stderr)
    return 1 if failed else 0


def _do_export_layout(project: Path) -> int:
    models = sorted(project.rglob("*.layout.model.yaml"))
    if not models:
        print(f"no *.layout.model.yaml found under {project}", file=sys.stderr)
        return 1
    failed = False
    for model in models:
        base = model.name[: -len(".layout.model.yaml")]
        # render() replaces the final suffix, so keep ".svg" in the stem to
        # preserve the ".layout" segment; it writes <base>.layout.svg + .png.
        stem = model.parent / f"{base}.layout.svg"
        try:
            render_breadboard(load_model(model), stem)
            print(f"exported {stem}")
        except (ValueError, KeyError) as exc:
            failed = True
            print(f"FAILED {model}: {exc}", file=sys.stderr)
    return 1 if failed else 0


def _do_convert(project: Path) -> int:
    circuits = sorted(project.rglob("circuit.yaml"))
    if not circuits:
        print(f"no circuit.yaml found under {project}", file=sys.stderr)
        return 1
    failed = False
    for source in circuits:
        out = source.parent / f"{source.parent.name}.convert.yaml"
        try:
            out.write_text(export_circuit(import_circuit(source)), encoding="utf-8")
            print(f"converted {out}")
        except (ValueError, KeyError) as exc:
            failed = True
            print(f"FAILED {source}: {exc}", file=sys.stderr)
    return 1 if failed else 0


def _do_check(project: Path, strict: bool) -> int:
    dual_format_dirs = [
        source.parent
        for source in sorted(project.rglob("circuit.yaml"))
        if (source.parent / "layout.yaml").exists()
    ]
    if not dual_format_dirs:
        print(f"no directory with both circuit.yaml and layout.yaml found under {project}", file=sys.stderr)
        return 1
    failed = False

    three_format_dirs = [d for d in dual_format_dirs if (d / "diagram.json").exists()]
    two_format_dirs = [d for d in dual_format_dirs if not (d / "diagram.json").exists()]

    for directory in three_format_dirs:
        try:
            schematic = import_circuit(directory / "circuit.yaml")
            breadboard = import_layout(directory / "layout.yaml")
            wokwi = import_wokwi(directory / "diagram.json")
            findings = check_three_format(schematic, breadboard, wokwi, strict=strict)
            records, summary = format_three_report(findings, strict)
        except (ValueError, KeyError) as exc:
            failed = True
            print(f"FAILED {directory}: {exc}", file=sys.stderr)
            continue
        print(summary)
        if any(record["severity"] == "error" for record in records):
            failed = True

    for directory in two_format_dirs:
        try:
            schematic = import_circuit(directory / "circuit.yaml")
            breadboard = import_layout(directory / "layout.yaml")
            findings = check_connectivity(schematic, breadboard)
            records, summary = format_report(findings, strict)
        except (ValueError, KeyError) as exc:
            failed = True
            print(f"FAILED {directory}: {exc}", file=sys.stderr)
            continue
        print(summary)
        if any(record["severity"] == "error" for record in records):
            failed = True
    return 1 if failed else 0


def _do_export(project: Path) -> int:
    # Exclude layout models: "*.model.yaml" also matches "*.layout.model.yaml",
    # whose MCU pins are not gpio-typed and would fail export_circuit.
    models = sorted(
        m
        for m in project.rglob("*.model.yaml")
        if not m.name.endswith(".layout.model.yaml")
    )
    if not models:
        print(f"no *.model.yaml found under {project}", file=sys.stderr)
        return 1
    failed = False
    for model in models:
        base = model.name[: -len(".model.yaml")]
        out = model.parent / f"{base}.circuit.yaml"
        try:
            out.write_text(export_circuit(load_model(model)), encoding="utf-8")
            print(f"exported {out}")
        except (ValueError, KeyError) as exc:
            failed = True
            print(f"FAILED {model}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
