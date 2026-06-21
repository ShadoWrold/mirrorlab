"""P2 + full-bench consolidated sweep acceptance.

P2 covers the 7 domains not in the sprint4 sweep set: damped_ho,
pendulum, rlc, wave, optics, fluid, kinetics. Combined with P1
(gravity / hooke / coulomb / thermal / decay) this exercises all 12
domains × 4 cells = 48 cells with truth-form GT.

Cliff cells (where stub vs ceiling spread is large because stub misses
shift physics or the output channel) and soft cells (where small spread
reflects real physics: small ε, scale-invariant SCALE breaks, single-
channel observation gaps, or stub/ceiling are both the canonical form)
are enumerated explicitly so the gate distinguishes the two.
"""

from __future__ import annotations

import statistics

import pytest

from mirrorlab.runners.ceiling_agent import build_submission as ceiling_submission
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.agent_stub import run as stub_submission
from mirrorlab.scenarios.loader import load


_P2_CELLS = [
    ("damped_ho", s) for s in ("baseline", "gamma_3_1", "gamma_3_2", "delta_3_1")
] + [
    ("pendulum",  s) for s in ("baseline", "gamma_4_1", "gamma_4_2", "delta_4_1")
] + [
    ("rlc",       s) for s in ("baseline", "gamma_6_1", "gamma_6_2", "delta_6_1")
] + [
    ("wave",      s) for s in ("baseline", "gamma_8_1", "gamma_8_2", "delta_8_1")
] + [
    ("optics",    s) for s in ("baseline", "gamma_9_1", "gamma_9_2", "delta_9_1")
] + [
    ("fluid",     s) for s in ("baseline", "gamma_10_1", "gamma_10_2", "delta_10_1")
] + [
    ("kinetics",  s) for s in ("baseline", "gamma_11_1", "gamma_11_2", "delta_11_1")
]

# Soft cells in P2 (real-physics small spread, not bench bug):
# After the contract-alignment + scoring-core fixes, the ONLY genuinely
# soft non-baseline cells left are the two optics cells that are
# structurally unhardenable in the angle channel (see below). Every other
# γ/δ shift now shows a large oracle−stub spread (≥0.87) and is a real
# cliff — the earlier exemptions for damped_ho/pendulum/wave/fluid/kinetics
# γ/δ cells were STALE (hardened by 89a827c/f979ef2; verified stub 0.00–0.12,
# spread 0.88–1.0) and have been removed so the gate now checks them.
#
#   * all P2 baselines           — stub IS the canonical law (no shift to
#                                  detect), so it ties the ceiling by design
#   * optics γ-9-2 / δ-9-1       — structurally unhardenable in the angle
#                                  channel: γ-9-2's cubic break +κ·anti·sin³θ
#                                  is in the SAME polynomial family as the GT
#                                  (a free refit asin(c·sinθ+d·sin³θ) absorbs
#                                  it exactly; declaring cf-canonical n_1/n_2
#                                  scores oracle-identical 1.0). δ-9-1's break
#                                  is T_TRANS energy (R+T≠1), not in the angle
#                                  channel at all (catalog step()==baseline).
#                                  See memory: cf Y-plumbing collapses the
#                                  hardness gap for closed-form-absorbable
#                                  breaks. Re-evaluate in the scoring overhaul.
_P2_SOFT_CELLS = {
    ("damped_ho", "baseline"),
    ("pendulum",  "baseline"),
    ("rlc",       "baseline"),
    ("wave",      "baseline"),
    ("optics",    "baseline"),
    ("optics",    "gamma_9_2"),
    ("optics",    "delta_9_1"),
    ("fluid",     "baseline"),
    ("kinetics",  "baseline"),
}


@pytest.fixture(scope="module")
def p2_sweep():
    out = {}
    for dom, shift in _P2_CELLS:
        ceil_list, stub_list = [], []
        for seed in (0, 1, 2):
            sc = load(dom, shift, seed=seed)
            ceil_list.append(score_against_scenario(sc, ceiling_submission(sc)))
            stub_list.append(score_against_scenario(sc, [stub_submission(sc)]))
        out[(dom, shift)] = {"ceiling": ceil_list, "stub": stub_list}
    return out


def test_p2_median_ceiling_above_threshold(p2_sweep):
    medians = [statistics.median(v["ceiling"]) for v in p2_sweep.values()]
    overall = statistics.median(medians)
    assert overall >= 0.90, (
        f"P2 overall median ceiling {overall:.4f} < 0.90"
    )


def test_p2_worst_cell_ceiling_above_floor(p2_sweep):
    worst = {(d, s): min(v["ceiling"]) for (d, s), v in p2_sweep.items()}
    bad = [(k, v) for k, v in worst.items() if v < 0.70]
    assert not bad, f"P2 worst-cell ceiling violations: {bad}"


def test_p2_truth_at_least_as_good_as_baseline(p2_sweep):
    violations = []
    for (d, s), v in p2_sweep.items():
        for seed, (c, b) in enumerate(zip(v["ceiling"], v["stub"])):
            if c < b - 1e-3:
                violations.append(f"{d}/{s}/seed={seed}: truth={c:.4f} < stub={b:.4f}")
    assert not violations, "P2 truth-vs-baseline direction violations:\n  " + "\n  ".join(violations)


def test_p2_cliff_cells_show_spread(p2_sweep):
    cliff_cells = [k for k in p2_sweep if k not in _P2_SOFT_CELLS]
    too_small = []
    for k in cliff_cells:
        ceil = p2_sweep[k]["ceiling"]
        stub = p2_sweep[k]["stub"]
        spreads = [c - b for c, b in zip(ceil, stub)]
        med = statistics.median(spreads)
        if med < 0.10:
            too_small.append((k, round(med, 4)))
    assert not too_small, (
        f"P2 cliff cells with median spread < 0.10: {too_small}"
    )
