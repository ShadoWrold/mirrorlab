"""Oracle ceiling agent for Sprint 4.

Given the catalog ground-truth law (read directly from the shift module's
``shifted_force`` / ``shifted_law`` or, for baselines, the domain class's
canonical force law), build a §5-compliant submission that uses a callable
predictor wrapping that law. No LLM, no tool calls.

This sets the *bench ceiling*: it answers "if an agent had perfect
knowledge of the law and parameters, what S_scen could it reach?" — which
tells us whether sub-baseline scores from real LLMs are LLM-limited or
bench-limited.

Post-XY status (T4, blueprint §3.5): per-shift truth-form predictors are
migrated incrementally. γ-2-1 (gravity) now ships the real anisotropic
``shifted_force`` projection with full param exposure so Y plumbing on
sub-grid (c) can override declared values with per-point ``cf_params``.
The other 30 ceiling branches still close over ``scenario.sim.params``
and will be migrated in T12 (P1 batch). Where a branch falls back to
baseline-form because the truth law requires inputs the legacy grid
does not expose, that fallback is silent today and will be replaced by
an explicit ``warn + CLAMP`` per blueprint §2.6 in T12.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from mirrorlab.scenarios.loader import ScenarioInstance
from mirrorlab.shifts import (
    coulomb_d_5_1,
    coulomb_g_5_1,
    coulomb_g_5_2,
    damped_ho_d_3_1,
    damped_ho_g_3_1,
    damped_ho_g_3_2,
    decay_d_12_1,
    decay_g_12_1,
    decay_g_12_2,
    fluid_d_10_1,
    fluid_g_10_1,
    fluid_g_10_2,
    gravity_d_2_1,
    gravity_g_2_1,
    gravity_g_2_2,
    hooke_d_1_1,
    hooke_g_1_1,
    hooke_g_1_2,
    kinetics_d_11_1,
    kinetics_g_11_1,
    kinetics_g_11_2,
    optics_d_9_1,
    optics_g_9_1,
    optics_g_9_2,
    pendulum_d_4_1,
    pendulum_g_4_1,
    pendulum_g_4_2,
    rlc_d_6_1,
    rlc_g_6_1,
    rlc_g_6_2,
    thermal_d_7_1,
    thermal_g_7_1,
    thermal_g_7_2,
    wave_d_8_1,
    wave_g_8_1,
    wave_g_8_2,
)

Submission = List[Dict[str, Any]]
PredictorFn = Callable[..., float]


# ---- Helpers ---------------------------------------------------------------

def _attr(p: Any, names, default: float) -> float:
    for n in names:
        if hasattr(p, n):
            try:
                v = float(getattr(p, n))
                if math.isfinite(v):
                    return v
            except (TypeError, ValueError):
                continue
    return float(default)


def _dim_units(scenario: ScenarioInstance) -> tuple[list[dict], list[dict]]:
    dim = scenario.dim_signature
    inputs = [{"name": n, "units": u} for n, u in (dim.get("inputs") or {}).items()]
    outputs = [{"name": n, "units": u} for n, u in (dim.get("outputs") or {}).items()]
    return inputs, outputs


# ---- Per-domain predictor builders -----------------------------------------
#
# Each function returns a callable predictor f(**inputs) → float.
# Predictors close over scenario.sim.params so they can be invoked with
# only the grid's input variables (no params kwarg).

def _hooke_pred(scenario: ScenarioInstance) -> PredictorFn:
    """Hooke ceiling predictors.

    T7 (blueprint §3.5): baseline + γ-1-1 + γ-1-2 + δ-1-1 read law
    coefficients via ``**kw`` with defaults bound to the sim's params,
    so the predictor is callable in legacy contexts AND every per-call
    kwarg overrides the default (Y plumbing on sub-grid (c)).
    """
    sim = scenario.sim
    p = sim.params
    shift_id = scenario.shift_id

    if shift_id == "delta_1_1":
        _k0 = float(_attr(p, ("k",), 1.0))
        _c0 = float(_attr(p, ("c",), 0.0))
        _L0 = float(_attr(p, ("L",), 1.0))

        def pred(*, x, v, k=_k0, c=_c0, L=_L0, **_):
            return -k * x - c * (x * x / (L * L)) * v
        return pred

    if shift_id == "gamma_1_1":
        _k0 = float(_attr(p, ("k",), 1.0))
        _eta0 = float(_attr(p, ("eta",), 0.0))
        _xs0 = float(_attr(p, ("x_scale",), 1.0)) or 1.0

        def pred(*, x, k=_k0, eta=_eta0, x_scale=_xs0, **_):
            return -k * x * (1.0 + eta * math.tanh(x / x_scale))
        return pred

    if shift_id == "gamma_1_2":
        # 2-D ROT-anisotropic stiffness. Read x, y from the grid and
        # return the radial-projected signed magnitude of F per blueprint
        # §2.5 (same convention as gravity γ-2-1).
        _k0 = float(_attr(p, ("k0", "k"), 1.0))
        _xi0 = float(_attr(p, ("xi",), 0.0))
        _phi0 = float(_attr(p, ("phi",), 0.0))

        def pred(*, x, y, k0=_k0, xi=_xi0, phi=_phi0, **_):
            r2 = x * x + y * y
            r = math.sqrt(r2)
            if r == 0.0:
                return 0.0
            theta = math.atan2(y, x)
            K_theta = k0 * (1.0 + xi * math.cos(2.0 * (theta - phi)))
            F_r = -K_theta * r
            F_theta = k0 * xi * r * math.sin(2.0 * (theta - phi))
            # Convert (F_r, F_θ) → (Fx, Fy) so we can apply the standard
            # signed-|F|·r̂ projection used in loader_shifts/hooke.py.
            rhat_x, rhat_y = x / r, y / r
            that_x, that_y = -rhat_y, rhat_x
            Fx = F_r * rhat_x + F_theta * that_x
            Fy = F_r * rhat_y + F_theta * that_y
            dot = Fx * rhat_x + Fy * rhat_y
            mag = math.sqrt(Fx * Fx + Fy * Fy)
            return math.copysign(mag, dot) if dot != 0.0 else mag
        return pred

    # Baseline: F = -k x.
    _k0 = float(_attr(p, ("k",), 1.0))

    def pred(*, x, k=_k0, **_):
        return -k * x
    return pred


def _damped_ho_pred(scenario: ScenarioInstance) -> PredictorFn:
    """damped_ho ceiling predictors. T16 truth-form for all 4 cells."""
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_3_1":
        # Use single-point ⟨x²⟩ ≈ x² proxy (same as builder).
        _w0 = float(_attr(p, ("omega0",), 1.0))
        _g0 = float(_attr(p, ("gamma",), 0.0))
        _ka0 = float(_attr(p, ("kappa",), 0.0))
        _xr0 = float(_attr(p, ("x_ref",), 1.0)) or 1.0

        def pred(*, x, v,
                 omega_0=_w0, gamma=_g0, kappa=_ka0, x_ref=_xr0, **_):
            x2_mean = x * x
            omega2 = omega_0 * omega_0 * (1.0 + kappa * x2_mean / (x_ref * x_ref))
            return -2.0 * gamma * v - omega2 * x
        return pred

    if shift_id == "gamma_3_2":
        _w0 = float(_attr(p, ("omega0",), 1.0))
        _g0 = float(_attr(p, ("gamma",), 0.0))
        _e0 = float(_attr(p, ("eps",), 0.0))
        _Op = float(_attr(p, ("Omega_p",), 0.0))

        def pred(*, x, v, t,
                 omega_0=_w0, gamma=_g0, eps=_e0, Omega_p=_Op, **_):
            omega2 = omega_0 * omega_0 * (1.0 + eps * math.cos(Omega_p * t))
            return -2.0 * gamma * v - omega2 * x
        return pred

    if shift_id == "delta_3_1":
        _w0 = float(_attr(p, ("omega0",), 1.0))
        _g0 = float(_attr(p, ("gamma",), 0.0))
        _L0 = float(_attr(p, ("L",), 1.0)) or 1.0

        def pred(*, x, v,
                 omega_0=_w0, gamma=_g0, L=_L0, **_):
            gate = abs(x) / L - 1.0
            return -2.0 * gamma * gate * v - omega_0 * omega_0 * x
        return pred

    # Baseline: F/m = −(k/m)x − (c/m)v; predictor returns ẍ.
    _k0 = float(_attr(p, ("k",), 1.0))
    _c0 = float(_attr(p, ("c",), 0.0))
    _m0 = float(_attr(p, ("m",), 1.0)) or 1.0

    def pred(*, x, v, k=_k0, c=_c0, m=_m0, **_):
        return -(k / m) * x - (c / m) * v
    return pred


def _gravity_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_2_1":
        # T4 (P0, blueprint §3.5): real 3-D anisotropic projection.
        # G/M/xi/nx/ny/nz default to the sim's params so the predictor is
        # callable in legacy contexts that invoke it with only the grid's
        # input variables. When the evaluator runs through the Y-plumbing
        # path on sub-grid (c), per-point ``cf_params`` flow in via
        # ``**kw`` and override these defaults — the per-call kwargs win
        # over defaults at the Python-binding level, exactly the override
        # semantics blueprint §2.3 demands.
        _G0 = float(_attr(p, ("G0", "G"), 6.6743e-11))
        _M0 = float(_attr(p, ("M",), 1.0))
        _m0 = float(_attr(p, ("m",), 1.0))
        _xi0 = float(_attr(p, ("xi",), 0.0))
        _nx0 = float(_attr(p, ("nx",), 0.0))
        _ny0 = float(_attr(p, ("ny",), 0.0))
        _nz0 = float(_attr(p, ("nz",), 1.0))

        def pred(*, x, y, z,
                 G=_G0, M=_M0, m=_m0, xi=_xi0,
                 nx=_nx0, ny=_ny0, nz=_nz0, **_):
            r2 = x * x + y * y + z * z
            r = math.sqrt(r2)
            if r == 0.0:
                return 0.0
            rhat_x, rhat_y, rhat_z = x / r, y / r, z / r
            mu = rhat_x * nx + rhat_y * ny + rhat_z * nz
            Amp = G * M * m
            rad_coef = -Amp * (1.0 + xi * (mu * mu - 1.0 / 3.0)) / r2
            perp_coef = 2.0 * Amp * xi * mu / r2
            Fx = rad_coef * rhat_x + perp_coef * (nx - mu * rhat_x)
            Fy = rad_coef * rhat_y + perp_coef * (ny - mu * rhat_y)
            Fz = rad_coef * rhat_z + perp_coef * (nz - mu * rhat_z)
            dot = Fx * rhat_x + Fy * rhat_y + Fz * rhat_z
            mag = math.sqrt(Fx * Fx + Fy * Fy + Fz * Fz)
            return math.copysign(mag, dot) if dot != 0.0 else mag
        return pred

    if shift_id == "gamma_2_2":
        # 1-D Lorentzian range bump. Reads via **kw; the t kwarg from
        # other branches is harmlessly absorbed by **_.
        _G0 = float(_attr(p, ("G", "G0"), 6.6743e-11))
        _M0 = float(_attr(p, ("M",), 1.0))
        _m0 = float(_attr(p, ("m",), 1.0))
        _a0 = float(_attr(p, ("alpha",), 0.0))
        _rs0 = float(_attr(p, ("r_scale",), 1.0e7)) or 1.0e7

        def pred(*, r,
                 G=_G0, M=_M0, m=_m0, alpha=_a0, r_scale=_rs0, **_):
            ratio = r / r_scale
            return -G * M * m / (r * r) * (1.0 + alpha * ratio / (1.0 + ratio * ratio))
        return pred

    if shift_id == "delta_2_1":
        # G(t) = G₀·(1 + β·cos(ω_G t)); ignore φ (catalog locks φ ≡ 0).
        _G0 = float(_attr(p, ("G0", "G"), 6.6743e-11))
        _M0 = float(_attr(p, ("M",), 1.0))
        _m0 = float(_attr(p, ("m",), 1.0))
        _b0 = float(_attr(p, ("beta",), 0.0))
        _w0 = float(_attr(p, ("omega_G",), 0.0))

        def pred(*, r, t,
                 G=_G0, M=_M0, m=_m0, beta=_b0, omega_G=_w0, **_):
            G_t = G * (1.0 + beta * math.cos(omega_G * t))
            return -G_t * M * m / (r * r)
        return pred

    # baseline (γ-2-1 handled above with full truth-form projection).
    _G0 = float(_attr(p, ("G", "G0"), 6.6743e-11))
    _M0 = float(_attr(p, ("M",), 1.0))
    _m0 = float(_attr(p, ("m",), 1.0))

    def pred(*, r, G=_G0, M=_M0, m=_m0, **_):
        return -G * M * m / (r * r)
    return pred


def _coulomb_pred(scenario: ScenarioInstance) -> PredictorFn:
    """Coulomb ceiling predictors.

    T8 (blueprint §3.5). Truth-form for baseline + γ-5-1 + γ-5-2 + δ-5-1;
    each reads law coefficients via ``**kw`` with defaults bound to
    sim.params so Y plumbing on (c) flows through.
    """
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_5_1":
        # 3-D anisotropic pair force, signed-|F|·r̂ projection.
        _ke0 = float(_attr(p, ("k_e",), 8.9875517873681764e9))
        _q10 = float(_attr(p, ("q_src",), 1.0e-9))
        _q20 = float(_attr(p, ("q_test",), 1.0e-9))
        _chi0 = float(_attr(p, ("chi",), 0.0))
        _mx0 = float(_attr(p, ("mx",), 0.0))
        _my0 = float(_attr(p, ("my",), 0.0))
        _mz0 = float(_attr(p, ("mz",), 1.0))

        def pred(*, x, y, z,
                 k_e=_ke0, q_1=_q10, q_2=_q20, chi=_chi0,
                 mx=_mx0, my=_my0, mz=_mz0, **_):
            r2 = x * x + y * y + z * z
            r = math.sqrt(r2)
            if r == 0.0:
                return 0.0
            rhat_x, rhat_y, rhat_z = x / r, y / r, z / r
            nu = rhat_x * mx + rhat_y * my + rhat_z * mz
            A = k_e * q_1 * q_2
            rad = A * (1.0 + chi * (nu * nu - 1.0 / 3.0)) / r2
            perp_coef = -2.0 * A * chi * nu / r2
            Fx = rad * rhat_x + perp_coef * (mx - nu * rhat_x)
            Fy = rad * rhat_y + perp_coef * (my - nu * rhat_y)
            Fz = rad * rhat_z + perp_coef * (mz - nu * rhat_z)
            dot = Fx * rhat_x + Fy * rhat_y + Fz * rhat_z
            mag = math.sqrt(Fx * Fx + Fy * Fy + Fz * Fz)
            return math.copysign(mag, dot) if dot != 0.0 else mag
        return pred

    if shift_id == "gamma_5_2":
        # 2 fixed source charges + 1 mobile test charge with saturating
        # potential nonlinearity. Source positions are BC (closure-only),
        # the law coefficients (k_e, xi, phi_0, charges) are kwargs.
        from mirrorlab.shifts import coulomb_g_5_2 as _g52_mod

        _ke0 = float(_attr(p, ("k_e",), 8.9875517873681764e9))
        _xi0 = float(_attr(p, ("xi",), 0.0))
        _phi00 = float(_attr(p, ("phi0",), 1.0))
        _q10 = float(_attr(p, ("src1_q",), 1.0e-6))
        _q20 = float(_attr(p, ("src2_q",), -1.0e-6))
        _q30 = float(_attr(p, ("q_test",), 1.0e-9))
        _src1 = (
            float(_attr(p, ("src1_x",), -0.5)),
            float(_attr(p, ("src1_y",), 0.0)),
            float(_attr(p, ("src1_z",), 0.0)),
        )
        _src2 = (
            float(_attr(p, ("src2_x",), 0.5)),
            float(_attr(p, ("src2_y",), 0.0)),
            float(_attr(p, ("src2_z",), 0.0)),
        )
        # Capture the midpoint for the signed-|F|·r̂ projection.
        _mid = (
            (_src1[0] + _src2[0]) / 2,
            (_src1[1] + _src2[1]) / 2,
            (_src1[2] + _src2[2]) / 2,
        )

        def pred(*, x, y, z,
                 k_e=_ke0, xi=_xi0, phi_0=_phi00,
                 q_1=_q10, q_2=_q20, q_3=_q30, **_):
            # Build a temporary params object so we can reuse the shift
            # module's vector force routine without duplicating it.
            # Source positions are taken from the closure (sim params),
            # only law coefficients come from kwargs.
            p_eff = _g52_mod.CoulombGamma52Params(
                k_e=k_e, xi=xi, phi0=phi_0, q_test=q_3, m=p.m,
                src1_q=q_1, src1_x=_src1[0], src1_y=_src1[1], src1_z=_src1[2],
                src2_q=q_2, src2_x=_src2[0], src2_y=_src2[1], src2_z=_src2[2],
                x0=p.x0, y0=p.y0, z0=p.z0,
                vx0=p.vx0, vy0=p.vy0, vz0=p.vz0,
            )
            F = _g52_mod.shifted_force((x, y, z), p_eff)
            dx, dy, dz = x - _mid[0], y - _mid[1], z - _mid[2]
            r = math.sqrt(dx * dx + dy * dy + dz * dz)
            if r == 0.0:
                return math.sqrt(F[0] ** 2 + F[1] ** 2 + F[2] ** 2)
            rhat = (dx / r, dy / r, dz / r)
            dot = F[0] * rhat[0] + F[1] * rhat[1] + F[2] * rhat[2]
            mag = math.sqrt(F[0] ** 2 + F[1] ** 2 + F[2] ** 2)
            return math.copysign(mag, dot) if dot != 0.0 else mag
        return pred

    if shift_id == "delta_5_1":
        # Charge-leakage dynamics: GT is ‖(dq1/dt, dq2/dt)‖.
        # Positions are fixed BC; only k_e/α/n/E_ref are law coefficients.
        from mirrorlab.shifts import coulomb_d_5_1 as _d51_mod

        _ke0 = float(_attr(p, ("k_e",), 8.9875517873681764e9))
        _a0 = float(_attr(p, ("alpha",), 1e-3))
        _n0 = float(_attr(p, ("n_exp",), 1.0))
        _Er0 = float(_attr(p, ("E_ref",), 1.0))

        def pred(*, q1, q2,
                 k_e=_ke0, alpha=_a0, n_exp=_n0, E_ref=_Er0, **_):
            p_eff = _d51_mod.CoulombDelta51Params(
                k_e=k_e, alpha=alpha, n_exp=n_exp, E_ref=E_ref,
                q1_0=q1, q2_0=q2,
                x1=p.x1, y1=p.y1, z1=p.z1,
                x2=p.x2, y2=p.y2, z2=p.z2,
                T_sim=p.T_sim,
            )
            dq1, dq2 = _d51_mod.shifted_law(q1, q2, p_eff)
            return math.sqrt(dq1 * dq1 + dq2 * dq2)
        return pred

    # Baseline: F = k_e q1 q2 / r².
    _ke0 = float(_attr(p, ("k_e",), 8.9875517873681764e9))
    _q10 = float(_attr(p, ("q1", "q_src", "src1_q"), 1.0e-9))
    _q20 = float(_attr(p, ("q2", "q_test", "src2_q"), 1.0e-9))

    def pred(*, r, k_e=_ke0, q_1=_q10, q_2=_q20, **_):
        return k_e * q_1 * q_2 / (r * r)
    return pred


def _pendulum_pred(scenario: ScenarioInstance) -> PredictorFn:
    """pendulum ceiling predictors. T17 truth-form for all 4 cells."""
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_4_1":
        _gol = float(_attr(p, ("g_over_L",), 9.81))
        _a0 = float(_attr(p, ("alpha",), 0.0))

        def pred(*, theta, g_over_L=_gol, alpha=_a0, **_):
            return -g_over_L * math.sin(theta) - g_over_L * alpha * (1.0 - math.cos(theta))
        return pred

    if shift_id == "gamma_4_2":
        _gol = float(_attr(p, ("g0_over_L", "g_over_L"), 9.81))
        _a0 = float(_attr(p, ("alpha",), 0.0))
        _L0 = float(_attr(p, ("L",), 1.0)) or 1.0
        _H0 = float(_attr(p, ("H",), 1.0)) or 1.0

        def pred(*, theta, g_over_L=_gol, alpha=_a0, L=_L0, H=_H0, **_):
            height = L * (1.0 - math.cos(theta))
            g_eff = g_over_L * (1.0 - alpha * height / H)
            return -g_eff * math.sin(theta)
        return pred

    if shift_id == "delta_4_1":
        _gol = float(_attr(p, ("g0_over_L", "g_over_L"), 9.81))
        _e0 = float(_attr(p, ("eps",), 0.0))
        _Om = float(_attr(p, ("Omega",), 0.0))

        def pred(*, theta, t, g_over_L=_gol, eps=_e0, Omega=_Om, **_):
            factor = 1.0 + eps * math.cos(Omega * t)
            return -g_over_L * factor * math.sin(theta)
        return pred

    # baseline
    _gol = float(_attr(p, ("g_over_L", "g0_over_L"),
                       _attr(p, ("g",), 9.81) / max(_attr(p, ("L",), 1.0), 1e-9)))

    def pred(*, theta, g_over_L=_gol, **_):
        return -g_over_L * math.sin(theta)
    return pred


def _rlc_pred(scenario: ScenarioInstance) -> PredictorFn:
    """rlc ceiling predictors. T20 truth-form returns di/dt.

    Output channel migrated from V (Kirchhoff sum) to di/dt to align
    with the truth-form builders in loader_shifts/rlc.py.
    """
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_6_1":
        from mirrorlab.shifts import rlc_g_6_1 as _g61_m
        _L0 = float(_attr(p, ("L0",), 1.0e-3))
        _R0 = float(_attr(p, ("R",), 1.0))
        _C0 = float(_attr(p, ("C",), 1.0e-6))
        _Is0 = float(_attr(p, ("I_sat",), 1.0))

        def pred(*, q, i,
                 L_0=_L0, R=_R0, C=_C0, I_sat=_Is0, **_):
            p_eff = _g61_m.RLCGamma61Params(
                L0=L_0, R=R, C=C, I_sat=I_sat,
                q0=getattr(p, "q0", 0.0), i0=getattr(p, "i0", 0.0),
            )
            return float(_g61_m.shifted_law(q, i, p_eff))
        return pred

    if shift_id == "gamma_6_2":
        from mirrorlab.shifts import rlc_g_6_2 as _g62_m
        _L10 = float(_attr(p, ("L1",), 1.0e-3))
        _L20 = float(_attr(p, ("L2",), 1.0e-3))
        _R10 = float(_attr(p, ("R1",), 1.0))
        _R20 = float(_attr(p, ("R2",), 1.0))
        _C10 = float(_attr(p, ("C1",), 1.0e-6))
        _C20 = float(_attr(p, ("C2",), 1.0e-6))
        _M00 = float(_attr(p, ("M0",), 0.0))
        _dM0 = float(_attr(p, ("dM",), 0.0))

        def pred(*, q_1, i_1, q_2, i_2,
                 L_1=_L10, L_2=_L20, R_1=_R10, R_2=_R20,
                 C_1=_C10, C_2=_C20, M_0=_M00, dM=_dM0, **_):
            p_eff = _g62_m.RLCGamma62Params(
                L1=L_1, L2=L_2, R1=R_1, R2=R_2,
                C1=C_1, C2=C_2, M0=M_0, dM=dM,
                q1_0=0.0, q2_0=0.0, i1_0=0.0, i2_0=0.0,
            )
            di1, _ = _g62_m.shifted_law(q_1, i_1, q_2, i_2, p_eff)
            return float(di1)
        return pred

    if shift_id == "delta_6_1":
        from mirrorlab.shifts import rlc_d_6_1 as _d61_m
        _L0 = float(_attr(p, ("L0",), 1.0e-3))
        _R0 = float(_attr(p, ("R",), 1.0))
        _C0 = float(_attr(p, ("C",), 1.0e-6))
        _e0 = float(_attr(p, ("eps",), 0.0))
        _Op = float(_attr(p, ("Omega_p",), 0.0))

        def pred(*, q, i, t,
                 L_0=_L0, R=_R0, C=_C0, eps=_e0, Omega_p=_Op, **_):
            p_eff = _d61_m.RLCDelta61Params(
                L0=L_0, R=R, C=C, eps=eps, Omega_p=Omega_p,
                q0=getattr(p, "q0", 0.0), i0=getattr(p, "i0", 0.0),
            )
            return float(_d61_m.shifted_law(q, i, t, p_eff))
        return pred

    # baseline: di/dt = -(R·i + q/C) / L
    _L0 = float(_attr(p, ("L", "L0"), 1.0e-3))
    _R0 = float(_attr(p, ("R",), 1.0))
    _C0 = float(_attr(p, ("C",), 1.0e-6))

    def pred(*, q, i, L=_L0, R=_R0, C=_C0, **_):
        return -(R * i + q / max(C, 1e-30)) / max(L, 1e-12)
    return pred


def _thermal_pred(scenario: ScenarioInstance) -> PredictorFn:
    """Thermal ceiling predictors.

    T9 (blueprint §3.5). Truth-form for baseline + γ-7-1 + γ-7-2 + δ-7-1.
    Coefficients read via **kw with defaults from sim params.
    """
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_7_1":
        # ROT anisotropic conductivity. K = k₀(I + β·n̂n̂ᵀ); GT = |K·∇T|
        # where ∇T = (T_cold − T_hot)/L · d̂.
        from mirrorlab.shifts import thermal_g_7_1 as _g71_mod

        _k0d = float(_attr(p, ("k0",), 1.0))
        _beta0 = float(_attr(p, ("beta",), 0.0))
        _n_vec = tuple(float(x) for x in getattr(p, "n", (0.0, 0.0, 1.0)))

        def pred(*, T_hot, T_cold, L, dx, dy, dz,
                 k=_k0d, beta=_beta0, **_):
            p_eff = _g71_mod.ThermalGamma71Params(
                k0=k, beta=beta, n=_n_vec,
                L=L, T_hot=T_hot, T_cold=T_cold, grad_dir=(dx, dy, dz),
            )
            return _g71_mod.shifted_flux_magnitude(p_eff)
        return pred

    if shift_id == "gamma_7_2":
        # Power-law memory kernel.
        from mirrorlab.shifts import thermal_g_7_2 as _g72_mod

        _k0d = float(_attr(p, ("k0",), 1.0))
        _p0 = float(_attr(p, ("p",), 0.5))
        _tau0 = float(_attr(p, ("tau_min",), 1e-3))

        def pred(*, T_hot, T_cold, L, t,
                 k=_k0d, p_exp=_p0, tau_min=_tau0, **_):
            p_eff = _g72_mod.ThermalGamma72Params(
                k0=k, p=p_exp, L=L, T_hot=T_hot, T_cold=T_cold, tau_min=tau_min,
            )
            return _g72_mod.shifted_flux(t, p_eff)
        return pred

    if shift_id == "delta_7_1":
        # PDE sink, step()-based truth: instantiate and integrate per
        # call. Slow (~ms each) but blueprint §3.2.1 accepts this for
        # the 7 step()-only cells.
        from mirrorlab.shifts import thermal_d_7_1 as _d71_mod

        _alpha0 = float(_attr(p, ("alpha",), 1e-4))
        _lam0 = float(_attr(p, ("lam",), 1e-3))
        _Tref0 = float(_attr(p, ("T_ref",), 300.0))
        _Ta0 = float(_attr(p, ("T_a",), 373.0))
        _Tb0 = float(_attr(p, ("T_b",), 293.0))
        _dx0 = float(_attr(p, ("dx",), 0.1))

        def pred(*, t,
                 alpha=_alpha0, lam=_lam0, T_ref=_Tref0, **_):
            p_eff = _d71_mod.ThermalDelta71Params(
                alpha=alpha, lam=lam, T_ref=T_ref,
                T_a=_Ta0, T_b=_Tb0, dx=_dx0,
            )
            inst = _d71_mod.ThermalDelta71Instance(p_eff)
            return inst.step(t)["T_a"]
        return pred

    # Baseline: Fourier q = k·(T_hot − T_cold)/L.
    _k0d = float(_attr(p, ("k",), 1.0))

    def pred(*, T_hot, T_cold, L, k=_k0d, **_):
        return k * (T_hot - T_cold) / max(L, 1e-12)
    return pred


def _wave_pred(scenario: ScenarioInstance) -> PredictorFn:
    """wave ceiling predictors. T21 truth-form returns u(t) at probe."""
    p = scenario.sim.params
    shift_id = scenario.shift_id
    x_probe = float(_attr(p, ("x_probe",), 0.0))

    if shift_id == "gamma_8_1":
        from mirrorlab.shifts import wave_g_8_1 as _g81_m
        _A0 = float(_attr(p, ("A",), 1.0))
        _k0 = float(_attr(p, ("k",), 1.0))
        _c0 = float(_attr(p, ("c",), 1.0))
        _g0 = float(_attr(p, ("gamma",), 0.0))

        def pred(*, t, A=_A0, k=_k0, c=_c0, gamma=_g0, **_):
            p_eff = _g81_m.WaveGamma81Params(A=A, k=k, c=c, gamma=gamma, x_probe=x_probe)
            w2 = _g81_m.shifted_omega_squared(p_eff)
            omega = math.sqrt(max(w2, 0.0))
            return A * math.sin(k * x_probe - omega * t)
        return pred

    if shift_id == "gamma_8_2":
        from mirrorlab.shifts import wave_g_8_2 as _g82_m
        _A0 = float(_attr(p, ("A",), 1.0))
        _k0 = float(_attr(p, ("k",), 1.0))
        _c0 = float(_attr(p, ("c",), 1.0))
        _b0 = float(_attr(p, ("beta",), 0.0))
        _tk0 = float(_attr(p, ("theta_k",), 0.0))
        _t00 = float(_attr(p, ("theta0",), 0.0))

        def pred(*, t, A=_A0, k=_k0, c=_c0, beta=_b0, **_):
            p_eff = _g82_m.WaveGamma82Params(
                A=A, k=k, theta_k=_tk0, c=c, beta=beta, theta0=_t00, x_probe=x_probe,
            )
            w2 = _g82_m.shifted_omega_squared(p_eff)
            omega = math.sqrt(max(w2, 0.0))
            return A * math.sin(k * x_probe - omega * t)
        return pred

    if shift_id == "delta_8_1":
        from mirrorlab.shifts import wave_d_8_1 as _d81_m
        _A0 = float(_attr(p, ("A",), 1.0))
        _k0 = float(_attr(p, ("k",), 1.0))
        _c0 = float(_attr(p, ("c",), 1.0))
        _a0 = float(_attr(p, ("alpha0",), 0.0))
        _ur0 = float(_attr(p, ("u_ref",), 1.0))

        def pred(*, t, A=_A0, k=_k0, c=_c0, alpha=_a0, u_ref=_ur0, **_):
            try:
                p_eff = _d81_m.WaveDelta81Params(A=A, k=k, c=c, alpha0=alpha, u_ref=u_ref)
                inst = _d81_m.WaveDelta81Instance(p_eff)
                return inst.step(t)["u"]
            except (ValueError, TypeError):
                # Validator rejected cf-perturbed params; baseline tie.
                return A * math.sin(k * x_probe - c * k * t)
        return pred

    # baseline
    _A0 = float(_attr(p, ("A",), 1.0))
    _k0 = float(_attr(p, ("k",), 1.0))
    _c0 = float(_attr(p, ("c",), 1.0))
    _ph0 = float(_attr(p, ("phi",), 0.0))

    def pred(*, t, A=_A0, k=_k0, c=_c0, phi=_ph0, **_):
        return A * math.sin(k * x_probe - c * k * t + phi)
    return pred


def _optics_pred(scenario: ScenarioInstance) -> PredictorFn:
    """optics ceiling predictors. T18 truth-form returns sin(θ_t)."""
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_9_1":
        _n10 = float(_attr(p, ("n1",), 1.0))
        _n00 = float(_attr(p, ("n0",), 1.5))
        _dn0 = float(_attr(p, ("dn",), 0.0))
        _ph0 = float(_attr(p, ("phi",), 0.0))

        def pred(*, theta_i, theta_pol,
                 n_1=_n10, n_0=_n00, dn=_dn0, phi=_ph0, **_):
            n_eff = n_0 + dn * math.sin(2.0 * theta_pol - phi) ** 2
            if n_eff == 0.0:
                return 0.0
            return (n_1 / n_eff) * math.sin(theta_i)
        return pred

    if shift_id == "gamma_9_2":
        _n10 = float(_attr(p, ("n1",), 1.0))
        _n20 = float(_attr(p, ("n2",), 1.5))
        _ka0 = float(_attr(p, ("kappa",), 0.0))

        def pred(*, theta_i, n_1=_n10, n_2=_n20, kappa=_ka0, **_):
            s = math.sin(theta_i)
            anti = (n_1 - n_2) / (n_1 + n_2) if (n_1 + n_2) != 0 else 0.0
            return (n_1 / n_2) * s + kappa * anti * s ** 3
        return pred

    if shift_id == "delta_9_1":
        # Current catalog step() is baseline Snell.
        _n10 = float(_attr(p, ("n1",), 1.0))
        _n20 = float(_attr(p, ("n2",), 1.5))

        def pred(*, theta_i, t=0.0, n_1=_n10, n_2=_n20, **_):
            return (n_1 / n_2) * math.sin(theta_i)
        return pred

    # baseline Snell.
    _n10 = float(_attr(p, ("n1",), 1.0))
    _n20 = float(_attr(p, ("n2",), 1.5))

    def pred(*, theta_i, n_1=_n10, n_2=_n20, **_):
        return (n_1 / n_2) * math.sin(theta_i)
    return pred


def _fluid_pred(scenario: ScenarioInstance) -> PredictorFn:
    """fluid ceiling predictors. T19 truth-form for all 4 cells."""
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_10_1":
        # 3-vector v1/v2 + α-anisotropic M tensor; rebuild Params per call.
        from mirrorlab.shifts import fluid_g_10_1 as _g101_m
        _rho0 = float(_attr(p, ("rho",), 1000.0))
        _g0 = float(_attr(p, ("g",), 9.81))
        _a0 = float(_attr(p, ("alpha",), 0.0))
        _n0 = tuple(float(x) for x in getattr(p, "n", (1.0, 0.0, 0.0)))
        _v1f = tuple(float(x) for x in getattr(p, "v1", (0.0, 0.0, 0.0)))
        _v2f = tuple(float(x) for x in getattr(p, "v2", (0.0, 0.0, 0.0)))

        def pred(*, p1, h1, h2,
                 rho=_rho0, g=_g0, alpha=_a0, **_):
            p_eff = _g101_m.FluidGamma101Params(
                rho=rho, alpha=alpha, n=_n0, g=g,
                h1=h1, p1=p1, v1=_v1f, h2=h2, v2=_v2f,
            )
            return float(_g101_m.shifted_pressure(p_eff))
        return pred

    if shift_id == "gamma_10_2":
        from mirrorlab.shifts import fluid_g_10_2 as _g102_m
        _rho0 = float(_attr(p, ("rho",), 1000.0))
        _g0 = float(_attr(p, ("g",), 9.81))
        _h00 = float(_attr(p, ("h0",), 8000.0))
        _l0 = float(_attr(p, ("lam",), 0.0))
        _q0 = float(_attr(p, ("q",), 1.0))

        def pred(*, p1, v1, v2, h1, h2,
                 rho=_rho0, g=_g0, h_0=_h00, lam=_l0, q=_q0, **_):
            p_eff = _g102_m.FluidGamma102Params(
                rho=rho, g=g, h0=h_0, lam=lam, q=q,
                h1=h1, v1=v1, p1=p1, h2=h2, v2=v2,
            )
            return float(_g102_m.shifted_pressure(p_eff))
        return pred

    if shift_id == "delta_10_1":
        from mirrorlab.shifts import fluid_d_10_1 as _d101_m
        _rho0 = float(_attr(p, ("rho",), 1000.0))
        _g0 = float(_attr(p, ("g",), 9.81))
        _z0 = float(_attr(p, ("zeta",), 0.0))
        _m0 = float(_attr(p, ("m",), 1.0))
        _vi0 = float(_attr(p, ("v_inf",), 1.0))
        _Lp0 = float(_attr(p, ("L_path",), 1.0))

        def pred(*, p1, v1, v2, h1, h2,
                 rho=_rho0, g=_g0, zeta=_z0, **_):
            p_eff = _d101_m.FluidDelta101Params(
                rho=rho, g=g,
                h1=h1, v1=v1, p1=p1, h2=h2, v2=v2,
                zeta=zeta, m=_m0, v_inf=_vi0, L_path=_Lp0,
            )
            return float(_d101_m.shifted_pressure(p_eff))
        return pred

    # baseline Bernoulli
    _rho0 = float(_attr(p, ("rho",), 1000.0))
    _g0 = float(_attr(p, ("g",), 9.81))

    def pred(*, p1, v1, v2, h1, h2, rho=_rho0, g=_g0, **_):
        return p1 + 0.5 * rho * (v1 * v1 - v2 * v2) + rho * g * (h1 - h2)
    return pred


def _kinetics_pred(scenario: ScenarioInstance) -> PredictorFn:
    """kinetics ceiling predictors. T22 truth-form returns C(t) (or C_A
    for δ-11-1's branching). All 4 cells step()-based."""
    from mirrorlab.domains.kinetics import KineticsBaseline, KineticsParams
    from mirrorlab.shifts import (
        kinetics_d_11_1 as _d111_m,
        kinetics_g_11_1 as _g111_m,
        kinetics_g_11_2 as _g112_m,
    )

    p = scenario.sim.params
    shift_id = scenario.shift_id

    def _baseline_C_closed(k, n, C0, t):
        if n == 1.0:
            return C0 * math.exp(-k * t)
        base = C0 ** (1.0 - n) + (n - 1.0) * k * t
        if base <= 0:
            return 0.0
        return base ** (1.0 / (1.0 - n))

    if shift_id == "gamma_11_1":
        _k0 = float(_attr(p, ("k",), 1.0))
        _n0 = float(_attr(p, ("n",), 1.0))
        _b0 = float(_attr(p, ("beta",), 0.0))
        _C00 = float(_attr(p, ("C0",), 1.0))
        _tau0 = float(_attr(p, ("tau_min",), 1e-3))
        _dt0 = float(_attr(p, ("dt",), 1e-3))
        _MAX_STEPS = 200

        def pred(*, t, k=_k0, n=_n0, beta=_b0,
                 C0=_C00, tau_min=_tau0, dt=_dt0, **_):
            try:
                # Cap fractional Adams-Moulton step count (O(n²) per call).
                dt_eff = max(dt, abs(t) / _MAX_STEPS)
                p_eff = _g111_m.KineticsGamma111Params(
                    k=k, n=n, beta=beta, C0=C0, tau_min=tau_min, dt=dt_eff,
                )
                inst = _g111_m.KineticsGamma111Instance(p_eff)
                return inst.step(t)["C"]
            except (ValueError, TypeError):
                return _baseline_C_closed(k, n, C0, t)
        return pred

    if shift_id == "gamma_11_2":
        _k0 = float(_attr(p, ("k",), 1.0))
        _n0 = float(_attr(p, ("n",), 1.0))
        _m0 = float(_attr(p, ("m",), 1.0))
        _Cs0 = float(_attr(p, ("C_sat",), 1.0))
        _C00 = float(_attr(p, ("C0",), 1.0))

        def pred(*, t, k=_k0, n=_n0, m_exp=_m0,
                 C_sat=_Cs0, C0=_C00, **_):
            try:
                p_eff = _g112_m.KineticsGamma112Params(
                    k=k, n=n, m=m_exp, C_sat=C_sat, C0=C0,
                )
                inst = _g112_m.KineticsGamma112Instance(p_eff)
                return inst.step(t)["C"]
            except (ValueError, TypeError):
                return _baseline_C_closed(k, n, C0, t)
        return pred

    if shift_id == "delta_11_1":
        _k0 = float(_attr(p, ("k",), 1.0))
        _n0 = float(_attr(p, ("n",), 1.0))
        _e0 = float(_attr(p, ("eta",), 0.0))
        _CA0 = float(_attr(p, ("C_A0",), 1.0))
        _CB0 = float(_attr(p, ("C_B0",), 0.0))

        def pred(*, t, k=_k0, n=_n0, eta=_e0,
                 C_A0=_CA0, C_B0=_CB0, **_):
            try:
                p_eff = _d111_m.KineticsDelta111Params(
                    k=k, n=n, eta=eta, C_A0=C_A0, C_B0=C_B0,
                )
                inst = _d111_m.KineticsDelta111Instance(p_eff)
                return inst.step(t)["C_A"]
            except (ValueError, TypeError):
                return _baseline_C_closed(k, n, C_A0, t)
        return pred

    # baseline n-th order
    _k0 = float(_attr(p, ("k",), 1.0))
    _n0 = float(_attr(p, ("n",), 1.0))
    _C00 = float(_attr(p, ("C0",), 1.0))

    def pred(*, t, k=_k0, n=_n0, C0=_C00, **_):
        try:
            inst = KineticsBaseline(KineticsParams(k=k, n=n, C0=C0))
            return inst.step(t)["C"]
        except (ValueError, TypeError):
            return _baseline_C_closed(k, n, C0, t)
    return pred


def _decay_pred(scenario: ScenarioInstance) -> PredictorFn:
    """Decay ceiling predictors.

    T10 (blueprint §3.5, §3.2.1 step()-only). All 4 cells return N(t),
    not dN/dt. baseline uses closed-form; the 3 shifts integrate their
    actual rhs per call (bypassing the catalog validator so cf-perturbed
    coefficients still score).
    """
    from scipy.integrate import solve_ivp as _solve_ivp

    p = scenario.sim.params
    shift_id = scenario.shift_id

    def _integrate(rhs, y0, t):
        t = max(float(t), 0.0)
        if t == 0.0:
            return list(y0)
        sol = _solve_ivp(
            rhs, (0.0, t), list(y0),
            method="DOP853", rtol=1e-9, atol=1e-12,
        )
        if not sol.success:
            return list(y0)
        return [float(v) for v in sol.y[:, -1]]

    if shift_id == "gamma_12_1":
        _lam0 = float(_attr(p, ("lam",), 0.1))
        _alpha0 = float(_attr(p, ("alpha",), 0.0))
        _p0 = float(_attr(p, ("p",), 1.0))
        _Ns0 = float(_attr(p, ("N_scale",), 1.0)) or 1.0
        _Ni0 = float(_attr(p, ("N_init",), 1.0e6))

        def pred(*, t,
                 lam=_lam0, alpha=_alpha0, p_exp=_p0,
                 N_scale=_Ns0, N_init=_Ni0, **_):
            def rhs(_t, y):
                (N,) = y
                Ns = max(N, 0.0)
                return (-lam * Ns * (1.0 + alpha * (Ns / N_scale) ** p_exp),)
            return _integrate(rhs, [N_init], t)[0]
        return pred

    if shift_id == "gamma_12_2":
        _lam0 = float(_attr(p, ("lam0", "lam"), 0.1))
        _eps0 = float(_attr(p, ("eps",), 0.0))
        _omg0 = float(_attr(p, ("omega",), 0.0))
        _Ni0 = float(_attr(p, ("N_init",), 1.0e6))

        def pred(*, t,
                 lam=_lam0, eps=_eps0, omega=_omg0, N_init=_Ni0, **_):
            def rhs(_t, y):
                (N,) = y
                lam_t = lam * (1.0 + eps * math.cos(omega * _t))
                return (-lam_t * N,)
            return _integrate(rhs, [N_init], t)[0]
        return pred

    if shift_id == "delta_12_1":
        _lam0 = float(_attr(p, ("lam",), 0.1))
        _xi0 = float(_attr(p, ("xi",), 0.0))
        _NA0 = float(_attr(p, ("N_A0",), 1.0e6))
        _NB0 = float(_attr(p, ("N_B0",), 0.0))

        def pred(*, t, lam=_lam0, xi=_xi0,
                 N_A0=_NA0, N_B0=_NB0, **_):
            def rhs(_t, y):
                NA, _NB = y
                return (-lam * NA, (1.0 - xi) * lam * NA)
            return _integrate(rhs, [N_A0, N_B0], t)[0]
        return pred

    # Baseline: closed-form N(t) = N₀·exp(−λ t).
    _lam0 = float(_attr(p, ("lam",), 0.1))
    _N00 = float(_attr(p, ("N0",), 1.0e6))

    def pred(*, t, lam=_lam0, N0=_N00, **_):
        return N0 * math.exp(-lam * t)
    return pred


_DISPATCH: Dict[str, Callable[[ScenarioInstance], PredictorFn]] = {
    "hooke": _hooke_pred,
    "damped_ho": _damped_ho_pred,
    "gravity": _gravity_pred,
    "coulomb": _coulomb_pred,
    "pendulum": _pendulum_pred,
    "rlc": _rlc_pred,
    "thermal": _thermal_pred,
    "wave": _wave_pred,
    "optics": _optics_pred,
    "fluid": _fluid_pred,
    "kinetics": _kinetics_pred,
    "decay": _decay_pred,
}


# Per-(domain, shift) declared-param builders for the truth-form ceilings
# that read their coefficients via **kw rather than closing over
# scenario.sim.params. The build_submission entry's ``params`` list is
# populated from here so Y plumbing on sub-grid (c) has names to
# override with per-point cf_params. Entries not listed get an empty
# params list (legacy closure-based predictors).
def _gravity_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "G", "value": float(getattr(p, "G"))},
        {"name": "M", "value": float(getattr(p, "M"))},
        {"name": "m", "value": float(getattr(p, "m"))},
    ]


def _gravity_gamma_2_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "G", "value": float(getattr(p, "G"))},
        {"name": "M", "value": float(getattr(p, "M"))},
        {"name": "m", "value": float(getattr(p, "m"))},
        {"name": "alpha", "value": float(getattr(p, "alpha"))},
        {"name": "r_scale", "value": float(getattr(p, "r_scale"))},
    ]


def _gravity_delta_2_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "G", "value": float(getattr(p, "G0"))},
        {"name": "M", "value": float(getattr(p, "M"))},
        {"name": "m", "value": float(getattr(p, "m"))},
        {"name": "beta", "value": float(getattr(p, "beta"))},
        {"name": "omega_G", "value": float(getattr(p, "omega_G"))},
    ]


def _gravity_gamma_2_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "G", "value": float(getattr(p, "G0"))},
        {"name": "M", "value": float(getattr(p, "M"))},
        {"name": "m", "value": float(getattr(p, "m"))},
        {"name": "xi", "value": float(getattr(p, "xi"))},
        {"name": "nx", "value": float(getattr(p, "nx"))},
        {"name": "ny", "value": float(getattr(p, "ny"))},
        {"name": "nz", "value": float(getattr(p, "nz"))},
    ]


def _hooke_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [{"name": "k", "value": float(getattr(p, "k"))}]


def _hooke_gamma_1_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "eta", "value": float(getattr(p, "eta"))},
        {"name": "x_scale", "value": float(getattr(p, "x_scale"))},
    ]


def _hooke_gamma_1_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k0", "value": float(getattr(p, "k0"))},
        {"name": "xi", "value": float(getattr(p, "xi"))},
        {"name": "phi", "value": float(getattr(p, "phi"))},
    ]


def _hooke_delta_1_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "c", "value": float(getattr(p, "c"))},
        {"name": "L", "value": float(getattr(p, "L"))},
    ]


def _coulomb_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k_e", "value": float(getattr(p, "k_e"))},
        {"name": "q_1", "value": float(getattr(p, "q1"))},
        {"name": "q_2", "value": float(getattr(p, "q2"))},
    ]


def _coulomb_gamma_5_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k_e", "value": float(getattr(p, "k_e"))},
        {"name": "q_1", "value": float(getattr(p, "q_src"))},
        {"name": "q_2", "value": float(getattr(p, "q_test"))},
        {"name": "chi", "value": float(getattr(p, "chi"))},
        {"name": "mx", "value": float(getattr(p, "mx"))},
        {"name": "my", "value": float(getattr(p, "my"))},
        {"name": "mz", "value": float(getattr(p, "mz"))},
    ]


def _coulomb_gamma_5_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k_e", "value": float(getattr(p, "k_e"))},
        {"name": "xi", "value": float(getattr(p, "xi"))},
        {"name": "phi_0", "value": float(getattr(p, "phi0"))},
        {"name": "q_1", "value": float(getattr(p, "src1_q"))},
        {"name": "q_2", "value": float(getattr(p, "src2_q"))},
        {"name": "q_3", "value": float(getattr(p, "q_test"))},
    ]


def _coulomb_delta_5_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k_e", "value": float(getattr(p, "k_e"))},
        {"name": "alpha", "value": float(getattr(p, "alpha"))},
        {"name": "n_exp", "value": float(getattr(p, "n_exp"))},
        {"name": "E_ref", "value": float(getattr(p, "E_ref"))},
    ]


def _thermal_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [{"name": "k", "value": float(getattr(p, "k"))}]


def _thermal_gamma_7_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k0"))},
        {"name": "beta", "value": float(getattr(p, "beta"))},
    ]


def _thermal_gamma_7_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k0"))},
        {"name": "p_exp", "value": float(getattr(p, "p"))},
        {"name": "tau_min", "value": float(getattr(p, "tau_min"))},
    ]


def _thermal_delta_7_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "alpha", "value": float(getattr(p, "alpha"))},
        {"name": "lam", "value": float(getattr(p, "lam"))},
        {"name": "T_ref", "value": float(getattr(p, "T_ref"))},
    ]


def _decay_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "lam", "value": float(getattr(p, "lam"))},
        {"name": "N0", "value": float(getattr(p, "N0"))},
    ]


def _decay_gamma_12_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "lam", "value": float(getattr(p, "lam"))},
        {"name": "alpha", "value": float(getattr(p, "alpha"))},
        {"name": "p_exp", "value": float(getattr(p, "p"))},
        {"name": "N_scale", "value": float(getattr(p, "N_scale"))},
    ]


def _decay_gamma_12_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "lam", "value": float(getattr(p, "lam0"))},
        {"name": "eps", "value": float(getattr(p, "eps"))},
        {"name": "omega", "value": float(getattr(p, "omega"))},
    ]


def _decay_delta_12_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "lam", "value": float(getattr(p, "lam"))},
        {"name": "xi", "value": float(getattr(p, "xi"))},
    ]


def _damped_ho_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "c", "value": float(getattr(p, "c"))},
        {"name": "m", "value": float(getattr(p, "m"))},
    ]


def _damped_ho_gamma_3_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "omega_0", "value": float(getattr(p, "omega0"))},
        {"name": "gamma", "value": float(getattr(p, "gamma"))},
        {"name": "kappa", "value": float(getattr(p, "kappa"))},
        {"name": "x_ref", "value": float(getattr(p, "x_ref"))},
    ]


def _damped_ho_gamma_3_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "omega_0", "value": float(getattr(p, "omega0"))},
        {"name": "gamma", "value": float(getattr(p, "gamma"))},
        {"name": "eps", "value": float(getattr(p, "eps"))},
        {"name": "Omega_p", "value": float(getattr(p, "Omega_p"))},
    ]


def _damped_ho_delta_3_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "omega_0", "value": float(getattr(p, "omega0"))},
        {"name": "gamma", "value": float(getattr(p, "gamma"))},
        {"name": "L", "value": float(getattr(p, "L"))},
    ]


def _pendulum_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "g", "value": float(getattr(p, "g"))},
        {"name": "L", "value": float(getattr(p, "L"))},
    ]


def _pendulum_gamma_4_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "g_over_L", "value": float(getattr(p, "g_over_L"))},
        {"name": "alpha", "value": float(getattr(p, "alpha"))},
    ]


def _pendulum_gamma_4_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "g_over_L", "value": float(getattr(p, "g0_over_L"))},
        {"name": "alpha", "value": float(getattr(p, "alpha"))},
        {"name": "L", "value": float(getattr(p, "L"))},
        {"name": "H", "value": float(getattr(p, "H"))},
    ]


def _pendulum_delta_4_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "g_over_L", "value": float(getattr(p, "g0_over_L"))},
        {"name": "eps", "value": float(getattr(p, "eps"))},
        {"name": "Omega", "value": float(getattr(p, "Omega"))},
    ]


def _optics_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "n_1", "value": float(getattr(p, "n1"))},
        {"name": "n_2", "value": float(getattr(p, "n2"))},
    ]


def _optics_gamma_9_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "n_1", "value": float(getattr(p, "n1"))},
        {"name": "n_0", "value": float(getattr(p, "n0"))},
        {"name": "dn", "value": float(getattr(p, "dn"))},
        {"name": "phi", "value": float(getattr(p, "phi"))},
    ]


def _optics_gamma_9_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "n_1", "value": float(getattr(p, "n1"))},
        {"name": "n_2", "value": float(getattr(p, "n2"))},
        {"name": "kappa", "value": float(getattr(p, "kappa"))},
    ]


def _optics_delta_9_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "n_1", "value": float(getattr(p, "n1"))},
        {"name": "n_2", "value": float(getattr(p, "n2"))},
    ]


def _fluid_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "rho", "value": float(getattr(p, "rho"))},
        {"name": "g", "value": float(getattr(p, "g"))},
    ]


def _fluid_gamma_10_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "rho", "value": float(getattr(p, "rho"))},
        {"name": "g", "value": float(getattr(p, "g"))},
        {"name": "alpha", "value": float(getattr(p, "alpha"))},
    ]


def _fluid_gamma_10_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "rho", "value": float(getattr(p, "rho"))},
        {"name": "g", "value": float(getattr(p, "g"))},
        {"name": "h_0", "value": float(getattr(p, "h0"))},
        {"name": "lam", "value": float(getattr(p, "lam"))},
        {"name": "q", "value": float(getattr(p, "q"))},
    ]


def _fluid_delta_10_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "rho", "value": float(getattr(p, "rho"))},
        {"name": "g", "value": float(getattr(p, "g"))},
        {"name": "zeta", "value": float(getattr(p, "zeta"))},
    ]


def _rlc_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "L", "value": float(getattr(p, "L"))},
        {"name": "R", "value": float(getattr(p, "R"))},
        {"name": "C", "value": float(getattr(p, "C"))},
    ]


def _rlc_gamma_6_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "L_0", "value": float(getattr(p, "L0"))},
        {"name": "R", "value": float(getattr(p, "R"))},
        {"name": "C", "value": float(getattr(p, "C"))},
        {"name": "I_sat", "value": float(getattr(p, "I_sat"))},
    ]


def _rlc_gamma_6_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "L_1", "value": float(getattr(p, "L1"))},
        {"name": "L_2", "value": float(getattr(p, "L2"))},
        {"name": "R_1", "value": float(getattr(p, "R1"))},
        {"name": "R_2", "value": float(getattr(p, "R2"))},
        {"name": "C_1", "value": float(getattr(p, "C1"))},
        {"name": "C_2", "value": float(getattr(p, "C2"))},
        {"name": "M_0", "value": float(getattr(p, "M0"))},
        {"name": "dM", "value": float(getattr(p, "dM"))},
    ]


def _rlc_delta_6_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "L_0", "value": float(getattr(p, "L0"))},
        {"name": "R", "value": float(getattr(p, "R"))},
        {"name": "C", "value": float(getattr(p, "C"))},
        {"name": "eps", "value": float(getattr(p, "eps"))},
        {"name": "Omega_p", "value": float(getattr(p, "Omega_p"))},
    ]


def _wave_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "A", "value": float(getattr(p, "A"))},
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "c", "value": float(getattr(p, "c"))},
        {"name": "phi", "value": float(getattr(p, "phi"))},
    ]


def _wave_gamma_8_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "A", "value": float(getattr(p, "A"))},
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "c", "value": float(getattr(p, "c"))},
        {"name": "gamma", "value": float(getattr(p, "gamma"))},
    ]


def _wave_gamma_8_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "A", "value": float(getattr(p, "A"))},
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "c", "value": float(getattr(p, "c"))},
        {"name": "beta", "value": float(getattr(p, "beta"))},
    ]


def _wave_delta_8_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "A", "value": float(getattr(p, "A"))},
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "c", "value": float(getattr(p, "c"))},
        {"name": "alpha", "value": float(getattr(p, "alpha0"))},
        {"name": "u_ref", "value": float(getattr(p, "u_ref"))},
    ]


def _kinetics_baseline_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "n", "value": float(getattr(p, "n"))},
        {"name": "C0", "value": float(getattr(p, "C0"))},
    ]


def _kinetics_gamma_11_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "n", "value": float(getattr(p, "n"))},
        {"name": "beta", "value": float(getattr(p, "beta"))},
    ]


def _kinetics_gamma_11_2_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "n", "value": float(getattr(p, "n"))},
        {"name": "m_exp", "value": float(getattr(p, "m"))},
        {"name": "C_sat", "value": float(getattr(p, "C_sat"))},
    ]


def _kinetics_delta_11_1_params(scenario: ScenarioInstance) -> List[Dict[str, Any]]:
    p = scenario.sim.params
    return [
        {"name": "k", "value": float(getattr(p, "k"))},
        {"name": "n", "value": float(getattr(p, "n"))},
        {"name": "eta", "value": float(getattr(p, "eta"))},
    ]


_DECLARED_PARAMS: Dict[Tuple[str, str], Callable[[ScenarioInstance], List[Dict[str, Any]]]] = {
    ("gravity", "baseline"): _gravity_baseline_params,
    ("gravity", "gamma_2_1"): _gravity_gamma_2_1_params,
    ("gravity", "gamma_2_2"): _gravity_gamma_2_2_params,
    ("gravity", "delta_2_1"): _gravity_delta_2_1_params,
    ("hooke", "baseline"): _hooke_baseline_params,
    ("hooke", "gamma_1_1"): _hooke_gamma_1_1_params,
    ("hooke", "gamma_1_2"): _hooke_gamma_1_2_params,
    ("hooke", "delta_1_1"): _hooke_delta_1_1_params,
    ("coulomb", "baseline"): _coulomb_baseline_params,
    ("coulomb", "gamma_5_1"): _coulomb_gamma_5_1_params,
    ("coulomb", "gamma_5_2"): _coulomb_gamma_5_2_params,
    ("coulomb", "delta_5_1"): _coulomb_delta_5_1_params,
    ("thermal", "baseline"): _thermal_baseline_params,
    ("thermal", "gamma_7_1"): _thermal_gamma_7_1_params,
    ("thermal", "gamma_7_2"): _thermal_gamma_7_2_params,
    ("thermal", "delta_7_1"): _thermal_delta_7_1_params,
    ("decay", "baseline"): _decay_baseline_params,
    ("decay", "gamma_12_1"): _decay_gamma_12_1_params,
    ("decay", "gamma_12_2"): _decay_gamma_12_2_params,
    ("decay", "delta_12_1"): _decay_delta_12_1_params,
    ("damped_ho", "baseline"): _damped_ho_baseline_params,
    ("damped_ho", "gamma_3_1"): _damped_ho_gamma_3_1_params,
    ("damped_ho", "gamma_3_2"): _damped_ho_gamma_3_2_params,
    ("damped_ho", "delta_3_1"): _damped_ho_delta_3_1_params,
    ("pendulum", "baseline"): _pendulum_baseline_params,
    ("pendulum", "gamma_4_1"): _pendulum_gamma_4_1_params,
    ("pendulum", "gamma_4_2"): _pendulum_gamma_4_2_params,
    ("pendulum", "delta_4_1"): _pendulum_delta_4_1_params,
    ("optics", "baseline"): _optics_baseline_params,
    ("optics", "gamma_9_1"): _optics_gamma_9_1_params,
    ("optics", "gamma_9_2"): _optics_gamma_9_2_params,
    ("optics", "delta_9_1"): _optics_delta_9_1_params,
    ("fluid", "baseline"): _fluid_baseline_params,
    ("fluid", "gamma_10_1"): _fluid_gamma_10_1_params,
    ("fluid", "gamma_10_2"): _fluid_gamma_10_2_params,
    ("fluid", "delta_10_1"): _fluid_delta_10_1_params,
    ("rlc", "baseline"): _rlc_baseline_params,
    ("rlc", "gamma_6_1"): _rlc_gamma_6_1_params,
    ("rlc", "gamma_6_2"): _rlc_gamma_6_2_params,
    ("rlc", "delta_6_1"): _rlc_delta_6_1_params,
    ("wave", "baseline"): _wave_baseline_params,
    ("wave", "gamma_8_1"): _wave_gamma_8_1_params,
    ("wave", "gamma_8_2"): _wave_gamma_8_2_params,
    ("wave", "delta_8_1"): _wave_delta_8_1_params,
    ("kinetics", "baseline"): _kinetics_baseline_params,
    ("kinetics", "gamma_11_1"): _kinetics_gamma_11_1_params,
    ("kinetics", "gamma_11_2"): _kinetics_gamma_11_2_params,
    ("kinetics", "delta_11_1"): _kinetics_delta_11_1_params,
}


_BROKEN_SYMMETRY: Dict[tuple[str, str], str] = {
    # Catalog R2-final labels. None means no labeled break (baseline).
    ("hooke", "gamma_1_1"): "PAR",
    ("hooke", "gamma_1_2"): "ROT",
    ("hooke", "delta_1_1"): "TR",
    ("gravity", "gamma_2_1"): "ROT",
    ("gravity", "gamma_2_2"): "SCALE",
    ("gravity", "delta_2_1"): "T_TRANS",
    ("damped_ho", "gamma_3_1"): "SCALE",
    ("damped_ho", "gamma_3_2"): "T_TRANS",
    ("damped_ho", "delta_3_1"): "TR",
    ("pendulum", "gamma_4_1"): "PAR",
    ("pendulum", "gamma_4_2"): "SCALE",
    ("pendulum", "delta_4_1"): "T_TRANS",
    ("coulomb", "gamma_5_1"): "ROT",
    ("coulomb", "gamma_5_2"): "ROT",
    ("coulomb", "delta_5_1"): "T_TRANS",
    ("rlc", "gamma_6_1"): "SCALE",
    ("rlc", "gamma_6_2"): "ROT",
    ("rlc", "delta_6_1"): "T_TRANS",
    ("thermal", "gamma_7_1"): "ROT",
    ("thermal", "gamma_7_2"): "T_TRANS",
    ("thermal", "delta_7_1"): "T_TRANS",
    ("wave", "gamma_8_1"): "SCALE",
    ("wave", "gamma_8_2"): "ROT",
    ("wave", "delta_8_1"): "T_TRANS",
    ("optics", "gamma_9_1"): "ROT",
    ("optics", "gamma_9_2"): "PAR",
    ("optics", "delta_9_1"): "T_TRANS",
    ("fluid", "gamma_10_1"): "SCALE",
    ("fluid", "gamma_10_2"): "ROT",
    ("fluid", "delta_10_1"): "T_TRANS",
    ("kinetics", "gamma_11_1"): "SCALE",
    ("kinetics", "gamma_11_2"): "T_TRANS",
    ("kinetics", "delta_11_1"): "T_TRANS",
    ("decay", "gamma_12_1"): "T_TRANS",
    ("decay", "gamma_12_2"): "SCALE",
    ("decay", "delta_12_1"): "T_TRANS",
}


def broken_symmetry_for(domain_id: str, shift_id: str) -> str:
    """Return the canonical broken-symmetry label.

    Baseline scenarios return ``"none"`` per spec §6.3.
    """
    if shift_id == "baseline":
        return "none"
    return _BROKEN_SYMMETRY.get((domain_id, shift_id), "none")


def build_submission(scenario: ScenarioInstance) -> Submission:
    """Return a §5-compliant 1-entry submission wrapping the catalog law.

    The entry uses an embedded callable (``_predictor``) so the eval can
    call it directly without ``exec``-ing reconstructed code. A trivial
    ``predictor.code`` stub is still attached to satisfy the schema for
    downstream consumers that re-serialize the submission.
    """
    builder = _DISPATCH.get(scenario.domain_id)
    if builder is None:
        raise KeyError(f"no ceiling predictor registered for domain {scenario.domain_id!r}")
    predictor = builder(scenario)
    inputs, outputs = _dim_units(scenario)
    sym = broken_symmetry_for(scenario.domain_id, scenario.shift_id)
    declared = _DECLARED_PARAMS.get((scenario.domain_id, scenario.shift_id))
    params = declared(scenario) if declared is not None else []
    entry: Dict[str, Any] = {
        "law_id": "L1",
        "formula": "oracle: catalog law wrapped via closure",
        "predictor": {
            "lang": "python",
            "code": "def f(**kw):\n    raise RuntimeError('use _predictor closure')\n",
        },
        "_predictor": predictor,
        "inputs": inputs,
        "outputs": outputs,
        "params": params,
        "claim_broken_symmetry": sym,
    }
    return [entry]


class CeilingAgent:
    """Oracle agent — no LLM, no tool calls."""

    def run(self, scenario: ScenarioInstance) -> Submission:
        return build_submission(scenario)


__all__ = [
    "CeilingAgent",
    "build_submission",
    "broken_symmetry_for",
]
