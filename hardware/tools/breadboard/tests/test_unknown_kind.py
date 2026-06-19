"""Behavior test for the render loop meeting an unknown component kind.

A layout may carry a component kind the renderer does not recognise. The
contract: the render loop logs a WARNING note naming the unknown kind, skips
that component, and still renders the rest of the layout (no exception).

The layout is built directly from ``breadboard.model`` objects rather than a
YAML fixture so the test depends on nothing beyond the model and the render
entry point. The resistor mirrors the known instance in
``fixtures/all_components.yaml`` (value "220", two legs).
"""

import logging

import render_layout
from breadboard import model


def _layout_with_one_known_and_one_unknown() -> model.Layout:
    known = model.Component(kind="resistor", ref="R1", value="220", legs=("A2", "A4"))
    unknown = model.Component(kind="frobnicator", ref="X1", legs=("B2", "B4"))
    return model.Layout(title="unknown kind", columns=25, components=(known, unknown))


def test_render_logs_warning_for_unknown_kind(tmp_path, caplog) -> None:
    layout = _layout_with_one_known_and_one_unknown()
    out_stem = tmp_path / "unknown_kind"

    with caplog.at_level(logging.WARNING, logger="breadboard"):
        render_layout.render(layout, out_stem)

    warnings = [
        r.getMessage()
        for r in caplog.records
        if r.levelno >= logging.WARNING and "unknown component kind" in r.getMessage()
    ]
    # Exactly one unknown-kind warning: the layout has one unknown component.
    # More than one means the renderer also warns on the KNOWN resistor.
    assert len(warnings) == 1, (
        "expected exactly one WARNING containing 'unknown component kind' "
        "(the single 'frobnicator' component); "
        f"got: {warnings}"
    )
    # The warning must name the UNKNOWN kind specifically, not fire generically.
    assert "frobnicator" in warnings[0], (
        "expected the 'unknown component kind' WARNING to name the unknown kind "
        f"'frobnicator'; got: {warnings[0]!r}"
    )
    # The KNOWN kind must stay silent: no unknown-kind warning may mention it.
    assert not any("resistor" in w for w in warnings), (
        "the known 'resistor' kind must not trigger an 'unknown component kind' "
        f"WARNING; got: {warnings}"
    )


def test_render_skips_unknown_but_still_renders_known(tmp_path, caplog) -> None:
    # An unknown kind must not abort the render: the known resistor still draws
    # and the output file is written. This guards against a renderer that
    # "passes" the warning test by skipping (or failing on) everything.
    layout = _layout_with_one_known_and_one_unknown()
    out_stem = tmp_path / "unknown_kind_output"

    with caplog.at_level(logging.WARNING, logger="breadboard"):
        render_layout.render(layout, out_stem)

    svg_path = out_stem.with_suffix(".svg")
    assert svg_path.exists(), f"render() did not write {svg_path}"
    assert svg_path.stat().st_size > 0
