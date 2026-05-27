"""T5/T6 (P0 end-to-end): ceiling vs baseline-stub spread on γ-2-1.

Verifies the P0 rollback gate per blueprint §8.1: with the X+Y stack
(loader_shifts/gravity γ-2-1 truth-form GT + Y-plumbing on (c) +
ceiling_agent γ-2-1 truth-form predictor), the spread between the
catalog ceiling and the baseline-form agent stub on γ-2-1 must be
visibly large under the real scoring path
(``sprint3_pilot.score_against_scenario``).

Pre-X+Y, the spread was ~0 because GT was baseline-form: baseline-form
submissions matched it and ceiling fell back to baseline form too.
Post-X+Y, the truth-form GT separates them:
- Ceiling reads (x, y, z, G, M, ...) and returns the actual
  ``shifted_force`` projection → S ≈ 1.
- Baseline stub declares ``inputs=[{r}]`` and signature ``f(r, G, M, m)``;
  the (x, y, z) grid keys are filtered out by ``_predictor_signature``
  and the predictor raises on the missing ``r`` kwarg, returning CLAMP
  per ``_safe_call`` → S ≈ 0.

This is the "X.B exposure" mechanism documented at blueprint §2.3
unstated-requirement-B: baseline-form submissions with narrower
declared inputs than the scenario's canonical_inputs score badly on
ROT-shift grids by design.
"""

from __future__ import annotations

import pytest

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_p0_ceiling_vs_baseline_stub_spread(seed):
    sc = load("gravity", "gamma_2_1", seed=seed)
    s_ceiling = score_against_scenario(sc, ceiling_submission(sc))
    s_stub = score_against_scenario(sc, [stub_submission(sc)])

    # Blueprint §8.1 P0 gate: spread ≥ 0.10. Empirically we measure
    # ≥ 0.95 across seeds, so the gate has a comfortable margin.
    spread = s_ceiling - s_stub
    assert s_ceiling >= 0.90, (
        f"seed={seed}: ceiling {s_ceiling:.6f} < 0.90 — γ-2-1 truth-form "
        "predictor or builder is misaligned with the truth GT."
    )
    assert spread >= 0.10, (
        f"seed={seed}: spread {spread:.6f} < 0.10 (ceiling={s_ceiling:.6f}, "
        f"stub={s_stub:.6f}). The baseline-form X.B exposure failed — check "
        "_alias_inputs / _predictor_signature filtering on the stub."
    )
