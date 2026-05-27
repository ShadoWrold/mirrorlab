"""T10 (P1, decay): truth-form builders end-to-end smoke.

All 4 decay cells use step()-based truth (blueprint §3.2.1) with the
observable ``N`` (population), not ``rate`` (dN/dt). The existing
agent_stub still emits ``rate = -lam·N`` and declares output units
``s**-1``, so the stage-1 dim filter (target_dim = "1" for N)
rejects every stub submission → stub scores 0 by construction.

This is the desired X.B exposure for decay: the canonical-baseline
agent has its observable / output channel pinned to ``rate``, while
the truth-form bench measures ``N(t)``. The post-T13 stub rewrite
will harmonize them; until then the cliff is large.
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
def test_decay_stub_below_ceiling(shift, seed):
    """Stub output is ``rate`` (s**-1) but truth GT is ``N`` (dimensionless);
    stub is filtered at stage-1 → 0 score. The cliff is uniform across
    all 4 decay cells."""
    sc = load("decay", shift, seed=seed)
    s_c = score_against_scenario(sc, ceiling_submission(sc))
    s_s = score_against_scenario(sc, [stub_submission(sc)])
    assert s_c - s_s >= 0.50, (
        f"seed={seed}: decay/{shift} spread {s_c - s_s:+.4f} < 0.50 "
        f"(ceiling {s_c:.4f}, stub {s_s:.4f})"
    )
