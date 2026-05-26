"""Scenario loader.

Combines a registry-built ``SimInstance`` with the agent-visible prompt and
the held-out test grids that the evaluator (§6) consumes.

Sprint 1 wires up the Hooke domain (baseline + γ-1-1). Sub-grids (a) and (b)
remain placeholders (calibration deferred to Sprint 3 — CAL-1/CAL-2). Sub-grid
(c) is the counterfactual probe: per-point perturbed-parameter law values,
implemented by ``mirrorlab.scenarios.counterfactual.perturb_params`` (CAL-3
default ±30%).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import numpy as np

from mirrorlab.domains.hooke import DIM_SIGNATURE as HOOKE_DIM_SIG
from mirrorlab.domains.hooke import SimInstance
from mirrorlab.scenarios import prompts
from mirrorlab.scenarios.counterfactual import DEFAULT_MAGNITUDE, perturb_params
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
        counterfactual).
    counterfactual_params
        Tuple of perturbed-parameter dataclasses, one per point in
        ``test_grids["c"]``. The evaluator builds per-point ground truth by
        applying the domain's force law with each entry's params instead of
        the baseline ``sim.params``. Empty tuple if (c) is unset.
    counterfactual_magnitude
        CAL-3 perturbation magnitude actually used (records the placeholder
        default so Sprint 3 calibration is auditable).
    """

    domain_id: str
    shift_id: str
    seed: int
    sim: SimInstance
    prompt: str
    observables: Tuple[str, ...]
    dim_signature: Dict[str, Dict[str, str]]
    test_grids: Dict[str, np.ndarray] = field(default_factory=dict)
    counterfactual_params: Tuple[Any, ...] = ()
    counterfactual_magnitude: float = DEFAULT_MAGNITUDE


def _hooke_test_grids(
    sim: SimInstance, seed: int, magnitude: float
) -> tuple[Dict[str, np.ndarray], Tuple[Any, ...]]:
    """Sprint-1 placeholder (a)(b) plus counterfactual (c).

    (a) covers the in-domain amplitude ``[-x0, x0]``; (b) extends to
    ``±[1.5·x0, 5·x0]`` (OOD per CAL-2 default 5×); (c) is again drawn from
    the in-domain scale but its per-point ground truth is computed against
    a freshly-perturbed parameter set, so a curve-fit with frozen
    coefficients cannot track it.
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
    cf_rng = np.random.default_rng(seed + 2)
    cf_params = tuple(
        perturb_params(sim.params, magnitude=magnitude, rng=cf_rng)
        for _ in range(grid_c.size)
    )
    return {"a": grid_a, "b": grid_b, "c": grid_c}, cf_params


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
    if domain_id == "hooke":
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
