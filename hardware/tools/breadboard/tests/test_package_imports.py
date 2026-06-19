"""Import-smoke tests for the breadboard package public surface.

Verifies that all public symbols are importable from their new module homes
and that the top-level package re-exports share object identity with the
submodule originals.
"""

import breadboard
import breadboard.geometry
import breadboard.model
import breadboard.style


def test_geometry_symbols_importable() -> None:
    from breadboard.geometry import Geometry, LINE_ORDER

    assert Geometry is not None
    assert LINE_ORDER is not None


def test_model_symbols_importable() -> None:
    from breadboard.model import Layout, Component, Pin

    assert Layout is not None
    assert Component is not None
    assert Pin is not None


def test_style_constants_importable() -> None:
    from breadboard.style import RENDER_DPI, HOLE_RADIUS, BOARD_COLOR

    assert RENDER_DPI is not None
    assert HOLE_RADIUS is not None
    assert BOARD_COLOR is not None


def test_package_exposes_version_string() -> None:
    assert isinstance(breadboard.__version__, str)


def test_package_reexports_share_identity() -> None:
    assert breadboard.Layout is breadboard.model.Layout
    assert breadboard.Component is breadboard.model.Component
    assert breadboard.Pin is breadboard.model.Pin
    assert breadboard.Geometry is breadboard.geometry.Geometry
