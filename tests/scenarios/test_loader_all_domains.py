"""Sprint-3 contract tests: loader handles all 12 (domain, shift) pairs."""

from __future__ import annotations

import re
from typing import Sequence

import numpy as np
import pytest

from mirrorlab.scenarios.counterfactual import _LAW_PARAM_FIELDS, perturb_params
from mirrorlab.scenarios.loader import ScenarioInstance, load
from mirrorlab.scenarios.registry import REGISTRY

# Phrase-style forbidden tokens (case-insensitive substring match). These
# are long enough that an incidental match is unlikely.
_FORBIDDEN_SUBSTRINGS = (
    "tanh", "shift", "broken", "parity", "linear",
    "hooke", "spring", "F = -k", "-k*x", "-k x",
    "newton", "inverse-square", "G*M",
    "coulomb",
    "pendulum",
    "ohm", "kirchhoff", "inductor", "capacitor", "resistor",
    "fourier", "conduction",
    "d'alembert", "wave equation",
    "snell", "refraction",
    "bernoulli", "incompressible",
    "first-order", "second-order", "mass-action", "rate constant",
    "exponential decay", "half-life",
    "gamma_", "delta_", "γ", "δ",
)

# Whole-word forbidden tokens (case-sensitive). Short / all-caps symmetry
# labels that would false-positive as substrings of common English.
_FORBIDDEN_WORDS = ("PAR", "T-rev", "T-trans")


def _all_domains() -> Sequence[str]:
    return sorted({d for d, _ in REGISTRY.keys()})


def _all_pairs() -> Sequence[tuple[str, str]]:
    return sorted(REGISTRY.keys())


@pytest.mark.parametrize("domain_id,shift_id", _all_pairs())
def test_load_every_pair(domain_id: str, shift_id: str) -> None:
    sc = load(domain_id, shift_id, seed=0)
    assert isinstance(sc, ScenarioInstance)
    assert sc.domain_id == domain_id
    assert sc.shift_id == shift_id
    assert isinstance(sc.prompt, str) and sc.prompt.strip()
    assert sc.observables, "observables must not be empty"
    assert "outputs" in sc.dim_signature and sc.dim_signature["outputs"]


@pytest.mark.parametrize("domain_id", _all_domains())
def test_prompt_no_global_forbidden_tokens(domain_id: str) -> None:
    sc = load(domain_id, "baseline", seed=0)
    lowered = sc.prompt.lower()
    for token in _FORBIDDEN_SUBSTRINGS:
        assert token.lower() not in lowered, (
            f"domain {domain_id!r} prompt leaked forbidden substring {token!r}"
        )
    for word in _FORBIDDEN_WORDS:
        assert not re.search(rf"\b{re.escape(word)}\b", sc.prompt), (
            f"domain {domain_id!r} prompt leaked forbidden word {word!r}"
        )


@pytest.mark.parametrize("domain_id,shift_id", _all_pairs())
def test_prompt_identical_across_shifts(domain_id: str, shift_id: str) -> None:
    """Same domain, different shift → identical prompt (no per-shift leak)."""
    sc = load(domain_id, shift_id, seed=0)
    sc_base = load(domain_id, "baseline", seed=0)
    assert sc.prompt == sc_base.prompt


@pytest.mark.parametrize("domain_id,shift_id", _all_pairs())
def test_counterfactual_whitelist_registered(domain_id: str, shift_id: str) -> None:
    """Every (domain, shift) pair's params type must be in the CAL-3 whitelist."""
    sc = load(domain_id, shift_id, seed=0)
    rng = np.random.default_rng(0)
    # Should not raise TypeError ("no counterfactual policy registered").
    out = perturb_params(sc.sim.params, magnitude=0.1, rng=rng)
    assert type(out) is type(sc.sim.params)


def test_whitelist_has_all_registry_param_types() -> None:
    """Exhaustive: every registered scenario's params type is on the whitelist."""
    seen: set[type] = set()
    for (domain_id, shift_id) in REGISTRY.keys():
        sc = load(domain_id, shift_id, seed=0)
        seen.add(type(sc.sim.params))
    missing = seen - set(_LAW_PARAM_FIELDS.keys())
    assert not missing, f"unregistered params types: {sorted(t.__name__ for t in missing)}"
