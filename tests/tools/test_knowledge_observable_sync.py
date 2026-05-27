"""Drift check: knowledge.list_observables must equal live step() keys.

Sprint 4.5 removed several leaking observables (E, T, etc.) from individual
domain step() bodies. The knowledge.list_observables tool is built from a
live reflection of the baseline step(), but we still pin the contract here
so that any future refactor of either side fails loudly.
"""

from __future__ import annotations

import pytest

from mirrorlab.scenarios.registry import make
from mirrorlab.tools import knowledge


_DOMAINS = sorted(knowledge._DOMAIN_TO_SCENARIO_ID)


@pytest.mark.parametrize("domain", _DOMAINS)
def test_list_observables_matches_baseline_step(domain: str) -> None:
    scenario_id = knowledge._DOMAIN_TO_SCENARIO_ID[domain]
    sim = make(scenario_id, "baseline", seed=0)
    live_keys = list(sim.step(0.0).keys())
    declared = knowledge.list_observables(domain=domain)["observables"]
    assert declared == live_keys, (
        f"list_observables({domain!r}) drifted from baseline step(): "
        f"declared={declared} live={live_keys}"
    )


@pytest.mark.parametrize("domain", _DOMAINS)
def test_list_observables_not_a_superset_of_removed_leaks(domain: str) -> None:
    """Sprint 4.5 leak motifs must not reappear in any domain's observables."""
    declared = set(knowledge.list_observables(domain=domain)["observables"])
    # Domain-specific leaks removed during Sprint 4.5 audits:
    forbidden = {
        "hooke":    {"E"},
        "damped":   {"E"},
        "gravity":  {"E"},
        "pendulum": {"E"},
        "coulomb":  {"Lz", "Q_total"},
        "thermal":  {"T", "T_mean", "q_x", "q_y"},
        "wave":     {"n_eff", "R_plus_T"},
        "optics":   {"n_eff", "R_plus_T"},
        "fluid":    set(),
        "kinetics": set(),
        "decay":    {"lam_t"},
        "rlc":      set(),
    }
    leaked = declared & forbidden.get(domain, set())
    assert not leaked, f"{domain} leaked observables: {leaked}"
