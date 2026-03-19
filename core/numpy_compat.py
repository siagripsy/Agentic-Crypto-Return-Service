"""Compatibility helpers for loading legacy NumPy-backed pickle artifacts."""

from __future__ import annotations

import importlib
import sys


def _alias_module(alias: str, target: str) -> None:
    """Register an import alias if the target module is available."""
    if alias in sys.modules:
        return

    try:
        sys.modules[alias] = importlib.import_module(target)
    except Exception:
        # Best-effort shim only; callers still get the real load error if aliasing is insufficient.
        return


def setup_numpy_compatibility() -> None:
    """
    Install compatibility shims for older pickles.

    Some previously saved artifacts reference private NumPy module paths such as
    ``numpy._core`` or legacy ``numpy.random`` internals. Newer/older runtimes
    may expose slightly different import paths, so we register lightweight
    aliases before unpickling.
    """
    import numpy.random as nr

    # Map private/core module paths across NumPy versions.
    module_aliases = {
        "numpy._core": "numpy.core",
        "numpy._core.multiarray": "numpy.core.multiarray",
        "numpy._core.numeric": "numpy.core.numeric",
        "numpy._core.numerictypes": "numpy.core.numerictypes",
        "numpy._core.umath": "numpy.core.umath",
        "numpy._core._multiarray_umath": "numpy.core._multiarray_umath",
    }

    for alias, target in module_aliases.items():
        _alias_module(alias, target)

    class MT19937:
        """Fallback MT19937 stub for legacy pickles."""

        def __init__(self):
            self.state = None

    class RandomState:
        """Fallback RandomState stub for legacy pickles."""

        def __init__(self):
            self.state = None

    class Generator:
        """Fallback Generator stub for legacy pickles."""

        def __init__(self):
            self.bit_generator = None

    if not hasattr(nr, "MT19937"):
        nr.MT19937 = MT19937
    if not hasattr(nr, "RandomState"):
        nr.RandomState = RandomState
    if not hasattr(nr, "Generator"):
        nr.Generator = Generator

    numpy_random_module = sys.modules.get("numpy.random")
    if numpy_random_module:
        if not hasattr(numpy_random_module, "MT19937"):
            numpy_random_module.MT19937 = MT19937
        if not hasattr(numpy_random_module, "RandomState"):
            numpy_random_module.RandomState = RandomState
        if not hasattr(numpy_random_module, "Generator"):
            numpy_random_module.Generator = Generator


if __name__ == "__main__":
    setup_numpy_compatibility()
    print("NumPy compatibility patching activated")
