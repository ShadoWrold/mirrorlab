"""Guard: every cell's loader ground truth IS its registered ``spec.law``.

The loader builds the scored grid GT and the oracle wraps ``spec.law``. If the
two ever computed the break formula differently, the bench ceiling would be
measured against a different law than the agents see. This test replays every
sub-grid point through ``spec.law`` and asserts bit-parity with the stored GT:

  (a)/(b)  GT == spec.law(inputs, sim.params)
  (c)      GT == spec.law(inputs, cf_params[i])     # third tuple element

This is the invariant that lets the loaders delegate their GT to ``spec.law``
instead of re-implementing each break formula inline (single source of truth).
"""

from __future__ import annotations

import math

import pytest

from mirrorlab.scenarios.loader import load
from mirrorlab.scenarios.registry import REGISTRY
from mirrorlab.spec import get_cell, has_cell

# Hooke keeps the legacy ndarray grid form (see test_loader_hooke.py); its GT
# path is intentionally not the (inputs_dict, gt) tuple shape replayed here.
_PAIRS = sorted(
    (d, s) for (d, s) in REGISTRY.keys() if d != "hooke" and has_cell(d, s)
)

_TOL = 1e-9


def _close(got: float, gt: float) -> bool:
    got, gt = float(got), float(gt)
    if math.isnan(got) or math.isnan(gt):
        return math.isnan(got) and math.isnan(gt)
    return abs(got - gt) <= _TOL + _TOL * abs(gt)


@pytest.mark.parametrize("domain_id,shift_id", _PAIRS)
def test_loader_gt_equals_spec_law(domain_id: str, shift_id: str) -> None:
    sc = load(domain_id, shift_id, seed=0)
    spec = get_cell(domain_id, shift_id)
    base = sc.sim.params

    for sub in ("a", "b", "c"):
        for i, entry in enumerate(sc.test_grids[sub]):
            inputs, gt = entry[0], entry[1]
            params = entry[2] if (sub == "c" and len(entry) == 3) else base
            got = spec.law(inputs, params)
            assert _close(got, gt), (
                f"{(domain_id, shift_id)}/{sub}[{i}] loader GT {gt!r} != "
                f"spec.law {got!r} at inputs {inputs}"
            )
