"""Sprint-3 contract tests: 11 non-Hooke domains pack (a)/(b)/(c) test grids.

Per spec §6.2 sub-grids, ``ScenarioInstance.test_grids`` must hand the
evaluator three sub-grids of ``(inputs_dict, ground_truth)`` tuples. Sprint
1/2 only wired Hooke; this test guards the Sprint-3 expansion.

Hooke is handled separately (legacy ndarray form, intentionally not
refactored — see ``test_loader_hooke.py``).
"""

from __future__ import annotations

import math
from typing import Sequence

import pytest

from mirrorlab.scenarios.loader import load
from mirrorlab.scenarios.registry import REGISTRY

_NON_HOOKE_PAIRS = sorted(
    (d, s) for (d, s) in REGISTRY.keys() if d != "hooke"
)


def _is_packed_grid(grid, *, allow_cf: bool = False) -> bool:
    if not isinstance(grid, list) or not grid:
        return False
    for entry in grid:
        if not isinstance(entry, tuple):
            return False
        if allow_cf:
            if len(entry) not in (2, 3):
                return False
        else:
            if len(entry) != 2:
                return False
        ins, gt = entry[0], entry[1]
        if not isinstance(ins, dict):
            return False
        if not math.isfinite(float(gt)):
            return False
    return True


@pytest.mark.parametrize("domain_id,shift_id", _NON_HOOKE_PAIRS)
def test_test_grids_packed_and_non_empty(domain_id: str, shift_id: str) -> None:
    sc = load(domain_id, shift_id, seed=0)
    grids = sc.test_grids
    for key in ("a", "b", "c"):
        assert key in grids, f"{(domain_id, shift_id)} missing sub-grid {key!r}"
        assert _is_packed_grid(grids[key], allow_cf=(key == "c")), (
            f"{(domain_id, shift_id)} sub-grid {key!r} not packed correctly"
        )


@pytest.mark.parametrize("domain_id,shift_id", _NON_HOOKE_PAIRS)
def test_inputs_match_observables(domain_id: str, shift_id: str) -> None:
    """Each sub-grid's inputs_dict keys are a subset of the domain's observables.

    Output channel names (``F``, ``q``, ``rate`` …) are excluded because GT is
    the output, not an input.

    Post-XY exception: ROT shifts expand the grid input vocabulary to
    3-D ``{x, y, z}`` so the anisotropic correction is observable
    (blueprint §3.2 / §4). Prompts.py listing of observables is updated
    in a later task (T13); until then, accept ``x, y, z`` as allowed
    extras on shifts that have a truth-form builder registered.
    """
    sc = load(domain_id, shift_id, seed=0)
    obs = set(sc.observables) | set(sc.dim_signature.get("inputs", {}).keys())
    for key, grid in sc.test_grids.items():
        sample_keys = set(grid[0][0].keys())
        # Agent-stub predictors also declare derived inputs not in OBSERVABLES
        # (e.g. ``didt`` for RLC; ``p1``/``h1``/``h2``/``v1``/``v2`` for fluid).
        # Post-XY: ROT shifts add 3-D position keys; T_TRANS shifts add ``t``;
        # δ-5-1 charge dynamics expose charges {q1, q2} as inputs.
        allowed_extras = {
            "didt", "p1", "h1", "h2", "v1", "v2", "L", "T_hot", "T_cold",
            "x", "y", "z", "t", "q1", "q2", "dx", "dy", "dz",
            "theta_i", "theta_pol",
            "q_1", "q_2", "i_1", "i_2",
        }
        leaked = sample_keys - obs - allowed_extras
        assert not leaked, (
            f"{(domain_id, shift_id)}/{key}: inputs {sorted(leaked)} not in "
            f"observables {sorted(obs)}"
        )


@pytest.mark.parametrize("domain_id,shift_id", _NON_HOOKE_PAIRS)
def test_counterfactual_differs_from_in_domain(domain_id: str, shift_id: str) -> None:
    """(c) reuses (a)'s inputs but GT is recomputed under perturbed params.

    With CAL-3 default magnitude (±30%), at least one point must differ
    measurably. We require the L1 norm of GT differences across the sub-grid
    to be above a small epsilon; that proves perturb_params actually moved
    the law parameters that the GT formula depends on.
    """
    sc = load(domain_id, shift_id, seed=0)
    grid_a = sc.test_grids["a"]
    grid_c = sc.test_grids["c"]
    assert len(grid_a) == len(grid_c), (
        f"{(domain_id, shift_id)}: (a) len {len(grid_a)} != (c) len {len(grid_c)}"
    )
    # Inputs at index i must match between (a) and (c).
    for i, (entry_a, entry_c) in enumerate(zip(grid_a, grid_c)):
        ins_a, _ = entry_a[0], entry_a[1]
        ins_c, _ = entry_c[0], entry_c[1]
        assert ins_a == ins_c, (
            f"{(domain_id, shift_id)}: (c) input[{i}] differs from (a): "
            f"{ins_a} vs {ins_c}"
        )
    diff = sum(abs(a[1] - c[1]) for a, c in zip(grid_a, grid_c))
    a_scale = sum(abs(a[1]) for a in grid_a) or 1.0
    assert diff / a_scale > 1e-6, (
        f"{(domain_id, shift_id)}: (c) GT is identical to (a) (diff={diff!r}); "
        f"perturb_params did not move any field the GT formula depends on"
    )


@pytest.mark.parametrize("domain_id,shift_id", _NON_HOOKE_PAIRS)
def test_ood_grid_extends_beyond_in_domain(domain_id: str, shift_id: str) -> None:
    """The OOD sub-grid should reach inputs further out than the in-domain one.

    Spec CAL-2 sets a 5x sampling-range default. Concretely: the max |input|
    across (b) should exceed the max |input| across (a) for at least one
    input dimension. Allow exceptions for inputs that aren't naturally
    range-bounded (e.g. RLC i / didt sampling is uniform over [-amp, amp]).
    """
    sc = load(domain_id, shift_id, seed=0)
    grid_a = sc.test_grids["a"]
    grid_b = sc.test_grids["b"]
    keys = list(grid_a[0][0].keys())

    def _max_abs(grid: Sequence) -> dict:
        out = {k: 0.0 for k in keys}
        for ins, _ in grid:
            for k in keys:
                out[k] = max(out[k], abs(float(ins[k])))
        return out

    a_max = _max_abs(grid_a)
    b_max = _max_abs(grid_b)
    assert any(b_max[k] > 1.1 * a_max[k] + 1e-12 for k in keys), (
        f"{(domain_id, shift_id)}: OOD grid {b_max} not wider than in-domain "
        f"{a_max}"
    )


@pytest.mark.parametrize("domain_id,shift_id", _NON_HOOKE_PAIRS)
def test_counterfactual_params_match_c_grid_size(
    domain_id: str, shift_id: str
) -> None:
    """One perturbed-params tuple per (c) point — keeps ``s_scen`` accountable."""
    sc = load(domain_id, shift_id, seed=0)
    assert len(sc.counterfactual_params) == len(sc.test_grids["c"])
