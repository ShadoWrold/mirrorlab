"""Counterfactual parameter perturbation (CAL-3).

Per spec §6.2 sub-grid (c) and ``docs/sprint1-report.md`` §3.3 'Known gaps':
the counterfactual sub-grid must defeat frozen-coefficient curve-fits by
re-instantiating the *physical law* with shifted free parameters at every
test point. Curve-fits whose coefficients are locked to the probe sim cannot
follow a re-instantiated law; a real physical theory re-evaluates and tracks.

Perturbation policy (CAL-3 default, ±30%): each numeric law parameter is
scaled by an independent factor ``1 + U(-magnitude, +magnitude)``. Initial
conditions and mass are *not* law parameters and are left untouched — only
the free coefficients of the shift / baseline force law move.

Sprint 3 will calibrate the magnitude (CAL-3). This module deliberately
ships the placeholder default.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from mirrorlab.domains.hooke import HookeParams
from mirrorlab.shifts.hooke_d_1_1 import HookeDelta11Params
from mirrorlab.shifts.hooke_g_1_1 import HookeGamma11Params
from mirrorlab.shifts.hooke_g_1_2 import HookeGamma12Params

DEFAULT_MAGNITUDE = 0.30  # CAL-3

# Per-type whitelist of law-parameter field names that may be perturbed.
# IC fields (x0/y0/v0/vx0/vy0) and mass (m) are excluded by construction.
# Extension protocol: each new domain's law-param dataclass lands here once
# its loader path is wired — the explicit registration is the audit trail
# that someone has thought through which coefficients are *law* vs *BC*.
_LAW_PARAM_FIELDS: dict[type, tuple[str, ...]] = {
    HookeParams: ("k",),
    HookeGamma11Params: ("k", "eta", "x_scale"),
    HookeGamma12Params: ("k0", "xi", "phi"),
    HookeDelta11Params: ("k", "c", "L"),
}


def _factor(rng: np.random.Generator, magnitude: float) -> float:
    return 1.0 + float(rng.uniform(-magnitude, magnitude))


def perturb_params(
    params: Any,
    *,
    magnitude: float = DEFAULT_MAGNITUDE,
    rng: np.random.Generator,
) -> Any:
    """Return a new params dataclass with law parameters scaled by ``1±magnitude``.

    Each law-parameter field gets an independent uniform factor in
    ``[1-magnitude, 1+magnitude]``. IC and mass fields are passed through
    unchanged.

    Raises ``TypeError`` if ``params`` is not a registered law-parameter
    dataclass — extending the whitelist is the explicit signal that a new
    domain has thought through *which* coefficients are the law's free
    parameters versus its boundary conditions.
    """
    if magnitude < 0:
        raise ValueError(f"magnitude must be non-negative; got {magnitude}")
    fields = _LAW_PARAM_FIELDS.get(type(params))
    if fields is None:
        raise TypeError(
            f"no counterfactual policy registered for {type(params).__name__}; "
            f"known: {[t.__name__ for t in _LAW_PARAM_FIELDS]}"
        )
    updates = {name: getattr(params, name) * _factor(rng, magnitude) for name in fields}
    return replace(params, **updates)


__all__ = ["DEFAULT_MAGNITUDE", "perturb_params"]
