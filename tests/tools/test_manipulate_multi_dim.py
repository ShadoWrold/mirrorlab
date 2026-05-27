"""Multi-D manipulate-tool tests. Spec §4.1 / Task #2.

Exercises the v1 manipulate tools on 2-D / 3-D shift scenarios where the
params dataclass exposes vector ICs (``x0, y0, vx0, vy0, ...``) — the original
Hooke-1-D whitelist would reject these. Also keeps a 1-D Hooke smoke test for
back-compat.
"""

from __future__ import annotations

import dataclasses

import pytest

from mirrorlab.scenarios.loader import load
from mirrorlab.tools.registry import call
from mirrorlab.tools.sandbox import SandboxContext


def _ctx(domain: str, shift: str, *, seed: int = 42) -> SandboxContext:
    scen = load(domain, shift, seed=seed)
    return SandboxContext(sim=scen.sim, scenario_id=f"{domain}:{shift}:{seed}")


# ---- set_parameter: non-Hooke fields are now settable --------------------

def test_set_parameter_non_hooke_field():
    ctx = _ctx("hooke", "gamma_1_2")  # has fields k0, xi, phi, m, x0, y0, vx0, vy0
    before = ctx.sim.params.xi
    target = before + 0.05
    r = call(ctx, "manipulate.set_parameter", param_name="xi", value=target)
    assert r["ok"]
    assert ctx.sim.params.xi == pytest.approx(target)


def test_set_parameter_unknown_field_rejected():
    ctx = _ctx("hooke", "gamma_1_2")
    with pytest.raises(ValueError):
        call(ctx, "manipulate.set_parameter", param_name="not_a_field", value=1.0)


# ---- set_initial: arbitrary IC dicts -------------------------------------

def test_set_initial_multi_dim_hooke():
    ctx = _ctx("hooke", "gamma_1_2")
    r = call(ctx, "manipulate.set_initial", body_id=0,
             state={"x0": 0.3, "y0": 0.1, "vx0": 0.0, "vy0": 0.1})
    assert r["ok"]
    p = ctx.sim.params
    assert p.x0 == pytest.approx(0.3)
    assert p.y0 == pytest.approx(0.1)
    assert p.vx0 == pytest.approx(0.0)
    assert p.vy0 == pytest.approx(0.1)


def test_set_initial_multi_dim_gravity_3d():
    ctx = _ctx("gravity", "gamma_2_1")
    r = call(ctx, "manipulate.set_initial", body_id=0,
             state={"x0": 1.0e7, "y0": 0.0, "z0": 0.0,
                    "vx0": 0.0, "vy0": 500.0, "vz0": 0.0})
    assert r["ok"]
    p = ctx.sim.params
    assert (p.x0, p.y0, p.z0) == pytest.approx((1.0e7, 0.0, 0.0))
    assert (p.vx0, p.vy0, p.vz0) == pytest.approx((0.0, 500.0, 0.0))


def test_set_initial_ignores_unknown_keys_keeps_known():
    ctx = _ctx("hooke", "gamma_1_2")
    r = call(ctx, "manipulate.set_initial", body_id=0,
             state={"x0": 0.25, "bogus": 99.0})
    assert r["ok"]
    assert ctx.sim.params.x0 == pytest.approx(0.25)


def test_set_initial_all_unknown_raises():
    ctx = _ctx("hooke", "gamma_1_2")
    with pytest.raises(ValueError):
        call(ctx, "manipulate.set_initial", body_id=0,
             state={"only_bogus_key": 1.0})


# ---- apply_impulse: vector + dict + scalar -------------------------------

def test_apply_impulse_vector_list_3d_gravity():
    ctx = _ctx("gravity", "gamma_2_1")
    vx_before = ctx.sim.params.vx0
    vy_before = ctx.sim.params.vy0
    vz_before = ctx.sim.params.vz0
    r = call(ctx, "manipulate.apply_impulse", body_id=0,
             delta_p=[1.0, 0.5, 0.0], t=0.0)
    assert r["ok"]
    m = ctx.sim.params.m
    assert ctx.sim.params.vx0 == pytest.approx(vx_before + 1.0 / m)
    assert ctx.sim.params.vy0 == pytest.approx(vy_before + 0.5 / m)
    assert ctx.sim.params.vz0 == pytest.approx(vz_before)  # unchanged


def test_apply_impulse_dict_components():
    ctx = _ctx("hooke", "gamma_1_2")
    vx_before = ctx.sim.params.vx0
    vy_before = ctx.sim.params.vy0
    r = call(ctx, "manipulate.apply_impulse", body_id=0,
             delta_p={"px": 0.2, "py": -0.1}, t=0.0)
    assert r["ok"]
    m = ctx.sim.params.m
    assert ctx.sim.params.vx0 == pytest.approx(vx_before + 0.2 / m)
    assert ctx.sim.params.vy0 == pytest.approx(vy_before - 0.1 / m)


def test_apply_impulse_scalar_back_compat_1d_hooke():
    ctx = _ctx("hooke", "baseline")
    v_before = ctx.sim.params.v0
    r = call(ctx, "manipulate.apply_impulse", body_id=0, delta_p=0.3, t=0.0)
    assert r["ok"]
    assert ctx.sim.params.v0 == pytest.approx(v_before + 0.3 / ctx.sim.params.m)


def test_apply_impulse_vector_too_long_raises():
    ctx = _ctx("hooke", "gamma_1_2")  # has vx0, vy0 only — no vz0
    with pytest.raises(ValueError):
        call(ctx, "manipulate.apply_impulse", body_id=0,
             delta_p=[1.0, 0.5, 0.25], t=0.0)


# ---- time_reverse_probe: multi-D uses primary observable -----------------

def test_time_reverse_probe_multi_dim_hooke():
    ctx = _ctx("hooke", "gamma_1_2")
    snap = dataclasses.replace(ctx.sim.params)
    r = call(ctx, "manipulate.time_reverse_probe", t_window=[0.0, 0.1])
    assert "forward_x" in r and "reversed_x" in r
    assert r["observable"] == "x"
    assert r["reversed_x"] == list(reversed(r["forward_x"]))
    # no mutation
    assert dataclasses.asdict(ctx.sim.params) == dataclasses.asdict(snap)


def test_time_reverse_probe_gravity_uses_r_or_x():
    """Gravity baseline exposes ``r`` (1-D radial); γ-2-1 3-D exposes ``x``.

    Either way the probe must succeed without a KeyError.
    """
    ctx = _ctx("gravity", "baseline")
    r = call(ctx, "manipulate.time_reverse_probe", t_window=[0.0, 100.0])
    assert r["observable"] in {"x", "r"}
    assert len(r["forward_x"]) == 3


# ---- set_external_field / set_boundary stubs improve the reason field ----

def test_set_external_field_reason_includes_domain():
    ctx = _ctx("hooke", "gamma_1_2")
    r = call(ctx, "manipulate.set_external_field", field_spec={"E": [0, 0, 1]})
    assert r["applicable"] is False
    assert "reason" in r and r["reason"]


def test_set_boundary_reason_includes_domain():
    ctx = _ctx("hooke", "gamma_1_2")
    r = call(ctx, "manipulate.set_boundary", boundary_spec={"type": "dirichlet"})
    assert r["applicable"] is False
    assert "reason" in r and r["reason"]
