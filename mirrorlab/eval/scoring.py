"""Per-scenario scoring (spec §7).

S_scen = max_e s_entry(e) · (1 − ρ · (|set| − 1)) + b · 𝟙[symmetry claim correct]

Defaults from CAL registry:
  ρ = 0.05 (CAL-6)   shotgun penalty per extra entry beyond the first
  b  = 0.10 (CAL-5)   correct-broken-symmetry-claim bonus

Spec §5.1 / §5.2: entries failing the stage-1 dim filter score 0; the set is
truncated at 5 in declaration order. Wrong symmetry claim ⇒ no penalty
(spec §6.3). Baseline scenarios accept ``"none"`` as the correct label.
Benchmark-level aggregation (`S_bench`) is stubbed: Sprint 1 only has the
single Hooke baseline + γ-1-1 cells, so per-cell macro-mean is a no-op.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from mirrorlab.eval.dimensional import Dim7, match_dim
from mirrorlab.eval.numeric import TestGrids, evaluate_entry

RHO_DEFAULT = 0.05      # CAL-6
BONUS_DEFAULT = 0.10    # CAL-5
SET_CAP = 5


def score_submission(
    submission_set: Sequence[Mapping[str, Any]],
    *,
    target_dim: str | Dim7,
    test_grids: TestGrids,
    gt_symmetry: Optional[str] = None,
    rho: float = RHO_DEFAULT,
    bonus: float = BONUS_DEFAULT,
) -> float:
    """Return ``S_scen`` per spec §7.

    Args:
        submission_set: list of submission entries; truncated at 5.
        target_dim: scenario's declared output dim signature (units string
            or pre-parsed 7-tuple) — used by the stage-1 filter.
        test_grids: three-sub-grid mapping consumed by ``evaluate_entry``.
        gt_symmetry: ground-truth broken-symmetry label (e.g. ``"PAR"`` for
            γ-1-1, or ``"none"`` for a baseline scenario). ``None`` disables
            the bonus.
        rho, bonus: CAL knobs; defaults track the spec.
    """
    if not submission_set:
        return 0.0
    entries = list(submission_set)[:SET_CAP]
    n = len(entries)

    best = 0.0
    bonus_fires = False
    for e in entries:
        if match_dim(e, target_dim):
            s = evaluate_entry(e, test_grids)
        else:
            s = 0.0
        if s > best:
            best = s
        # Bonus is awarded if *any* entry's claim matches the ground truth —
        # spec §6.3 frames it as an independent signal that does not depend
        # on the best-scoring entry being the one that named the symmetry.
        if gt_symmetry is not None:
            claim = e.get("claim_broken_symmetry")
            if claim is not None and str(claim).strip().upper() == gt_symmetry.strip().upper():
                bonus_fires = True

    penalty = 1.0 - rho * (n - 1)
    scen = best * max(penalty, 0.0)
    if bonus_fires:
        scen += bonus
    return float(scen)


__all__ = ["RHO_DEFAULT", "BONUS_DEFAULT", "SET_CAP", "score_submission"]
