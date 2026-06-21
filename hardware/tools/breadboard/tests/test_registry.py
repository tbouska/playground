"""Contract tests for the self-registering component drawer registry.

Exercises the public API exposed as ``from breadboard.components import
register, get_drawer``. These tests treat the registry purely as a USER: a
drawer is any callable, registered under one or more kind names, and looked up
by kind. Fake kind names (``test_*``) are used so registrations never collide
with the real component kinds that share the same process-wide registry.
"""

from breadboard.components import get_drawer, register


def test_register_returns_drawer_unchanged() -> None:
    # @register(...) is a decorator factory: applied to a drawer it must hand
    # back the SAME function object, so the decorated name stays callable.
    def drawer() -> str:
        return "drawn"

    decorated = register("test_widget_xyz")(drawer)

    assert decorated is drawer
    assert decorated() == "drawn"


def test_get_drawer_returns_registered_drawer() -> None:
    @register("test_alpha")
    def drawer() -> None:
        return None

    assert get_drawer("test_alpha") is drawer


def test_get_drawer_returns_none_for_unregistered_kind() -> None:
    assert get_drawer("test_never_registered_kind") is None


def test_register_multiple_kinds_maps_all_to_same_drawer() -> None:
    @register("test_alpha2", "test_beta2")
    def drawer() -> None:
        return None

    assert get_drawer("test_alpha2") is drawer
    assert get_drawer("test_beta2") is drawer


def test_crystal_kind_resolves() -> None:
    assert get_drawer("crystal") is not None


def test_inductor_kind_resolves() -> None:
    assert get_drawer("inductor") is not None
