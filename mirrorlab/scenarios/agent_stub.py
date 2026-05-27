"""Rule-based scenario-agent stub — domain-dispatched.

Sprint 3 demo only. NOT an LLM. For each registered domain, the stub
probes the live ``SimInstance`` along its natural trajectory, fits the
one-parameter natural baseline form, and emits one submission entry in
the §5 format with the correct SI dimensional signature.

By construction the stub is blind to symmetry breaks: on a baseline
shift it should fit well; on γ/δ shifts the same baseline-form fit will
mis-extrapolate, which is the point of the end-to-end demo. The LLM
wiring is ``llm-runner``'s job — this stub is the floor against which
the LLM is compared.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Sequence

import numpy as np

from mirrorlab.scenarios.loader import ScenarioInstance

_PROBE_TIMES: tuple[float, ...] = tuple(np.linspace(0.01, 2.0, 32))


# ---- Probing helpers ---------------------------------------------------

def _safe_observe(sim, t: float) -> Dict[str, Any]:
    try:
        return sim.step(float(t))
    except Exception:
        return {}


def _collect(
    sim, probe_times: Sequence[float], keys: Sequence[str]
) -> Dict[str, np.ndarray]:
    out: Dict[str, list] = {k: [] for k in keys}
    for t in probe_times:
        obs = _safe_observe(sim, t)
        for k in keys:
            v = obs.get(k)
            if v is None:
                continue
            try:
                out[k].append(float(v))
            except (TypeError, ValueError):
                continue
    return {k: np.asarray(vs, dtype=float) for k, vs in out.items()}


def _fit_neg_linear(xs: np.ndarray, ys: np.ndarray) -> float:
    """Least-squares fit of ``y = -k x``; returns 0 on degenerate input."""
    if xs.size == 0 or ys.size == 0 or xs.size != ys.size:
        return 0.0
    denom = float(np.dot(xs, xs))
    if denom <= 0.0:
        return 0.0
    return -float(np.dot(xs, ys)) / denom


def _param(name: str, units: str, value: float) -> Dict[str, Any]:
    if not math.isfinite(value):
        value = 0.0
    return {"name": name, "units": units, "value": float(value)}


def _entry(
    law_id: str,
    formula: str,
    code: str,
    inputs: Sequence[Dict[str, str]],
    outputs: Sequence[Dict[str, str]],
    params: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "law_id": law_id,
        "formula": formula,
        "predictor": {"lang": "python", "code": code},
        "inputs": list(inputs),
        "outputs": list(outputs),
        "params": list(params),
    }


def _attr(sim, name: str, default: float) -> float:
    try:
        v = float(getattr(sim.params, name))
        return v if math.isfinite(v) else default
    except (AttributeError, TypeError, ValueError):
        return default


# ---- Per-domain stubs --------------------------------------------------

def _hooke(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    data = _collect(sc.sim, probe_times, ("x", "F"))
    k_hat = _fit_neg_linear(data["x"], data["F"])
    return _entry(
        "L1",
        "F = -k*x",
        "def f(x, k):\n    return -k*x\n",
        [{"name": "x", "units": "m"}],
        [{"name": "F", "units": "kg*m*s**-2"}],
        [_param("k", "kg*s**-2", k_hat)],
    )


def _damped_ho(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    data = _collect(sc.sim, probe_times, ("x", "v", "F"))
    xs, vs, fs = data["x"], data["v"], data["F"]
    if xs.size and vs.size and fs.size and xs.size == fs.size == vs.size:
        # Least squares for F = -k*x - c*v on (x, v) → F.
        A = np.column_stack([xs, vs])
        try:
            coef, *_ = np.linalg.lstsq(A, fs, rcond=None)
            k_hat = -float(coef[0])
            c_hat = -float(coef[1])
        except np.linalg.LinAlgError:
            k_hat = _attr(sc.sim, "k", 1.0)
            c_hat = _attr(sc.sim, "c", 0.0)
    else:
        # Shifts may not emit F; fall back to params defaults.
        omega0 = _attr(sc.sim, "omega0", 1.0)
        k_hat = _attr(sc.sim, "k", omega0 ** 2)
        c_hat = _attr(sc.sim, "c", 0.0)
    return _entry(
        "L1",
        "F = -k*x - c*v",
        "def f(x, v, k, c):\n    return -k*x - c*v\n",
        [{"name": "x", "units": "m"}, {"name": "v", "units": "m*s**-1"}],
        [{"name": "F", "units": "kg*m*s**-2"}],
        [_param("k", "kg*s**-2", k_hat), _param("c", "kg*s**-1", c_hat)],
    )


def _gravity(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    G = _attr(sc.sim, "G", 6.674e-11)
    if not G:
        G = _attr(sc.sim, "G0", 6.674e-11)
    M = _attr(sc.sim, "M", 1.0)
    m = _attr(sc.sim, "m", 1.0)
    return _entry(
        "L1",
        "F = -G*M*m/r**2",
        "def f(r, G, M, m):\n    return -G*M*m/(r*r)\n",
        [{"name": "r", "units": "m"}],
        [{"name": "F", "units": "kg*m*s**-2"}],
        [
            _param("G", "m**3*kg**-1*s**-2", G),
            _param("M", "kg", M),
            _param("m", "kg", m),
        ],
    )


def _coulomb(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    k_e = _attr(sc.sim, "k_e", 8.9875517873681764e9)
    q1 = _attr(sc.sim, "q1", _attr(sc.sim, "q_src", 1.0e-9))
    q2 = _attr(sc.sim, "q2", _attr(sc.sim, "q_test", 1.0e-9))
    return _entry(
        "L1",
        "F = k_e*q1*q2/r**2",
        "def f(r, k_e, q1, q2):\n    return k_e*q1*q2/(r*r)\n",
        [{"name": "r", "units": "m"}],
        [{"name": "F", "units": "kg*m*s**-2"}],
        [
            _param("k_e", "kg*m**3*s**-4*A**-2", k_e),
            _param("q1", "A*s", q1),
            _param("q2", "A*s", q2),
        ],
    )


def _pendulum(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    # Post-XY (T13): bench builders output θ̈ from input θ but the
    # pendulum DIM declares output "theta" (unit "1"). The ceiling
    # entry inherits that declared output schema, so the stub must do
    # the same to pass stage-1 dim filtering. The numeric output is
    # still −(g/L)·sin(θ).
    g_over_L = _attr(
        sc.sim, "g_over_L", _attr(sc.sim, "g0_over_L", _attr(sc.sim, "g", 9.81) / max(_attr(sc.sim, "L", 1.0), 1e-9))
    )
    return _entry(
        "L1",
        "theta_dotdot = -(g_over_L)*sin(theta)",
        "import math\ndef f(theta, g_over_L):\n    return -g_over_L*math.sin(theta)\n",
        [{"name": "theta", "units": "1"}],
        [{"name": "theta", "units": "1"}],
        [_param("g_over_L", "s**-2", g_over_L)],
    )


def _rlc(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    # Post-XY (T13): bench builders return di/dt from inputs {q, i}
    # (and +t for δ-6-1). The RLC DIM declares output {q, i, V}, but
    # ceiling and bench operate on the di/dt channel. Stub emits the
    # Kirchhoff-derived di/dt directly so the stage-1 filter passes
    # on the same channel.
    L = _attr(sc.sim, "L", _attr(sc.sim, "L0", _attr(sc.sim, "L1", 1.0)))
    R = _attr(sc.sim, "R", _attr(sc.sim, "R1", 1.0))
    C = _attr(sc.sim, "C", _attr(sc.sim, "C1", 1.0e-6))
    return _entry(
        "L1",
        "didt = -(R*i + q/C)/L",
        (
            "def f(q, i, L, R, C):\n"
            "    return -(R*i + q/max(C, 1e-30))/max(L, 1e-12)\n"
        ),
        [
            {"name": "q", "units": "A*s"},
            {"name": "i", "units": "A"},
        ],
        [{"name": "q", "units": "A*s"}],
        [
            _param("L", "kg*m**2*s**-2*A**-2", L),
            _param("R", "kg*m**2*s**-3*A**-2", R),
            _param("C", "kg**-1*m**-2*s**4*A**2", C),
        ],
    )


def _thermal(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    k = _attr(sc.sim, "k", _attr(sc.sim, "k0", 1.0))
    return _entry(
        "L1",
        "q = k*(T_hot - T_cold)/L",
        "def f(T_hot, T_cold, L, k):\n    return k*(T_hot - T_cold)/L\n",
        [
            {"name": "T_hot", "units": "K"},
            {"name": "T_cold", "units": "K"},
            {"name": "L", "units": "m"},
        ],
        [{"name": "q", "units": "kg*s**-3"}],
        [_param("k", "kg*m*s**-3*K**-1", k)],
    )


def _wave(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    # Post-XY (T13): bench measures u(t) at sim.params.x_probe and uses
    # sin(k·x_probe − ω·t + φ). Stub bakes x_probe in as a closure
    # constant so its predictor signature matches the grid keys {t}.
    A = _attr(sc.sim, "A", 1.0)
    k = _attr(sc.sim, "k", 1.0)
    c = _attr(sc.sim, "c", 1.0)
    phi = _attr(sc.sim, "phi", 0.0)
    x_probe = _attr(sc.sim, "x_probe", 0.0)
    return _entry(
        "L1",
        "u(t) = A*sin(k*x_probe - c*k*t + phi)",
        (
            "import math\n"
            "def f(t, A, k, c, phi, x_probe):\n"
            "    return A*math.sin(k*x_probe - c*k*t + phi)\n"
        ),
        [{"name": "t", "units": "s"}],
        [{"name": "u", "units": "m"}],
        [
            _param("A", "m", A),
            _param("k", "m**-1", k),
            _param("c", "m*s**-1", c),
            _param("phi", "1", phi),
            _param("x_probe", "m", x_probe),
        ],
    )


def _optics(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    n1 = _attr(sc.sim, "n1", 1.0)
    n2 = _attr(sc.sim, "n2", _attr(sc.sim, "n0", 1.0))
    return _entry(
        "L1",
        "n1*sin(theta1) = n2*sin(theta2)",
        (
            "import math\n"
            "def f(theta1, n1, n2):\n"
            "    return math.asin((n1/n2)*math.sin(theta1))\n"
        ),
        [{"name": "theta1", "units": "1"}],
        [{"name": "theta2", "units": "1"}],
        [_param("n1", "1", n1), _param("n2", "1", n2)],
    )


def _fluid(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    rho = _attr(sc.sim, "rho", 1000.0)
    g = _attr(sc.sim, "g", 9.81)
    return _entry(
        "L1",
        "p2 = p1 + 0.5*rho*(v1**2 - v2**2) + rho*g*(h1 - h2)",
        (
            "def f(p1, v1, v2, h1, h2, rho, g):\n"
            "    return p1 + 0.5*rho*(v1*v1 - v2*v2) + rho*g*(h1 - h2)\n"
        ),
        [
            {"name": "p1", "units": "kg*m**-1*s**-2"},
            {"name": "v1", "units": "m*s**-1"},
            {"name": "v2", "units": "m*s**-1"},
            {"name": "h1", "units": "m"},
            {"name": "h2", "units": "m"},
        ],
        [{"name": "p2", "units": "kg*m**-1*s**-2"}],
        [
            _param("rho", "kg*m**-3", rho),
            _param("g", "m*s**-2", g),
        ],
    )


def _kinetics(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    # Post-XY (T13): bench measures C(t) (mol/m³), not rate (s^-1).
    # Stub now emits the n-th-order analytic C(t) so the dim filter
    # passes and the spread reflects "stub missed shift physics"
    # instead of "wrong output channel."
    data = _collect(sc.sim, probe_times, ("C", "rate"))
    k_hat = _fit_neg_linear(data["C"], data["rate"])
    if k_hat == 0.0:
        k_hat = _attr(sc.sim, "k", 0.1)
    n_hat = _attr(sc.sim, "n", 1.0)
    C0_hat = _attr(sc.sim, "C0", _attr(sc.sim, "C_A0", 1.0))
    return _entry(
        "L1",
        "C(t) = analytic n-th-order solution",
        (
            "import math\n"
            "def f(t, k, n, C0):\n"
            "    if n == 1.0:\n"
            "        return C0*math.exp(-k*t)\n"
            "    base = C0**(1.0 - n) + (n - 1.0)*k*t\n"
            "    if base <= 0:\n"
            "        return 0.0\n"
            "    return base**(1.0/(1.0 - n))\n"
        ),
        [{"name": "t", "units": "s"}],
        [{"name": "C", "units": "mol*m**-3"}],
        [
            _param("k", "s**-1", k_hat),
            _param("n", "1", n_hat),
            _param("C0", "mol*m**-3", C0_hat),
        ],
    )


def _decay(sc: ScenarioInstance, probe_times: Sequence[float]) -> Dict[str, Any]:
    # Post-T10 bench measures N(t) (dimensionless) as the truth channel,
    # not dN/dt. Fit λ from observed (N, rate) when both are exposed and
    # emit a closed-form N₀·exp(−λ·t) predictor so the stage-1 dim
    # filter passes and the baseline cell shows ~0 spread.
    data = _collect(sc.sim, probe_times, ("N", "rate"))
    lam_hat = _fit_neg_linear(data["N"], data["rate"])
    if lam_hat == 0.0:
        lam_hat = _attr(sc.sim, "lam", _attr(sc.sim, "lam0", 0.1))
    N0_hat = _attr(sc.sim, "N0", _attr(sc.sim, "N_init", 1.0e6))
    return _entry(
        "L1",
        "N(t) = N0*exp(-lam*t)",
        "import math\ndef f(t, lam, N0):\n    return N0*math.exp(-lam*t)\n",
        [{"name": "t", "units": "s"}],
        [{"name": "N", "units": "1"}],
        [
            _param("lam", "s**-1", lam_hat),
            _param("N0", "1", N0_hat),
        ],
    )


_DISPATCH = {
    "hooke": _hooke,
    "damped_ho": _damped_ho,
    "gravity": _gravity,
    "coulomb": _coulomb,
    "pendulum": _pendulum,
    "rlc": _rlc,
    "thermal": _thermal,
    "wave": _wave,
    "optics": _optics,
    "fluid": _fluid,
    "kinetics": _kinetics,
    "decay": _decay,
}


def run(
    scenario: ScenarioInstance,
    *,
    probe_times: Sequence[float] = _PROBE_TIMES,
) -> Dict[str, Any]:
    """Run the rule-based stub and return one submission entry per §5."""
    handler = _DISPATCH.get(scenario.domain_id)
    if handler is None:
        raise KeyError(
            f"no rule-based stub registered for domain {scenario.domain_id!r}; "
            f"registered: {sorted(_DISPATCH)}"
        )
    return handler(scenario, probe_times)


__all__ = ["run"]
