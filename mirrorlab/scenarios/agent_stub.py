"""Rule-based scenario-agent stub.

Sprint 1 demo only. NOT an LLM. The stub:

  1. probes the live ``SimInstance`` at a handful of times along the
     scenario's natural trajectory (no tool pool — Sprint 2 wires that up);
  2. collects ``(x, F)`` pairs;
  3. fits a single linear law ``F = -k x`` by least squares;
  4. emits one submission entry in the §5 format with the correct SI
     dimensional signature.

This stub is intentionally blind to nonlinearity: on the Hooke baseline it
should fit well; on γ-1-1 the same linear fit will mis-extrapolate, which is
the point of the Sprint 1 end-to-end demo (the evaluator should distinguish).
"""

from __future__ import annotations

from typing import Any, Dict, Sequence

import numpy as np

from mirrorlab.scenarios.loader import ScenarioInstance

_PROBE_TIMES: tuple[float, ...] = tuple(np.linspace(0.01, 2.0, 32))


def _collect_xF(sim, probe_times: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    xs, fs = [], []
    for t in probe_times:
        obs = sim.step(float(t))
        xs.append(obs["x"])
        fs.append(obs["F"])
    return np.asarray(xs, dtype=float), np.asarray(fs, dtype=float)


def _fit_linear_k(xs: np.ndarray, fs: np.ndarray) -> float:
    """Least-squares fit of ``F = -k x``."""
    denom = float(np.dot(xs, xs))
    if denom <= 0.0:
        return 0.0
    return -float(np.dot(xs, fs)) / denom


def run(
    scenario: ScenarioInstance,
    *,
    probe_times: Sequence[float] = _PROBE_TIMES,
) -> Dict[str, Any]:
    """Run the rule-based stub and return one submission entry per §5."""
    xs, fs = _collect_xF(scenario.sim, probe_times)
    k_hat = _fit_linear_k(xs, fs)
    return {
        "law_id": "L1",
        "formula": "F = -k*x",
        "predictor": {
            "lang": "python",
            "code": "def f(x, k):\n    return -k*x\n",
        },
        "inputs": [{"name": "x", "units": "m"}],
        "outputs": [{"name": "F", "units": "kg*m*s**-2"}],
        "params": [{"name": "k", "units": "kg*s**-2", "value": k_hat}],
    }


__all__ = ["run"]
