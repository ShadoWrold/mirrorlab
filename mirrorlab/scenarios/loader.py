"""Scenario loader.

Combines a registry-built ``SimInstance`` with the agent-visible prompt and
the held-out test grids that the evaluator (§6) consumes.

Sprint 1 wires up the Hooke domain (baseline + γ-1-1). The test grids are
*placeholders* — they exercise the loader contract and are dimensioned per
§6.2 sub-grids (a / b / c) so the evaluator harness has something concrete
to consume in #4 / #5; calibration of grid sizes and ranges is deferred
to Sprint 3 (CAL-1, CAL-2, CAL-3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import numpy as np

from mirrorlab.domains.hooke import DIM_SIGNATURE as HOOKE_DIM_SIG
from mirrorlab.domains.hooke import SimInstance
from mirrorlab.scenarios import prompts
from mirrorlab.scenarios.registry import make as _make_sim

_DOMAIN_PROMPT_BUILDERS = {
    "hooke": prompts.hooke_prompt,
}

_DOMAIN_OBSERVABLES = {
    "hooke": prompts.HOOKE_OBSERVABLES,
}

_DOMAIN_DIM = {
    "hooke": HOOKE_DIM_SIG,
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
        counterfactual). Sprint 1 placeholders.
    """

    domain_id: str
    shift_id: str
    seed: int
    sim: SimInstance
    prompt: str
    observables: Tuple[str, ...]
    dim_signature: Dict[str, Dict[str, str]]
    test_grids: Dict[str, np.ndarray] = field(default_factory=dict)


def _hooke_test_grids(sim: SimInstance, seed: int) -> Dict[str, np.ndarray]:
    """Sprint 1 placeholder grids for the Hooke domain.

    Uses the IC amplitude ``x0`` as the in-domain scale: (a) covers
    [-x0, x0]; (b) covers ±[1.5·x0, 5·x0] (OOD per CAL-2 default 5×);
    (c) is the in-domain scale resampled under a fresh RNG to stand in
    for counterfactual parameter perturbations (CAL-3, real impl in #4).
    """
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
    return {"a": grid_a, "b": grid_b, "c": grid_c}


def load(
    domain_id: str,
    shift_id: str,
    *,
    seed: int = 0,
    params: Any | None = None,
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
    if domain_id == "hooke":
        test_grids = _hooke_test_grids(sim, seed)
    else:
        test_grids = {}
    return ScenarioInstance(
        domain_id=domain_id,
        shift_id=shift_id,
        seed=seed,
        sim=sim,
        prompt=prompt,
        observables=observables,
        dim_signature=dim_signature,
        test_grids=test_grids,
    )


__all__ = ["ScenarioInstance", "load"]
