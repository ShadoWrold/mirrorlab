"""Sub-grid (c) counterfactual override unit test (blueprint-xy §6.2).

Y plumbing intent: on counterfactual sub-grid (c), the per-point
``cf_params_obj`` carried in the 3-tuple ``(inputs, gt, cf_params_obj)``
must override the entry's declared params at evaluation time. A frozen-
coefficient submission that bakes its constants into a closure should
no longer auto-pass (c) — its declared values are overlaid by the
perturbed values from ``cf_params_obj`` per blueprint-xy §2.3.

This test exercises that contract end-to-end via ``evaluate_entry``,
with a controlled 3-tuple grid where the override is the only way to
match the ground truth.
"""

from __future__ import annotations

import math

import pytest

from mirrorlab.eval.numeric import (
    SUBGRID_WEIGHTS,
    TAU_DEFAULT,
    evaluate_entry,
)
from mirrorlab.scenarios.counterfactual import (
    params_to_predictor_kwargs,
    _PREDICTOR_NAME_MAP,
)


# ---------------------------------------------------------------------------
# 1. Bijection (blueprint-xy §2.5 step-5 round-trip property).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("params_type,name_map", list(_PREDICTOR_NAME_MAP.items()))
def test_predictor_name_map_is_bijection(params_type, name_map):
    canonical_names = list(name_map.values())
    assert len(set(canonical_names)) == len(canonical_names), (
        f"{params_type.__name__}: predictor-facing names collide: {canonical_names}"
    )


# ---------------------------------------------------------------------------
# 2. params_to_predictor_kwargs basic shapes.
# ---------------------------------------------------------------------------

def test_params_to_predictor_kwargs_renames_G0_to_G():
    from mirrorlab.shifts.gravity_g_2_1 import GravityGamma21Params
    p = GravityGamma21Params(G0=7e-11, M=1.0e21, m=1.0, xi=0.05,
                              nx=0.0, ny=0.0, nz=1.0,
                              x0=1.0e7, y0=0.0, z0=0.0,
                              vx0=0.0, vy0=0.0, vz0=0.0)
    out = params_to_predictor_kwargs(p)
    assert math.isclose(out["G"], 7e-11)
    assert math.isclose(out["M"], 1.0e21)
    assert math.isclose(out["xi"], 0.05)
    assert "G0" not in out  # renamed
    assert "m" not in out  # m is a mass (BC), not a law coefficient
    # Direction / IC fields are not law coefficients either.
    assert "nx" not in out
    assert "x0" not in out


def test_params_to_predictor_kwargs_idempotent_on_dict():
    d = {"G": 6.67e-11, "M": 1.0e21}
    out = params_to_predictor_kwargs(d)
    assert out == d


def test_params_to_predictor_kwargs_skips_non_finite():
    d = {"G": 6.67e-11, "M": float("nan"), "k": float("inf")}
    out = params_to_predictor_kwargs(d)
    assert "G" in out
    assert "M" not in out
    assert "k" not in out


# ---------------------------------------------------------------------------
# 3. Y plumbing contract: declared params vs cf overrides.
# ---------------------------------------------------------------------------

class _FakeParams:
    """Minimal stand-in that mimics a registered Params dataclass."""

    def __init__(self, G):
        self.G = G


def _make_entry_with_declared_G(declared_G: float):
    return {
        "predictor": {
            "lang": "python",
            "code": "def f(r, G, M=1.0, m=1.0): return -G*M*m/(r*r)",
        },
        "params": [
            {"name": "G", "value": declared_G},
            {"name": "M", "value": 1.0e21},
            {"name": "m", "value": 1.0},
        ],
    }


def _make_grids(declared_G_for_a: float, cf_G_for_c: float):
    """Construct a synthetic grid where (a) and (c) use the same r, but the
    ground truth on (c) is computed with ``cf_G_for_c`` (overriding the
    declared G)."""
    r = 5.0e6
    gt_a = -declared_G_for_a * 1.0e21 * 1.0 / (r * r)
    gt_c = -cf_G_for_c * 1.0e21 * 1.0 / (r * r)
    return {
        "a": [({"r": r}, gt_a)],
        "b": [({"r": r}, gt_a)],
        "c": [({"r": r}, gt_c, _FakeParams(cf_G_for_c))],
    }


def test_cf_params_override_declared_params_on_c():
    """On (c), the per-point cf_params object must supersede declared G.

    With declared G = 7e-11 but cf G = 1.4e-10, a predictor that uses the
    cf value to compute its output will match the (c) ground truth exactly.
    If Y plumbing is broken (declared G silently wins), the (c) RMSE
    blows up — and via exp(-r/tau) the score collapses near 0 on (c).
    """
    # Register _FakeParams on the predictor name map so the helper finds it.
    _PREDICTOR_NAME_MAP[_FakeParams] = {"G": "G"}
    try:
        declared_G = 7e-11
        cf_G = 1.4e-10  # 2x the declared value
        entry = _make_entry_with_declared_G(declared_G)
        grids = _make_grids(declared_G, cf_G)
        s = evaluate_entry(entry, grids)
        # If cf-override works, predictor on (c) used cf_G → matches gt_c
        # exactly. (a) and (b) match gt_a exactly with declared_G. Score → 1.0.
        assert s > 0.99, (
            f"expected near-perfect score with working Y plumbing, got {s}; "
            f"declared G={declared_G}, cf G={cf_G}"
        )
    finally:
        del _PREDICTOR_NAME_MAP[_FakeParams]


def test_declared_params_win_when_no_cf_object():
    """Legacy 2-tuple in (c) → no cf object → declared params are used.

    This preserves Sprint-1 behavior for grids that have not been ported
    to the 3-tuple shape yet (defensive backward-compat per the
    `len(point) == 2` branch in evaluate_entry).
    """
    declared_G = 7e-11
    entry = _make_entry_with_declared_G(declared_G)
    # (c) emits a legacy 2-tuple; GT computed with the same declared G so
    # a no-override predictor matches it exactly.
    r = 5.0e6
    gt = -declared_G * 1.0e21 * 1.0 / (r * r)
    grids = {
        "a": [({"r": r}, gt)],
        "b": [({"r": r}, gt)],
        "c": [({"r": r}, gt)],  # 2-tuple — no cf object
    }
    s = evaluate_entry(entry, grids)
    assert s > 0.99


def test_subgrid_c_rejects_scalar_point():
    """A bare scalar (e.g. numpy ndarray of floats) on (c) raises."""
    entry = _make_entry_with_declared_G(7e-11)
    grids = {"a": [({"r": 1.0}, 1.0)], "c": [1.0, 2.0, 3.0]}
    with pytest.raises(TypeError, match="2- or 3-tuple"):
        evaluate_entry(entry, grids)


# ---------------------------------------------------------------------------
# 4. Real loader integration — gravity baseline (c) gets a real cf object.
# ---------------------------------------------------------------------------

def test_loader_grid_c_is_3_tuple_for_non_hooke_baseline():
    """Spot-check that the new _pack signature actually shipped: every
    non-hooke baseline now emits a 3-tuple on (c) with a Params object.
    """
    from mirrorlab.scenarios.loader import load
    from mirrorlab.domains.gravity import GravityParams

    sc = load("gravity", "baseline", seed=0)
    grid_c = sc.test_grids["c"]
    assert len(grid_c) > 0
    first = grid_c[0]
    assert isinstance(first, tuple)
    assert len(first) == 3
    ins, gt, cf = first
    assert isinstance(ins, dict)
    assert math.isfinite(float(gt))
    assert isinstance(cf, GravityParams)
