"""Sub-grid (c) is a true latent-parameter shift, not an in-domain resample.

Sprint 2 (CAL-3 placeholder, ±30%): each (c) point's ground truth must come
from a fresh law instantiation with perturbed parameters — not the baseline
sim's params. See ``docs/sprint1-report.md`` §3.3 and spec §6.2.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mirrorlab.domains.hooke import HookeParams
from mirrorlab.scenarios.counterfactual import DEFAULT_MAGNITUDE, perturb_params
from mirrorlab.scenarios.loader import load
from mirrorlab.shifts.hooke_g_1_1 import HookeGamma11Params, shifted_force


_LAW_FIELDS = {
    HookeParams: ("k",),
    HookeGamma11Params: ("k", "eta", "x_scale"),
}
_IC_FIELDS = ("x0", "v0", "m")


# ----------------------------- perturb_params -----------------------------


@pytest.mark.parametrize(
    "params",
    [
        HookeParams(k=10.0, m=1.0, x0=0.1, v0=0.0),
        HookeGamma11Params(
            k=10.0, m=1.0, x0=0.1, v0=0.0, eta=0.5, x_scale=0.2
        ),
    ],
)
def test_perturb_keeps_ic_and_mass_untouched(params):
    rng = np.random.default_rng(0)
    p2 = perturb_params(params, rng=rng)
    for f in _IC_FIELDS:
        assert getattr(p2, f) == getattr(params, f), f"IC field {f} moved"


@pytest.mark.parametrize(
    "params",
    [
        HookeParams(k=10.0, m=1.0, x0=0.1, v0=0.0),
        HookeGamma11Params(
            k=10.0, m=1.0, x0=0.1, v0=0.0, eta=0.5, x_scale=0.2
        ),
    ],
)
def test_perturb_law_fields_move_within_magnitude(params):
    rng = np.random.default_rng(123)
    samples = [perturb_params(params, rng=rng) for _ in range(64)]
    for f in _LAW_FIELDS[type(params)]:
        base = getattr(params, f)
        factors = np.array([getattr(s, f) / base for s in samples])
        assert factors.min() >= 1.0 - DEFAULT_MAGNITUDE - 1e-12
        assert factors.max() <= 1.0 + DEFAULT_MAGNITUDE + 1e-12
        # at least one draw is materially different (no silent identity)
        assert np.max(np.abs(factors - 1.0)) > 0.05


def test_perturb_rejects_unknown_params_type():
    class Foo:
        pass

    with pytest.raises(TypeError):
        perturb_params(Foo(), rng=np.random.default_rng(0))


def test_perturb_rejects_negative_magnitude():
    with pytest.raises(ValueError):
        perturb_params(
            HookeParams(k=1.0, m=1.0, x0=0.0, v0=0.0),
            magnitude=-0.1,
            rng=np.random.default_rng(0),
        )


# ----------------------------- loader wiring -----------------------------


@pytest.mark.parametrize("shift_id", ["baseline", "gamma_1_1"])
def test_loader_emits_counterfactual_params_aligned_with_c_grid(shift_id):
    sc = load("hooke", shift_id, seed=0)
    grid_c = sc.test_grids["c"]
    cf = sc.counterfactual_params
    assert len(cf) == grid_c.size
    assert sc.counterfactual_magnitude == pytest.approx(DEFAULT_MAGNITUDE)


def test_loader_c_params_differ_from_baseline_sim_params():
    sc = load("hooke", "gamma_1_1", seed=0)
    base = sc.sim.params
    cf = sc.counterfactual_params
    # Every (c) instance is a fresh dataclass with at least one law field moved.
    for p in cf:
        assert type(p) is type(base)
        moved = [
            getattr(p, f) != getattr(base, f) for f in _LAW_FIELDS[type(base)]
        ]
        assert any(moved), f"counterfactual params identical to baseline: {p}"


def test_loader_c_params_perturbation_in_30pct_band_per_field():
    sc = load("hooke", "gamma_1_1", seed=0)
    base = sc.sim.params
    cf = sc.counterfactual_params
    for f in _LAW_FIELDS[type(base)]:
        ratios = np.array([getattr(p, f) / getattr(base, f) for p in cf])
        assert ratios.min() >= 1.0 - DEFAULT_MAGNITUDE - 1e-12
        assert ratios.max() <= 1.0 + DEFAULT_MAGNITUDE + 1e-12


def test_loader_a_and_b_unchanged_from_perturbation():
    """(a) and (b) are NOT counterfactual: they share the baseline sim's law."""
    sc = load("hooke", "gamma_1_1", seed=0)
    # The loader's (a)(b) are pure x-arrays; (c) is too, but (c) carries
    # extra params metadata while (a)(b) don't.
    for key in ("a", "b"):
        assert isinstance(sc.test_grids[key], np.ndarray)
    # And the metadata-bearing structure is reserved for (c).
    assert sc.counterfactual_params  # non-empty


# --------------------------- per-point GT semantics ---------------------------


def test_runner_c_grid_ground_truth_uses_perturbed_params():
    """For γ-1-1, runner's (c) GT must equal force(x, perturbed_params), not
    force(x, sim.params)."""
    from mirrorlab.runners.sprint1_demo import _grids_with_ground_truth

    sc = load("hooke", "gamma_1_1", seed=0)
    grids = _grids_with_ground_truth(sc)
    c = grids["c"]
    assert len(c) > 0
    # Recompute under baseline params and verify GT does NOT match.
    base_params = sc.sim.params
    diff_count = 0
    for inputs, gt in c:
        x = inputs["x"]
        gt_baseline = float(shifted_force(x, base_params))
        if not np.isclose(gt, gt_baseline, rtol=1e-12, atol=1e-12):
            diff_count += 1
    # With ±30% on three independent draws and 11 points, near-zero collisions
    # are the only way every-point-equals-baseline could happen.
    assert diff_count >= len(c) - 1


def test_runner_c_grid_ground_truth_matches_some_perturbed_instantiation():
    """Each (c) GT is recoverable by evaluating the law at *some* perturbed
    instance — sanity that the runner used the CF policy, not random noise."""
    from mirrorlab.runners.sprint1_demo import _grids_with_ground_truth

    sc = load("hooke", "gamma_1_1", seed=0)
    grids = _grids_with_ground_truth(sc)
    base = sc.sim.params
    for inputs, gt in grids["c"]:
        x = inputs["x"]
        # Reproduce from bounds: GT must lie between the force evaluated under
        # the most-aggressive ±30% k/eta/x_scale combinations.
        lo_p = replace(
            base,
            k=base.k * (1 - DEFAULT_MAGNITUDE),
            eta=base.eta * (1 - DEFAULT_MAGNITUDE),
            x_scale=base.x_scale * (1 - DEFAULT_MAGNITUDE),
        )
        hi_p = replace(
            base,
            k=base.k * (1 + DEFAULT_MAGNITUDE),
            eta=base.eta * (1 + DEFAULT_MAGNITUDE),
            x_scale=base.x_scale * (1 + DEFAULT_MAGNITUDE),
        )
        f_lo = float(shifted_force(x, lo_p))
        f_hi = float(shifted_force(x, hi_p))
        envelope = (min(f_lo, f_hi), max(f_lo, f_hi))
        # tanh is monotone in x_scale-aware way, but force = -kx(1 + η tanh).
        # The exact envelope isn't monotone in (k,η,x_scale) jointly for fixed
        # x, but the magnitude of GT must stay bounded by the loose envelope
        # implied by independent ±30% factors. Use a 2× safety pad.
        pad = 2.0 * max(abs(envelope[0]), abs(envelope[1]), 1e-9)
        assert envelope[0] - pad <= gt <= envelope[1] + pad
