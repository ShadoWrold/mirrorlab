"""Scenario loader.

Combines a registry-built ``SimInstance`` with the agent-visible prompt and
the held-out test grids that the evaluator (§6) consumes.

Sprint 3 wires up all 12 domains. Sub-grids (a) and (b) remain placeholders
(calibration deferred to CAL-1/CAL-2). Sub-grid (c) is the counterfactual
probe: per-point perturbed-parameter law values, implemented by
``mirrorlab.scenarios.counterfactual.perturb_params`` (CAL-3 default ±30%).
The Hooke domain ships a fully wired set of (a)/(b)/(c) grids for the
Sprint 1 demo; other domains return empty placeholders until their per-
domain natural amplitudes are nailed down.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from mirrorlab.domains.coulomb import DIM_SIGNATURE as COULOMB_DIM
from mirrorlab.domains.damped_ho import DIM_SIGNATURE as DAMPED_HO_DIM
from mirrorlab.domains.decay import DIM_SIGNATURE as DECAY_DIM
from mirrorlab.domains.fluid import DIM_SIGNATURE as FLUID_DIM
from mirrorlab.domains.gravity import DIM_SIGNATURE as GRAVITY_DIM
from mirrorlab.domains.hooke import DIM_SIGNATURE as HOOKE_DIM_SIG
from mirrorlab.domains.hooke import SimInstance
from mirrorlab.domains.kinetics import DIM_SIGNATURE as KINETICS_DIM
from mirrorlab.domains.optics import DIM_SIGNATURE as OPTICS_DIM
from mirrorlab.domains.pendulum import DIM_SIGNATURE as PENDULUM_DIM
from mirrorlab.domains.rlc import DIM_SIGNATURE as RLC_DIM
from mirrorlab.domains.thermal import DIM_SIGNATURE as THERMAL_DIM
from mirrorlab.domains.wave import DIM_SIGNATURE as WAVE_DIM
from mirrorlab.scenarios import prompts
from mirrorlab.scenarios import loader_shifts as _shifts
from mirrorlab.scenarios.counterfactual import DEFAULT_MAGNITUDE, perturb_params
from mirrorlab.scenarios.registry import make as _make_sim

_DOMAIN_PROMPT_BUILDERS = {
    "hooke": prompts.hooke_prompt,
    "damped_ho": prompts.damped_ho_prompt,
    "gravity": prompts.gravity_prompt,
    "coulomb": prompts.coulomb_prompt,
    "pendulum": prompts.pendulum_prompt,
    "rlc": prompts.rlc_prompt,
    "thermal": prompts.thermal_prompt,
    "wave": prompts.wave_prompt,
    "optics": prompts.optics_prompt,
    "fluid": prompts.fluid_prompt,
    "kinetics": prompts.kinetics_prompt,
    "decay": prompts.decay_prompt,
}

_DOMAIN_OBSERVABLES = {
    "hooke": prompts.HOOKE_OBSERVABLES,
    "damped_ho": prompts.DAMPED_HO_OBSERVABLES,
    "gravity": prompts.GRAVITY_OBSERVABLES,
    "coulomb": prompts.COULOMB_OBSERVABLES,
    "pendulum": prompts.PENDULUM_OBSERVABLES,
    "rlc": prompts.RLC_OBSERVABLES,
    "thermal": prompts.THERMAL_OBSERVABLES,
    "wave": prompts.WAVE_OBSERVABLES,
    "optics": prompts.OPTICS_OBSERVABLES,
    "fluid": prompts.FLUID_OBSERVABLES,
    "kinetics": prompts.KINETICS_OBSERVABLES,
    "decay": prompts.DECAY_OBSERVABLES,
}

_DOMAIN_DIM = {
    "hooke": HOOKE_DIM_SIG,
    "damped_ho": DAMPED_HO_DIM,
    "gravity": GRAVITY_DIM,
    "coulomb": COULOMB_DIM,
    "pendulum": PENDULUM_DIM,
    "rlc": RLC_DIM,
    "thermal": THERMAL_DIM,
    "wave": WAVE_DIM,
    "optics": OPTICS_DIM,
    "fluid": FLUID_DIM,
    "kinetics": KINETICS_DIM,
    "decay": DECAY_DIM,
}


@dataclass(frozen=True)
class ScenarioInstance:
    """Loader output: everything one scenario run needs.

    Attributes
    ----------
    domain_id, shift_id, seed
        Identifying triple. ``shift_id`` is opaque to the agent.
    sim
        Live ``SimInstance`` the agent (or rule-based stub) probes.
    prompt
        Agent-visible scenario description (no shift label, no formula hint).
    observables
        Names the prompt declares the agent may reference in submissions.
    dim_signature
        SI units of declared inputs / outputs / params — used by the
        evaluator's stage-1 dimensional pre-filter.
    test_grids
        Dict ``{"a": np.ndarray, "b": np.ndarray, "c": np.ndarray}`` of
        x-input sample points for §6.2 sub-grids (in-domain / OOD /
        counterfactual). Hooke wires all three for the Sprint 1 demo; other
        domains return ``{}`` until per-domain amplitudes are nailed down.
    counterfactual_params
        Tuple of perturbed-parameter dataclasses, one per point in
        ``test_grids["c"]``.
    counterfactual_magnitude
        CAL-3 perturbation magnitude actually used.
    """

    domain_id: str
    shift_id: str
    seed: int
    sim: Any
    prompt: str
    observables: Tuple[str, ...]
    dim_signature: Dict[str, Dict[str, str]]
    test_grids: Dict[str, np.ndarray] = field(default_factory=dict)
    counterfactual_params: Tuple[Any, ...] = ()
    counterfactual_magnitude: float = DEFAULT_MAGNITUDE


def _hooke_test_grids(
    sim: SimInstance, seed: int, magnitude: float
) -> tuple[Dict[str, np.ndarray], Tuple[Any, ...]]:
    """Sprint-1 placeholder (a)(b) plus counterfactual (c)."""
    x_amp = float(abs(getattr(sim.params, "x0", 1.0)) or 1.0)
    rng = np.random.default_rng(seed + 1)
    grid_a = np.linspace(-x_amp, x_amp, 11)
    grid_b = np.concatenate(
        [
            np.linspace(-5.0 * x_amp, -1.5 * x_amp, 5),
            np.linspace(1.5 * x_amp, 5.0 * x_amp, 5),
        ]
    )
    grid_c = rng.uniform(-x_amp, x_amp, size=11)
    cf_rng = np.random.default_rng(seed + 2)
    cf_params = tuple(
        perturb_params(sim.params, magnitude=magnitude, rng=cf_rng)
        for _ in range(grid_c.size)
    )
    return {"a": grid_a, "b": grid_b, "c": grid_c}, cf_params


# ---- Sprint-3 generic grid helpers ------------------------------------------
#
# Pattern (mirrors `_hooke_test_grids`, but emits packed
# `(inputs_dict, ground_truth)` tuples ready for `evaluate_entry`):
#   (a)  in-domain inputs sampled from the training range
#   (b)  OOD inputs at CAL-2's 5x range
#   (c)  same inputs as (a), but GT recomputed under perturbed params
#
# GT formulas mirror `agent_stub`'s baseline-form predictor per domain. The
# point of (b)/(c) is comparison-against-self: a frozen-coefficient predictor
# cannot follow a re-instantiated law, while a re-evaluating physical model
# can. Whether the GT here matches the *true* shifted law in detail is not
# the point — it just has to be self-consistent and parameter-sensitive.

_GRID_SIZE = 11
_OOD_FACTOR = 5.0  # CAL-2 default


def _attr(p: Any, names: Sequence[str], default: float) -> float:
    for n in names:
        if hasattr(p, n):
            try:
                v = float(getattr(p, n))
                if math.isfinite(v):
                    return v
            except (TypeError, ValueError):
                continue
    return float(default)


def _pack(rng_seed: int, magnitude: float, sim: Any, build: Any) -> tuple[
    Dict[str, List[Any]], Tuple[Any, ...]
]:
    """Shared scaffold: build (a,b,c) sub-grids via the domain-supplied ``build``.

    ``build(rng, mode)`` returns a list of ``(inputs_dict, gt_fn)`` pairs where
    ``gt_fn`` accepts the params object and returns a scalar GT. Modes are
    ``"a"`` (in-domain), ``"b"`` (OOD), ``"c"`` (same inputs as a).

    Per blueprint-xy §2.3: grid_c is a list of 3-tuples
    ``(inputs_dict, gt_scalar, cf_params_obj)``. (a)/(b) remain 2-tuples —
    they have no per-point param perturbation. The ``cf_params_obj`` is the
    same instance used to compute the GT, so downstream consumers in
    ``eval/numeric.py`` can override declared predictor params with the
    matching perturbation on a per-point basis.
    """
    rng_a = np.random.default_rng(rng_seed + 1)
    rng_b = np.random.default_rng(rng_seed + 3)
    cf_rng = np.random.default_rng(rng_seed + 2)
    pts_a = build(rng_a, "a")
    pts_b = build(rng_b, "b")
    pts_c_inputs = [ins for ins, _ in pts_a]  # mirror (a)'s input points
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


def _linspace_signed(amp: float, n: int) -> np.ndarray:
    return np.linspace(-amp, amp, n)


def _ood_signed(amp: float, n: int) -> np.ndarray:
    half = max(1, n // 2)
    return np.concatenate(
        [
            np.linspace(-_OOD_FACTOR * amp, -1.5 * amp, half),
            np.linspace(1.5 * amp, _OOD_FACTOR * amp, n - half),
        ]
    )


# ---- Per-domain helpers -----------------------------------------------------

def _damped_ho_test_grids(sim, seed, magnitude):
    x_amp = abs(_attr(sim.params, ("x0",), 0.1)) or 0.1
    omega0 = _attr(sim.params, ("omega0",), math.sqrt(_attr(sim.params, ("k",), 1.0) / _attr(sim.params, ("m",), 1.0)))
    v_amp = omega0 * x_amp if omega0 > 0 else 1.0

    def gt(inputs):
        def fn(p):
            m = _attr(p, ("m",), 1.0)
            k = _attr(p, ("k",), _attr(p, ("omega0",), 1.0) ** 2 * m)
            c = _attr(p, ("c",), 2.0 * _attr(p, ("gamma",), 0.0) * m)
            return -k * inputs["x"] - c * inputs["v"]
        return fn

    def build(rng, mode):
        if mode == "b":
            xs = _ood_signed(x_amp, _GRID_SIZE)
            vs = _ood_signed(v_amp, _GRID_SIZE)
        else:
            xs = _linspace_signed(x_amp, _GRID_SIZE)
            vs = rng.uniform(-v_amp, v_amp, size=_GRID_SIZE)
        return [({"x": float(x), "v": float(v)}, gt({"x": float(x), "v": float(v)})) for x, v in zip(xs, vs)]

    return _pack(seed, magnitude, sim, build)


def _gravity_test_grids(sim, seed, magnitude):
    r0 = _attr(sim.params, ("r0",), 1.0e7) or 1.0e7

    def gt(inputs):
        def fn(p):
            G = _attr(p, ("G", "G0"), 6.6743e-11)
            M = _attr(p, ("M",), 1.0)
            m = _attr(p, ("m",), 1.0)
            r = inputs["r"]
            return -G * M * m / (r * r)
        return fn

    def build(rng, mode):
        if mode == "b":
            rs = np.linspace(_OOD_FACTOR * r0, (_OOD_FACTOR + 4.0) * r0, _GRID_SIZE)
        else:
            rs = np.linspace(0.5 * r0, 1.5 * r0, _GRID_SIZE)
        return [({"r": float(r)}, gt({"r": float(r)})) for r in rs]

    return _pack(seed, magnitude, sim, build)


def _coulomb_test_grids(sim, seed, magnitude):
    r0 = _attr(sim.params, ("r0",), 1.0) or 1.0

    def gt(inputs):
        def fn(p):
            k_e = _attr(p, ("k_e",), 8.9875517873681764e9)
            q1 = _attr(p, ("q1", "q_src", "src1_q"), 1.0e-9)
            q2 = _attr(p, ("q2", "q_test", "src2_q"), 1.0e-9)
            r = inputs["r"]
            return k_e * q1 * q2 / (r * r)
        return fn

    def build(rng, mode):
        if mode == "b":
            rs = np.linspace(_OOD_FACTOR * r0, (_OOD_FACTOR + 4.0) * r0, _GRID_SIZE)
        else:
            rs = np.linspace(0.5 * r0, 1.5 * r0, _GRID_SIZE)
        return [({"r": float(r)}, gt({"r": float(r)})) for r in rs]

    return _pack(seed, magnitude, sim, build)


def _pendulum_test_grids(sim, seed, magnitude):
    theta_amp = abs(_attr(sim.params, ("theta0",), 0.3)) or 0.3
    theta_amp = min(theta_amp * 4.0, 0.8)  # in-domain stays small-angle-ish

    def gt(inputs):
        def fn(p):
            g_over_L = _attr(
                p,
                ("g_over_L", "g0_over_L"),
                _attr(p, ("g",), 9.81) / max(_attr(p, ("L",), 1.0), 1e-9),
            )
            return -g_over_L * math.sin(inputs["theta"])
        return fn

    def build(rng, mode):
        if mode == "b":
            # OOD: large angles where sin(theta) ≠ theta is dramatic, capped at ~1.5 rad.
            ood_amp = min(_OOD_FACTOR * theta_amp, 1.5)
            thetas = _ood_signed(ood_amp, _GRID_SIZE)
        else:
            thetas = _linspace_signed(theta_amp, _GRID_SIZE)
        return [({"theta": float(th)}, gt({"theta": float(th)})) for th in thetas]

    return _pack(seed, magnitude, sim, build)


def _rlc_test_grids(sim, seed, magnitude):
    q_amp = abs(_attr(sim.params, ("q0",), 1e-6)) or 1e-6
    i_amp = abs(_attr(sim.params, ("i0",), 1e-3)) or 1e-3
    # Estimate didt magnitude from V/L scale: V ~ q/C, didt ~ V/L.
    L_est = _attr(sim.params, ("L", "L0", "L1"), 1e-3)
    C_est = _attr(sim.params, ("C", "C1"), 1e-6)
    didt_amp = (q_amp / C_est) / max(L_est, 1e-12) if L_est > 0 else 1.0

    def gt(inputs):
        def fn(p):
            L = _attr(p, ("L", "L0", "L1"), 1.0)
            R = _attr(p, ("R", "R1"), 1.0)
            C = _attr(p, ("C", "C1"), 1.0e-6)
            return L * inputs["didt"] + R * inputs["i"] + inputs["q"] / max(C, 1e-30)
        return fn

    def build(rng, mode):
        scale = _OOD_FACTOR if mode == "b" else 1.0
        qs = rng.uniform(-scale * q_amp, scale * q_amp, size=_GRID_SIZE)
        if mode == "b":
            qs = np.where(np.abs(qs) < 1.5 * q_amp, np.sign(qs) * 1.5 * q_amp, qs)
        i_arr = rng.uniform(-scale * i_amp, scale * i_amp, size=_GRID_SIZE)
        didt_arr = rng.uniform(-scale * didt_amp, scale * didt_amp, size=_GRID_SIZE)
        pts = []
        for q, i_, dd in zip(qs, i_arr, didt_arr):
            ins = {"i": float(i_), "didt": float(dd), "q": float(q)}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


def _thermal_test_grids(sim, seed, magnitude):
    T_hot0 = _attr(sim.params, ("T_hot",), 373.0)
    T_cold0 = _attr(sim.params, ("T_cold",), 293.0)
    L0 = _attr(sim.params, ("L", "dx"), 0.1) or 0.1
    dT = max(abs(T_hot0 - T_cold0), 1.0)

    def gt(inputs):
        def fn(p):
            k = _attr(p, ("k", "k0", "alpha"), 1.0)
            return k * (inputs["T_hot"] - inputs["T_cold"]) / max(inputs["L"], 1e-12)
        return fn

    def build(rng, mode):
        if mode == "b":
            # OOD: amplify hot-cold gap and thin/thick slab.
            T_hot = rng.uniform(T_hot0, T_hot0 + _OOD_FACTOR * dT, size=_GRID_SIZE)
            T_cold = rng.uniform(T_cold0 - _OOD_FACTOR * dT, T_cold0, size=_GRID_SIZE)
            Ls = rng.uniform(L0 / _OOD_FACTOR, L0 * _OOD_FACTOR, size=_GRID_SIZE)
        else:
            T_hot = rng.uniform(T_hot0 - 0.1 * dT, T_hot0 + 0.1 * dT, size=_GRID_SIZE)
            T_cold = rng.uniform(T_cold0 - 0.1 * dT, T_cold0 + 0.1 * dT, size=_GRID_SIZE)
            Ls = rng.uniform(0.8 * L0, 1.2 * L0, size=_GRID_SIZE)
        pts = []
        for th, tc, L in zip(T_hot, T_cold, Ls):
            ins = {"T_hot": float(th), "T_cold": float(tc), "L": float(L)}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


def _wave_test_grids(sim, seed, magnitude):
    # Fix probe x via sim.params.x_probe if set (baseline) — else sample x in 1 wavelength.
    k_est = _attr(sim.params, ("k",), 1.0) or 1.0
    c_est = _attr(sim.params, ("c",), 1.0) or 1.0
    lam = 2.0 * math.pi / k_est
    T = lam / c_est
    x_probe = _attr(sim.params, ("x_probe",), 0.5)

    def gt(inputs):
        def fn(p):
            A = _attr(p, ("A",), 1.0)
            k = _attr(p, ("k",), 1.0)
            c = _attr(p, ("c",), 1.0)
            phi = _attr(p, ("phi",), 0.0)
            return A * math.cos(k * inputs["x"] - c * k * inputs["t"] + phi)
        return fn

    def build(rng, mode):
        scale = _OOD_FACTOR if mode == "b" else 1.0
        ts = rng.uniform(0.0, scale * T, size=_GRID_SIZE)
        xs = rng.uniform(x_probe - scale * lam / 2, x_probe + scale * lam / 2, size=_GRID_SIZE)
        pts = []
        for x, t in zip(xs, ts):
            ins = {"x": float(x), "t": float(t)}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


def _optics_test_grids(sim, seed, magnitude):
    th0 = abs(_attr(sim.params, ("theta1",), 0.3)) or 0.3
    in_amp = min(max(th0, 0.1), 0.5)  # rad
    ood_amp = min(_OOD_FACTOR * in_amp, math.pi / 2 - 0.05)

    def gt(inputs):
        def fn(p):
            n1 = _attr(p, ("n1",), 1.0)
            n2 = _attr(p, ("n2", "n0"), 1.0)
            s = (n1 / max(n2, 1e-12)) * math.sin(inputs["theta1"])
            s = max(-1.0, min(1.0, s))  # clamp to avoid NaN past critical angle
            return math.asin(s)
        return fn

    def build(rng, mode):
        amp = ood_amp if mode == "b" else in_amp
        thetas = np.linspace(-amp, amp, _GRID_SIZE)
        return [({"theta1": float(th)}, gt({"theta1": float(th)})) for th in thetas]

    return _pack(seed, magnitude, sim, build)


def _fluid_test_grids(sim, seed, magnitude):
    # rho, g come from params. (p1, v1, v2, h1, h2) are inputs — sample around
    # the baseline-defined scales.
    p1_0 = _attr(sim.params, ("p1",), 1.01e5)
    v_scale = _attr(sim.params, ("v1",), 1.0) or 1.0
    h_scale = max(_attr(sim.params, ("h1",), 1.0), 0.1)

    def gt(inputs):
        def fn(p):
            rho = _attr(p, ("rho",), 1000.0)
            g = _attr(p, ("g",), 9.81)
            return (
                inputs["p1"]
                + 0.5 * rho * (inputs["v1"] ** 2 - inputs["v2"] ** 2)
                + rho * g * (inputs["h1"] - inputs["h2"])
            )
        return fn

    def build(rng, mode):
        scale = _OOD_FACTOR if mode == "b" else 1.0
        p1s = rng.uniform(0.9 * p1_0, 1.1 * p1_0, size=_GRID_SIZE)
        v1s = rng.uniform(0.5 * v_scale, scale * 2.0 * v_scale, size=_GRID_SIZE)
        v2s = rng.uniform(0.5 * v_scale, scale * 2.0 * v_scale, size=_GRID_SIZE)
        h1s = rng.uniform(0.5 * h_scale, scale * 2.0 * h_scale, size=_GRID_SIZE)
        h2s = rng.uniform(0.0, scale * h_scale, size=_GRID_SIZE)
        pts = []
        for p1, v1, v2, h1, h2 in zip(p1s, v1s, v2s, h1s, h2s):
            ins = {"p1": float(p1), "v1": float(v1), "v2": float(v2),
                   "h1": float(h1), "h2": float(h2)}
            pts.append((ins, gt(ins)))
        return pts

    return _pack(seed, magnitude, sim, build)


def _kinetics_test_grids(sim, seed, magnitude):
    C0 = abs(_attr(sim.params, ("C0",), 1.0)) or 1.0

    def gt(inputs):
        def fn(p):
            k = _attr(p, ("k",), 0.1)
            n = _attr(p, ("n",), 1.0)
            C = max(inputs["C"], 0.0)
            return -k * (C ** n)
        return fn

    def build(rng, mode):
        if mode == "b":
            Cs = np.linspace(C0, _OOD_FACTOR * C0, _GRID_SIZE)
        else:
            Cs = np.linspace(0.05 * C0, C0, _GRID_SIZE)
        return [({"C": float(C)}, gt({"C": float(C)})) for C in Cs]

    return _pack(seed, magnitude, sim, build)


def _decay_test_grids(sim, seed, magnitude):
    N0 = abs(_attr(sim.params, ("N0",), 1.0e6)) or 1.0e6

    def gt(inputs):
        def fn(p):
            lam = _attr(p, ("lam", "lam0"), 0.1)
            return -lam * inputs["N"]
        return fn

    def build(rng, mode):
        if mode == "b":
            Ns = np.linspace(N0, _OOD_FACTOR * N0, _GRID_SIZE)
        else:
            Ns = np.linspace(0.05 * N0, N0, _GRID_SIZE)
        return [({"N": float(N)}, gt({"N": float(N)})) for N in Ns]

    return _pack(seed, magnitude, sim, build)


_NON_HOOKE_GRID_BUILDERS = {
    "damped_ho": _damped_ho_test_grids,
    "gravity": _gravity_test_grids,
    "coulomb": _coulomb_test_grids,
    "pendulum": _pendulum_test_grids,
    "rlc": _rlc_test_grids,
    "thermal": _thermal_test_grids,
    "wave": _wave_test_grids,
    "optics": _optics_test_grids,
    "fluid": _fluid_test_grids,
    "kinetics": _kinetics_test_grids,
    "decay": _decay_test_grids,
}


def load(
    domain_id: str,
    shift_id: str,
    *,
    seed: int = 0,
    params: Any | None = None,
    counterfactual_magnitude: float = DEFAULT_MAGNITUDE,
) -> ScenarioInstance:
    """Build a fully-formed scenario for the requested ``(domain_id, shift_id)``."""
    if domain_id not in _DOMAIN_PROMPT_BUILDERS:
        raise KeyError(
            f"no prompt template for domain {domain_id!r}; "
            f"registered: {sorted(_DOMAIN_PROMPT_BUILDERS)}"
        )
    sim = _make_sim(domain_id, shift_id, seed=seed, params=params)
    prompt = _DOMAIN_PROMPT_BUILDERS[domain_id]()
    observables = tuple(_DOMAIN_OBSERVABLES[domain_id])
    dim_signature = _DOMAIN_DIM[domain_id]
    # Post-T7 (blueprint §3.2): every (domain, shift) flows through the
    # loader_shifts dispatch table. The Sprint-1 hooke ndarray path
    # (``_hooke_test_grids``) is retained only as a no-op fallback when
    # no dispatch entry exists (e.g. an unregistered shift).
    if (domain_id, shift_id) in _shifts._GRID_BUILDERS:
        test_grids, cf_params = _shifts.get(domain_id, shift_id)(
            sim, seed, counterfactual_magnitude
        )
    elif domain_id == "hooke":
        # Legacy ndarray path — preserved for any hooke shift not yet
        # registered in loader_shifts. Should be unreachable after T7
        # since all 4 hooke shifts are registered.
        test_grids, cf_params = _hooke_test_grids(
            sim, seed, counterfactual_magnitude
        )
    else:
        test_grids, cf_params = {}, ()
    return ScenarioInstance(
        domain_id=domain_id,
        shift_id=shift_id,
        seed=seed,
        sim=sim,
        prompt=prompt,
        observables=observables,
        dim_signature=dim_signature,
        test_grids=test_grids,
        counterfactual_params=cf_params,
        counterfactual_magnitude=counterfactual_magnitude,
    )


__all__ = ["ScenarioInstance", "load"]


# Populate the per-(domain, shift) dispatch table with the legacy per-
# domain builders. Per-shift truth-form modules (T3+) call
# ``_shifts.register(...)`` from their import and override individual
# entries. This call must happen after ``_NON_HOOKE_GRID_BUILDERS`` is
# defined above so it can be read.
_shifts.register_legacy_dispatch()
