"""(domain_id, shift_id) → factory mapping.

Sprint 1 only registers the Hooke domain (baseline + γ-1-1).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

from mirrorlab.domains.hooke import HookeBaseline, HookeParams, SimInstance
from mirrorlab.shifts import hooke_g_1_1

Factory = Callable[..., SimInstance]


def _baseline_default_params(seed: int) -> HookeParams:
    rng = np.random.default_rng(seed)
    k = float(np.exp(rng.uniform(np.log(1.0), np.log(100.0))))
    return HookeParams(k=k, m=1.0, x0=0.1, v0=0.0)


def _hooke_baseline_factory(
    *, seed: int = 0, params: Optional[HookeParams] = None
) -> SimInstance:
    if params is None:
        params = _baseline_default_params(seed)
    return HookeBaseline(params)


def _hooke_g_1_1_factory(
    *, seed: int = 0, params: Optional[hooke_g_1_1.HookeGamma11Params] = None
) -> SimInstance:
    return hooke_g_1_1.build(params=params, seed=seed)


REGISTRY: Dict[Tuple[str, str], Factory] = {
    ("hooke", "baseline"): _hooke_baseline_factory,
    ("hooke", "gamma_1_1"): _hooke_g_1_1_factory,
}


def make(
    domain_id: str,
    shift_id: str,
    *,
    seed: int = 0,
    params: Optional[Any] = None,
) -> SimInstance:
    """Build a SimInstance for the requested `(domain_id, shift_id)`.

    Use `shift_id="baseline"` for the unmodified domain law. If `params` is
    omitted the factory draws a default / sampled parameter set under `seed`.
    """
    key = (domain_id, shift_id)
    if key not in REGISTRY:
        raise KeyError(
            f"unknown scenario {key!r}; registered: {sorted(REGISTRY)}"
        )
    return REGISTRY[key](seed=seed, params=params)


__all__ = ["REGISTRY", "make"]
