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
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_3_2":
        # F(x, v, t): grid does not pass t → use t=0 snapshot.
        def pred(**kw):
            x = float(kw.get("x", 0.0))
            v = float(kw.get("v", 0.0))
            try:
                return float(damped_ho_g_3_2.shifted_law(x, v, 0.0, p))
            except Exception:
                k = _attr(p, ("k",), 1.0)
                c = _attr(p, ("c",), 0.0)
                return -k * x - c * v
        return pred

    # baseline, γ-3-1 (uses x2_mean: pass 0 as best static proxy), δ-3-1.
    def pred(**kw):
        x = float(kw.get("x", 0.0))
        v = float(kw.get("v", 0.0))
        if shift_id == "gamma_3_1":
            try:
                return float(damped_ho_g_3_1.shifted_law(x, v, 0.0, p))
            except Exception:
                pass
        if shift_id == "delta_3_1":
            try:
                return float(damped_ho_d_3_1.shifted_law(x, v, p))
            except Exception:
                pass
        # Baseline / fallback.
        k = _attr(p, ("k",), 1.0)
        c = _attr(p, ("c",), 0.0)
        return -k * x - c * v

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
        def pred(**kw):
            r = float(kw.get("r", 1.0))
            try:
                return float(gravity_g_2_2.shifted_force(r, p))
            except Exception:
                G = _attr(p, ("G", "G0"), 6.6743e-11)
                M = _attr(p, ("M",), 1.0)
                m = _attr(p, ("m",), 1.0)
                return -G * M * m / (r * r)
        return pred

    if shift_id == "delta_2_1":
        def pred(**kw):
            r = float(kw.get("r", 1.0))
            try:
                return float(gravity_d_2_1.shifted_force(r, 0.0, p))
            except Exception:
                G = _attr(p, ("G", "G0"), 6.6743e-11)
                M = _attr(p, ("M",), 1.0)
                m = _attr(p, ("m",), 1.0)
                return -G * M * m / (r * r)
        return pred

    # baseline (γ-2-1 handled above with full truth-form projection).
    def pred(**kw):
        r = float(kw.get("r", 1.0))
        G = _attr(p, ("G", "G0"), 6.6743e-11)
        M = _attr(p, ("M",), 1.0)
        m = _attr(p, ("m",), 1.0)
        return -G * M * m / (r * r)
    return pred


def _coulomb_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params

    def pred(**kw):
        r = float(kw.get("r", 1.0))
        k_e = _attr(p, ("k_e",), 8.9875517873681764e9)
        q1 = _attr(p, ("q1", "q_src", "src1_q"), 1.0e-9)
        q2 = _attr(p, ("q2", "q_test", "src2_q"), 1.0e-9)
        return k_e * q1 * q2 / (r * r)
    return pred


def _pendulum_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params
    shift_id = scenario.shift_id

    if shift_id == "gamma_4_1":
        def pred(**kw):
            th = float(kw.get("theta", 0.0))
            try:
                return float(pendulum_g_4_1.shifted_law(th, p))
            except Exception:
                gol = _attr(p, ("g_over_L", "g0_over_L"),
                            _attr(p, ("g",), 9.81) / max(_attr(p, ("L",), 1.0), 1e-9))
                return -gol * math.sin(th)
        return pred

    if shift_id == "gamma_4_2":
        def pred(**kw):
            th = float(kw.get("theta", 0.0))
            try:
                return float(pendulum_g_4_2.shifted_law(th, p))
            except Exception:
                gol = _attr(p, ("g_over_L",), 9.81)
                return -gol * math.sin(th)
        return pred

    if shift_id == "delta_4_1":
        def pred(**kw):
            th = float(kw.get("theta", 0.0))
            try:
                return float(pendulum_d_4_1.shifted_law(th, 0.0, p))
            except Exception:
                gol = _attr(p, ("g_over_L",), 9.81)
                return -gol * math.sin(th)
        return pred

    # baseline
    def pred(**kw):
        th = float(kw.get("theta", 0.0))
        gol = _attr(p, ("g_over_L", "g0_over_L"),
                    _attr(p, ("g",), 9.81) / max(_attr(p, ("L",), 1.0), 1e-9))
        return -gol * math.sin(th)
    return pred


def _rlc_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params

    # Test-grid GT for RLC uses the Kirchhoff voltage form
    # V = L·didt + R·i + q/C with the shift's L,R,C plugged in. The catalog
    # shifted_law functions for rlc_g_6_1 / rlc_d_6_1 return didt
    # (an acceleration), not V, so wrapping them here would mismatch the
    # eval channel. The strongest predictor expressible in the grid's
    # input vocabulary ({q, i, didt}) is the baseline Kirchhoff sum with
    # shift-provided params — i.e. exactly what GT computes.
    def pred(**kw):
        q = float(kw.get("q", 0.0))
        i = float(kw.get("i", 0.0))
        didt = float(kw.get("didt", 0.0))
        L = _attr(p, ("L", "L0", "L1"), 1.0e-3)
        R = _attr(p, ("R", "R1"), 1.0)
        C = _attr(p, ("C", "C1"), 1.0e-6)
        return L * didt + R * i + q / max(C, 1e-30)
    return pred


def _thermal_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params

    def pred(**kw):
        Th = float(kw.get("T_hot", 0.0))
        Tc = float(kw.get("T_cold", 0.0))
        L = float(kw.get("L", 1.0))
        k = _attr(p, ("k", "k0", "alpha"), 1.0)
        return k * (Th - Tc) / max(L, 1e-12)
    return pred


def _wave_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params

    def pred(**kw):
        x = float(kw.get("x", 0.0))
        t = float(kw.get("t", 0.0))
        A = _attr(p, ("A",), 1.0)
        k = _attr(p, ("k",), 1.0)
        c = _attr(p, ("c",), 1.0)
        phi = _attr(p, ("phi",), 0.0)
        return A * math.cos(k * x - c * k * t + phi)
    return pred


def _optics_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params

    def pred(**kw):
        th1 = float(kw.get("theta1", 0.0))
        n1 = _attr(p, ("n1",), 1.0)
        n2 = _attr(p, ("n2", "n0"), 1.0)
        s = (n1 / max(n2, 1e-12)) * math.sin(th1)
        s = max(-1.0, min(1.0, s))
        return math.asin(s)
    return pred


def _fluid_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params

    def pred(**kw):
        p1 = float(kw.get("p1", 0.0))
        v1 = float(kw.get("v1", 0.0))
        v2 = float(kw.get("v2", 0.0))
        h1 = float(kw.get("h1", 0.0))
        h2 = float(kw.get("h2", 0.0))
        rho = _attr(p, ("rho",), 1000.0)
        g = _attr(p, ("g",), 9.81)
        return p1 + 0.5 * rho * (v1 * v1 - v2 * v2) + rho * g * (h1 - h2)
    return pred


def _kinetics_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params

    def pred(**kw):
        C = max(float(kw.get("C", 0.0)), 0.0)
        k = _attr(p, ("k",), 0.1)
        n = _attr(p, ("n",), 1.0)
        return -k * (C ** n)
    return pred


def _decay_pred(scenario: ScenarioInstance) -> PredictorFn:
    p = scenario.sim.params

    def pred(**kw):
        N = float(kw.get("N", 0.0))
        lam = _attr(p, ("lam", "lam0"), 0.1)
        return -lam * N
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


_DECLARED_PARAMS: Dict[Tuple[str, str], Callable[[ScenarioInstance], List[Dict[str, Any]]]] = {
    ("gravity", "gamma_2_1"): _gravity_gamma_2_1_params,
    ("hooke", "baseline"): _hooke_baseline_params,
    ("hooke", "gamma_1_1"): _hooke_gamma_1_1_params,
    ("hooke", "gamma_1_2"): _hooke_gamma_1_2_params,
    ("hooke", "delta_1_1"): _hooke_delta_1_1_params,
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
