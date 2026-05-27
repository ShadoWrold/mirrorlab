"""Per-(domain_id, shift_id) test-grid builder dispatch.

Blueprint-xy §3.1/§3.2: dispatch moved from per-``domain_id`` (which made
every shift share a baseline-form GT closure — root cause of the BLOCKER
documented in docs/blocker-consensus.md) to per-``(domain_id, shift_id)``.
This module owns the dispatch table; the per-shift truth-form builders
are added incrementally (T3+ in the implementation DAG, blueprint §5).

Until each shift gets its own truth-form builder, the dispatch entry for
that (domain, shift) key falls back to the legacy per-domain builder
imported from ``mirrorlab.scenarios.loader``. This keeps behavior bit-
identical to pre-T2 while enabling per-shift override at a single key.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

# Builder signature: (sim, seed, magnitude) -> (test_grids_dict, cf_params_tuple)
GridBuilder = Callable[[Any, int, float], tuple]

# Registry of registered (domain_id, shift_id) → builder. Populated by
# ``register_legacy_dispatch`` at import time (below) so the new dispatch
# table is non-empty even before any truth-form builder is shipped.
_GRID_BUILDERS: Dict[Tuple[str, str], GridBuilder] = {}


def register(domain_id: str, shift_id: str, builder: GridBuilder) -> None:
    """Register or replace the grid builder for a single (domain, shift) pair.

    Per-shift truth-form builders (T3+) call this from their module's
    import to override the legacy fallback for their key only.
    """
    _GRID_BUILDERS[(domain_id, shift_id)] = builder


def get(domain_id: str, shift_id: str) -> GridBuilder:
    """Return the builder for ``(domain_id, shift_id)``.

    Raises ``KeyError`` if the dispatch table does not have an entry. The
    legacy-fallback registration in ``register_legacy_dispatch`` ensures
    every key in ``mirrorlab.scenarios.registry.REGISTRY`` is covered, so
    a ``KeyError`` here indicates a registry / dispatch drift bug.
    """
    return _GRID_BUILDERS[(domain_id, shift_id)]


def register_legacy_dispatch() -> None:
    """Populate ``_GRID_BUILDERS`` with the pre-XY per-domain builders.

    Walks ``mirrorlab.scenarios.registry.REGISTRY`` and binds each non-
    hooke (domain, shift) key to the matching legacy
    ``_<domain>_test_grids`` closure from ``mirrorlab.scenarios.loader``.
    Hooke is skipped: it uses its own Sprint-1 ndarray path
    (``_hooke_test_grids``) gated directly in ``load()``.

    Uses ``setdefault`` so a per-shift truth-form builder that registered
    earlier (T3+, via ``register(...)`` from its own import) is never
    clobbered by the legacy fallback. Called once at the bottom of
    ``loader.py`` after ``_NON_HOOKE_GRID_BUILDERS`` is defined.
    """
    # Imported lazily to avoid a circular import (loader.py imports this
    # package at module load).
    from mirrorlab.scenarios import loader as _legacy
    from mirrorlab.scenarios.registry import REGISTRY

    for (domain_id, shift_id) in REGISTRY:
        if domain_id == "hooke":
            continue
        builder = _legacy._NON_HOOKE_GRID_BUILDERS.get(domain_id)
        if builder is None:
            continue
        _GRID_BUILDERS.setdefault((domain_id, shift_id), builder)


__all__ = [
    "GridBuilder",
    "register",
    "get",
    "register_legacy_dispatch",
    "_GRID_BUILDERS",
]
