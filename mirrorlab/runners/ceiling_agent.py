"""Oracle ceiling agent for Sprint 4.

Given the catalog ground-truth law (read directly from the shift module's
``shifted_force`` / ``shifted_law`` or, for baselines, the domain class's
canonical force law), build a §5-compliant submission that uses a callable
predictor wrapping that law. No LLM, no tool calls.

This sets the *bench ceiling*: it answers "if an agent had perfect
knowledge of the law and parameters, what S_scen could it reach?" — which
tells us whether sub-baseline scores from real LLMs are LLM-limited or
bench-limited.

For shifts whose true law signature requires inputs the test grid does
not expose (e.g. 3-D anisotropic shifts, time-dependent shifts that pass
no ``t`` input through the grid), the predictor falls back to the
baseline-form law evaluated with the shift's params — i.e. the strongest
predictor expressible in the grid's input vocabulary. This is honest:
those gaps are real bench-design limitations and should surface as low
ceiling scores in the report.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Mapping, Optional

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
    sim = scenario.sim
    p = sim.params
    shift_id = scenario.shift_id

    if shift_id == "delta_1_1":
        def pred(**kw):
            x = float(kw.get("x", 0.0))
            v = float(kw.get("v", 0.0))
            try:
                return float(hooke_d_1_1.shifted_force(x, v, p))
            except Exception:
                return -_attr(p, ("k",), 1.0) * x
        return pred

    if shift_id == "gamma_1_1":
        def pred(**kw):
            x = float(kw.get("x", 0.0))
            try:
                return float(hooke_g_1_1.shifted_force(x, p))
            except Exception:
                return -_attr(p, ("k",), 1.0) * x
        return pred

    if shift_id == "gamma_1_2":
        # 2-D shift; grid only exposes scalar x. Project onto the (x,0)
        # axis: shifted_force((x,0), p)[0] is the x-component.
        def pred(**kw):
            x = float(kw.get("x", 0.0))
            try:
                fx, _ = hooke_g_1_2.shifted_force((x, 0.0), p)
                return float(fx)
            except Exception:
                return -_attr(p, ("k",), 1.0) * x
        return pred

    # Baseline: F = -k x.
    def pred(**kw):
        x = float(kw.get("x", 0.0))
        return -_attr(p, ("k",), 1.0) * x
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

    # baseline + γ-2-1 (3-D anisotropic → use scalar baseline form).
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
        "params": [],
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
