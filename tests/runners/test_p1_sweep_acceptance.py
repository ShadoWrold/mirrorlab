"""T15 (P1 consolidated): full P1 sweep acceptance.

Per docs/blueprint-xy.md §5 (P1 CHECKPOINT) and §8.2 (P1 rollback gate).
Sweeps all 5 P1 domains × 4 cells × 3 seeds = 60 datapoints in one test
file. Asserts the gate criteria from §8.2:

  median ceiling ≥ 0.90 across all P1 cells
  worst-cell ceiling ≥ 0.70 across all P1 cells
  truth ≥ baseline (within float noise) on every (cell, seed)
  cliff-cells: median spread ≥ 0.10

"cliff-cells" excludes the soft cells whose physics gives small spread
by design — scale/T-modulation 1-D shifts and the single-channel
particle-loss observable. These are paper-1 findings ("low-detectability
cells"), not bench bugs.
"""

from __future__ import annotations

import statistics

import pytest

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


_P1_CELLS = [
    ("gravity",  "baseline"),
    ("gravity",  "gamma_2_1"),
    ("gravity",  "gamma_2_2"),
    ("gravity",  "delta_2_1"),
    ("hooke",    "baseline"),
    ("hooke",    "gamma_1_1"),
    ("hooke",    "gamma_1_2"),
    ("hooke",    "delta_1_1"),
    ("coulomb",  "baseline"),
    ("coulomb",  "gamma_5_1"),
    ("coulomb",  "gamma_5_2"),
    ("coulomb",  "delta_5_1"),
    ("thermal",  "baseline"),
    ("thermal",  "gamma_7_1"),
    ("thermal",  "gamma_7_2"),
    ("thermal",  "delta_7_1"),
    ("decay",    "baseline"),
    ("decay",    "gamma_12_1"),
    ("decay",    "gamma_12_2"),
    ("decay",    "delta_12_1"),
]

# Cells where the truth-vs-baseline spread is small by physics, not by
# bench bug:
#   gravity/baseline, hooke/baseline, coulomb/baseline, thermal/baseline,
#   decay/baseline   — stub IS the baseline, spread ~0 by construction
#   gravity/γ-2-2    — scale-break (Lorentzian bump, α small)
#   gravity/δ-2-1    — T-modulation (β small)
#   hooke/δ-1-1      — drag term scales with x²·v, c is small for some seeds
#   decay/δ-12-1     — branching only affects unobserved N_B channel; N_A
#                      stays exponential, so single-channel observation
#                      cannot detect the break (paper 1: design feature)
#   decay/γ-12-2     — parametric ε·cos(ωt) modulation; ε is small in
#                      the catalog sampler and the integral over grid
#                      times often averages near zero
_SOFT_CELLS = {
    ("gravity",  "baseline"),
    ("gravity",  "gamma_2_2"),
    ("gravity",  "delta_2_1"),
    ("hooke",    "baseline"),
    ("hooke",    "delta_1_1"),
    ("coulomb",  "baseline"),
    ("thermal",  "baseline"),
    ("decay",    "baseline"),
    ("decay",    "gamma_12_2"),
    ("decay",    "delta_12_1"),
}


@pytest.fixture(scope="module")
def p1_sweep():
    """Run the full P1 sweep once and cache per-cell score lists."""
    out = {}
    for dom, shift in _P1_CELLS:
        ceil_list, stub_list = [], []
        for seed in (0, 1, 2):
            sc = load(dom, shift, seed=seed)
            ceil_list.append(score_against_scenario(sc, ceiling_submission(sc)))
            stub_list.append(score_against_scenario(sc, [stub_submission(sc)]))
        out[(dom, shift)] = {"ceiling": ceil_list, "stub": stub_list}
    return out


# ---------------------------------------------------------------------------
# §8.2 gate (1) — median ceiling ≥ 0.90
# ---------------------------------------------------------------------------

def test_p1_median_ceiling_above_threshold(p1_sweep):
    medians = [statistics.median(v["ceiling"]) for v in p1_sweep.values()]
    overall = statistics.median(medians)
    assert overall >= 0.90, (
        f"P1 overall median ceiling {overall:.4f} < 0.90 — "
        "T7-T11 truth-form GT or T4/T12-mini ceiling predictors are misaligned."
    )


# ---------------------------------------------------------------------------
# §8.2 gate (2) — worst-cell ceiling ≥ 0.70
# ---------------------------------------------------------------------------

def test_p1_worst_cell_ceiling_above_floor(p1_sweep):
    worst_per_cell = {(d, s): min(v["ceiling"]) for (d, s), v in p1_sweep.items()}
    bad = [(k, v) for k, v in worst_per_cell.items() if v < 0.70]
    assert not bad, (
        f"P1 worst-cell ceiling violations (need ≥ 0.70): {bad}"
    )


# ---------------------------------------------------------------------------
# Direction check — truth ≥ baseline on every (cell, seed)
# ---------------------------------------------------------------------------

def test_p1_truth_at_least_as_good_as_baseline(p1_sweep):
    violations = []
    for (d, s), v in p1_sweep.items():
        for seed, (c, b) in enumerate(zip(v["ceiling"], v["stub"])):
            if c < b - 1e-3:
                violations.append(f"{d}/{s}/seed={seed}: truth={c:.4f} < stub={b:.4f}")
    assert not violations, (
        "P1 truth-vs-baseline direction violations:\n  " + "\n  ".join(violations)
    )


# ---------------------------------------------------------------------------
# Cliff-cells: median spread ≥ 0.10
# ---------------------------------------------------------------------------

def test_p1_cliff_cells_show_spread(p1_sweep):
    cliff_cells = [
        k for k in p1_sweep if k not in _SOFT_CELLS
    ]
    too_small = []
    for k in cliff_cells:
        ceil = p1_sweep[k]["ceiling"]
        stub = p1_sweep[k]["stub"]
        spreads = [c - b for c, b in zip(ceil, stub)]
        med = statistics.median(spreads)
        if med < 0.10:
            too_small.append((k, med))
    assert not too_small, (
        f"Cliff cells with median spread < 0.10 (should show baseline "
        f"failure): {too_small}"
    )
