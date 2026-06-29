"""dupont CLI: convert between ``circuit.yaml`` and the interchange model.

A1 supports circuit<->circuit round-trip and circuit->model-schema conversion
only::

    dupont import  --project <dir>   # each circuit.yaml -> <dir>.model.yaml
    dupont export  --project <dir>   # each *.model.yaml -> <name>.circuit.yaml
    dupont convert --project <dir>   # each circuit.yaml -> <dir>.convert.yaml
                                     #   (import then export round-trip)

``--project`` is scanned recursively. Any other direction or ``--format`` fails
loud listing the supported set, so A2/A3 surfaces (check, layout, wokwi) report
an explicit "not supported" error rather than silently doing nothing. All
outputs are written beside their source under new names; no source file is
overwritten.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dupont.formats.circuit.exporter import export_circuit
from dupont.formats.circuit.importer import import_circuit
from dupont.migrate import migrate_circuits
from dupont.model.serialize import load_model

_DIRECTIONS = ("import", "export", "convert")
_FORMATS = ("circuit",)


def main(argv: list[str] | None = None) -> int:
    """Dispatch a dupont CLI invocation. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="dupont", description=__doc__)
    parser.add_argument("direction", help="import | export | convert")
    parser.add_argument(
        "--project", required=True, type=Path, help="directory scanned recursively"
    )
    parser.add_argument(
        "--format", default="circuit", help="source format (A1 supports: circuit)"
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
        return _do_import(args.project)
    if args.direction == "convert":
        return _do_convert(args.project)
    return _do_export(args.project)


def _do_import(project: Path) -> int:
    circuits = sorted(project.rglob("circuit.yaml"))
    if not circuits:
        print(f"no circuit.yaml found under {project}", file=sys.stderr)
        return 1
    report = migrate_circuits(circuits, project)
    for path in report.migrated:
        print(f"imported {path}")
    for source, reason in report.failed:
        print(f"FAILED {source}: {reason}", file=sys.stderr)
    return 1 if report.failed else 0


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


def _do_export(project: Path) -> int:
    models = sorted(project.rglob("*.model.yaml"))
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
