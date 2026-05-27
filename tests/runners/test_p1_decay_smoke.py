"""T10 (P1, decay): truth-form builders end-to-end smoke.

All 4 decay cells use step()-based truth (blueprint §3.2.1) with the
observable ``N`` (population). T12-mini patched agent_stub._decay to
emit N(t) = N₀·exp(−λ·t) (units "1") so the stage-1 dim filter passes
and baseline / δ-12-1 show ~0 spread (their truth is also exponential
on the observed N_A channel; only the unobserved N_B differs).

Cell-by-cell expectations:
- baseline:  ceiling ≈ stub (both N₀·exp(−λt))
- γ-12-1:    density-coupled rate → stub misses α·N^p correction,
             spread ~0.1-0.9 (sampler-dependent)
- γ-12-2:    parametric modulation → stub misses ε·cos(ωt), spread
             0 to 0.1 (ε is small; sometimes the timing of the
             integral aligns to 0)
- δ-12-1:    branching loss only affects N_B; observed channel N_A
             obeys the SAME exponential as baseline → stub matches
             truth by physics, not by mistake. paper 1: "single-channel
             observation cannot detect particle-loss to dark channel."
"""

from __future__ import annotations

import pytest

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


@pytest.mark.parametrize("shift", ["baseline", "gamma_12_1", "gamma_12_2", "delta_12_1"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_decay_ceiling_high(shift, seed):
    sc = load("decay", shift, seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    assert s_c >= 0.90, (
        f"seed={seed}: decay/{shift} ceiling {s_c:.4f} < 0.90 — "
        "step()-based truth or coefficient binding is broken."
    )


@pytest.mark.parametrize("shift", ["baseline", "gamma_12_1", "gamma_12_2", "delta_12_1"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_decay_truth_not_worse_than_stub(shift, seed):
    """Direction check: truth ≥ stub on every cell (within float noise)."""
    sc = load("decay", shift, seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c >= s_s - 1e-3, (
        f"seed={seed}: decay/{shift} truth {s_c:.4f} < stub {s_s:.4f}"
    )
