"""Common helpers shared by per-(domain, shift) grid builders.

Extracted from ``mirrorlab.scenarios.loader`` per blueprint-xy §3.1/§3.2:
each shift's truth-form GT lives in its own module under
``mirrorlab/scenarios/loader_shifts/``, and they all share the scaffolding
here (sub-grid layout, OOD ranges, parameter introspection, ``_pack``).

Sub-grid contract (post-XY, blueprint-xy §2.3):
- ``(a)`` and ``(b)`` are lists of ``(inputs_dict, gt_scalar)`` 2-tuples.
- ``(c)`` is a list of ``(inputs_dict, gt_scalar, cf_params_obj)`` 3-tuples
  so the evaluator can override declared predictor params per point
  with the matching counterfactual perturbation.

Each per-shift builder is a function ``builder(sim, seed, magnitude) ->
(test_grids: dict, cf_params: tuple)`` that calls ``_pack`` with a
``build(rng, mode) -> list[(inputs_dict, gt_fn)]`` closure. ``gt_fn(params)``
returns the scalar ground truth for the per-point inputs at the supplied
params object.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from mirrorlab.scenarios.counterfactual import perturb_params

# Test-grid sizing — CAL-1 (sub-grid weight 0.20/0.40/0.40) and CAL-2
# (OOD spans 5x the in-domain amplitude) defaults.
_GRID_SIZE = 11
_OOD_FACTOR = 5.0


def _attr(p: Any, names: Sequence[str], default: float) -> float:
    """Return the first finite float attribute of ``p`` named in ``names``.

    Falls back to ``default`` if no listed attribute exists or none yields
    a finite float. Used to look up parameter values across name variants
    (e.g. ``("G", "G0")`` to accept either baseline ``G`` or the γ-shift's
    ``G0`` field).
    """
    for n in names:
        if hasattr(p, n):
            try:
                v = float(getattr(p, n))
                if math.isfinite(v):
                    return v
            except (TypeError, ValueError):
                continue
    return float(default)


def _linspace_signed(amp: float, n: int) -> np.ndarray:
    """Symmetric ``n``-point grid spanning ``[-amp, +amp]``."""
    return np.linspace(-amp, amp, n)


def _ood_signed(amp: float, n: int) -> np.ndarray:
    """Symmetric OOD grid covering ``±[1.5·amp, _OOD_FACTOR·amp]``.

    Half the points fall on each side; ``max(1, n // 2)`` so callers with
    odd ``n`` still get at least one point per branch.
    """
    half = max(1, n // 2)
    return np.concatenate(
        [
            np.linspace(-_OOD_FACTOR * amp, -1.5 * amp, half),
            np.linspace(1.5 * amp, _OOD_FACTOR * amp, n - half),
        ]
    )


def _pack(rng_seed: int, magnitude: float, sim: Any, build: Any) -> Tuple[
    Dict[str, List[Any]], Tuple[Any, ...]
]:
    """Materialize ``(a, b, c)`` sub-grids from a domain-supplied ``build``.

    ``build(rng, mode)`` returns a list of ``(inputs_dict, gt_fn)`` pairs
    where ``gt_fn(params)`` returns the scalar ground truth at the inputs.
    Modes are ``"a"`` (in-domain), ``"b"`` (OOD), ``"c"`` (mirror of a).

    Counterfactual sub-grid (c) reuses (a)'s input points and perturbs the
    sim's params per point via ``perturb_params``. Each (c) tuple carries
    the perturbed params object as a third element so ``evaluate_entry``
    can override declared predictor params on a per-point basis (blueprint
    §2.3, Y plumbing).
    """
    rng_a = np.random.default_rng(rng_seed + 1)
    rng_b = np.random.default_rng(rng_seed + 3)
    cf_rng = np.random.default_rng(rng_seed + 2)
    pts_a = build(rng_a, "a")
    pts_b = build(rng_b, "b")
    pts_c_inputs = [ins for ins, _ in pts_a]
    cf_params = tuple(
        perturb_params(sim.params, magnitude=magnitude, rng=cf_rng)
        for _ in range(len(pts_c_inputs))
    )
    grid_a = [(ins, float(gt_fn(sim.params))) for ins, gt_fn in pts_a]
    grid_b = [(ins, float(gt_fn(sim.params))) for ins, gt_fn in pts_b]
    grid_c = [
        (ins, float(gt_fn(cf_params[i])), cf_params[i])
        for i, (ins, gt_fn) in enumerate(zip(pts_c_inputs, [g for _, g in pts_a]))
    ]
    return {"a": grid_a, "b": grid_b, "c": grid_c}, cf_params


__all__ = [
    "_GRID_SIZE",
    "_OOD_FACTOR",
    "_attr",
    "_linspace_signed",
    "_ood_signed",
    "_pack",
]
