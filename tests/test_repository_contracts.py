"""MODULE-078 - repository contract tests.

"Keep domain/repository/storage interfaces portable" (ADR-021) is only
a real guarantee if every `SQLAlchemy*Repository` actually implements
every method its `*Repository(Protocol)` declares - Python's structural
typing never checks this at import time, and a typo'd/missing method on
a new repository method would otherwise only surface the first time a
caller happens to exercise that exact method. This reflects over every
Protocol/impl pair automatically (by the `SQLAlchemy{Name}` naming
convention every repository in this codebase already follows) rather
than hand-listing all 26 pairs, so a new repository added later is
covered with zero extra test code.
"""

import inspect

import pytest

from xerama.repositories import interfaces, sqlalchemy_impl


def _discover_repository_protocols() -> list[tuple[str, type]]:
    return [
        (name, obj)
        for name, obj in vars(interfaces).items()
        if isinstance(obj, type) and name.endswith("Repository") and getattr(obj, "_is_protocol", False)
    ]


def _protocol_method_names(protocol_cls: type) -> list[str]:
    return [
        name
        for name, member in inspect.getmembers(protocol_cls)
        if not name.startswith("_") and inspect.isfunction(member)
    ]


_PROTOCOLS = _discover_repository_protocols()


def test_at_least_two_dozen_repository_protocols_were_discovered() -> None:
    """A canary for the discovery mechanism itself - if this drops to 0,
    `_is_protocol` reflection broke (e.g. a typing internals change),
    and every other test in this file would be silently vacuous."""
    assert len(_PROTOCOLS) >= 20


@pytest.mark.parametrize("protocol_name,protocol_cls", _PROTOCOLS, ids=[n for n, _ in _PROTOCOLS])
def test_sqlalchemy_impl_exists_for_every_protocol(protocol_name, protocol_cls) -> None:
    impl_name = f"SQLAlchemy{protocol_name}"
    assert hasattr(sqlalchemy_impl, impl_name), (
        f"{protocol_name} has no matching {impl_name} in sqlalchemy_impl.py"
    )


@pytest.mark.parametrize("protocol_name,protocol_cls", _PROTOCOLS, ids=[n for n, _ in _PROTOCOLS])
def test_sqlalchemy_impl_implements_every_protocol_method(protocol_name, protocol_cls) -> None:
    impl_cls = getattr(sqlalchemy_impl, f"SQLAlchemy{protocol_name}", None)
    if impl_cls is None:
        pytest.skip("covered by test_sqlalchemy_impl_exists_for_every_protocol")

    for method_name in _protocol_method_names(protocol_cls):
        impl_method = getattr(impl_cls, method_name, None)
        assert impl_method is not None, f"SQLAlchemy{protocol_name} is missing method {method_name!r}"
        assert callable(impl_method), f"SQLAlchemy{protocol_name}.{method_name} exists but is not callable"

        # Parameter *names* (not full type signatures - the Protocol
        # methods are declared with `...` bodies and no default values,
        # so comparing defaults/annotations would false-positive on
        # every impl that adds a sensible default) must match, so a
        # renamed/reordered/removed argument is caught rather than only
        # surfacing as a confusing TypeError at the first real call.
        protocol_params = list(inspect.signature(protocol_cls.__dict__[method_name]).parameters)
        impl_params = list(inspect.signature(impl_method).parameters)
        assert protocol_params == impl_params, (
            f"SQLAlchemy{protocol_name}.{method_name} parameters {impl_params} "
            f"don't match the Protocol's {protocol_params}"
        )
