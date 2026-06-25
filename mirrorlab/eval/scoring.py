"""Per-scenario scoring (spec §7).

S_scen = max_e s_entry(e) · (1 − ρ · (|set| − 1)) + b · 𝟙[symmetry claim correct]

Defaults from CAL registry:
  ρ = 0.05 (CAL-6)   shotgun penalty per extra entry beyond the first
  b  = 0.10 (CAL-5)   correct-broken-symmetry-claim bonus

Spec §5.1 / §5.2: entries failing the stage-1 dim filter score 0; the set is
truncated at 5 in declaration order. Wrong symmetry claim ⇒ no penalty
(spec §6.3). Baseline scenarios accept ``"none"`` as the correct label.

Symmetry bonus (post-debate hardening): the bonus is awarded only if the
**best-scoring** entry names the correct broken symmetry — not "any entry".
The old "any entry" rule let a multi-submission farm the +b for free: list 5
entries each claiming a different symmetry label, near-guaranteeing the bonus
for only a flat shotgun-penalty cost. Binding the bonus to the best entry
forces the symmetry judgement onto the same hypothesis that fits the data.

Single-submission vs best-of-k (post-debate): ``score_submission`` returns the
best-of-k S_scen (legacy float API, unchanged). ``score_submission_detail``
additionally returns the **single-submission** score — the first declared
entry alone, no max over a set, no shotgun penalty — which is immune by
construction to submission-strategy contamination. The single-submission
number is the exhaustion-proof primary metric for single-law cells; best-of-k
is retained as a secondary diagnostic and as the big-world (multi-law)
interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from mirrorlab.eval.dimensional import Dim7, match_dim
from mirrorlab.eval.numeric import TestGrids, evaluate_entry

RHO_DEFAULT = 0.05      # CAL-6
BONUS_DEFAULT = 0.10    # CAL-5
SET_CAP = 5


@dataclass(frozen=True)
class ScoreDetail:
    """Both scoring views of one submission (post-debate dual metric).

    best_of_k          : the legacy S_scen — max over the (capped) set, with
                         shotgun penalty and best-entry symmetry bonus.
    single_submission  : the first declared entry scored alone (no set, no
                         penalty, its own claim for the bonus). Immune to
                         submission-strategy contamination; the primary metric
                         for single-law cells.
    n_entries          : number of entries actually scored (post-cap).
    captured_fraction  : the structural-probe captured_fraction of the
                         bonus-bearing entry (Phase 2). None when no spec was
                         supplied or the cell has no applicable probe (the
                         bonus then falls back to the string-match rule). It is
                         recorded for observability even when it gates the bonus.
    """

    best_of_k: float
    single_submission: float
    n_entries: int
    captured_fraction: Optional[float] = None


def _entry_score(
    e: Mapping[str, Any],
    target_dim: str | Dim7,
    test_grids: TestGrids,
    canonical_inputs: Optional[Sequence[str]],
) -> float:
    if not match_dim(e, target_dim):
        return 0.0
    try:
        return evaluate_entry(e, test_grids, canonical_inputs=canonical_inputs)
    except Exception:
        # A single malformed entry (e.g. a predictor body with a Python
        # SyntaxError / IndentationError) scores 0 — it must NOT crash the whole
        # submission set. Observed: a gpt fluid/delta_10_1 entry with a broken
        # indent zeroed the entire cell, dropping a sibling entry that scored
        # 0.067. The §5 contract evaluates entries independently; a bad one is
        # just an unscorable entry, not a fatal error for the set.
        return 0.0


def _claim_matches(e: Mapping[str, Any], gt_symmetry: Optional[str]) -> bool:
    if gt_symmetry is None:
        return False
    claim = e.get("claim_broken_symmetry")
    return claim is not None and str(claim).strip().upper() == gt_symmetry.strip().upper()


def _entry_captured_fraction(
    entry: Mapping[str, Any], spec: Any, base_params: Any, test_grids: TestGrids
) -> Optional[float]:
    """Structural captured_fraction of one entry's predictor (Phase 2).

    Materializes the entry's predictor and runs the cell's structural probe to
    measure how much of the true broken-symmetry structure it actually
    reproduces. Returns None when the cell has no applicable probe (so the
    caller falls back to the string-match bonus) or when the predictor cannot
    be materialized. Any failure is non-fatal — structure is an ADDITIVE bonus
    on top of the numeric score, never a reason to error a submission.
    """
    try:
        from mirrorlab.eval.numeric import _entry_predictor
        from mirrorlab.eval.structural import structural_score
        predictor = _entry_predictor(entry)
        result = structural_score(predictor, spec, base_params, test_grids=test_grids)
        if not result.applicable:
            return None
        return result.captured_fraction
    except Exception:
        return None


def score_submission(
    submission_set: Sequence[Mapping[str, Any]],
    *,
    target_dim: str | Dim7,
    test_grids: TestGrids,
    gt_symmetry: Optional[str] = None,
    rho: float = RHO_DEFAULT,
    bonus: float = BONUS_DEFAULT,
    canonical_inputs: Optional[Sequence[str]] = None,
) -> float:
    """Return the best-of-k ``S_scen`` per spec §7 (legacy float API).

    Args:
        submission_set: list of submission entries; truncated at 5.
        target_dim: scenario's declared output dim signature (units string
            or pre-parsed 7-tuple) — used by the stage-1 filter.
        test_grids: three-sub-grid mapping consumed by ``evaluate_entry``.
        gt_symmetry: ground-truth broken-symmetry label (e.g. ``"PAR"`` for
            γ-1-1, or ``"none"`` for a baseline scenario). ``None`` disables
            the bonus.
        rho, bonus: CAL knobs; defaults track the spec.

    The symmetry bonus is bound to the BEST-scoring entry (see module
    docstring): it fires only when the highest-scoring entry names the correct
    symmetry, closing the multi-submission free-rider.
    """
    return score_submission_detail(
        submission_set,
        target_dim=target_dim,
        test_grids=test_grids,
        gt_symmetry=gt_symmetry,
        rho=rho,
        bonus=bonus,
        canonical_inputs=canonical_inputs,
    ).best_of_k


def score_submission_detail(
    submission_set: Sequence[Mapping[str, Any]],
    *,
    target_dim: str | Dim7,
    test_grids: TestGrids,
    gt_symmetry: Optional[str] = None,
    rho: float = RHO_DEFAULT,
    bonus: float = BONUS_DEFAULT,
    canonical_inputs: Optional[Sequence[str]] = None,
    spec: Any = None,
    base_params: Any = None,
) -> ScoreDetail:
    """Return both the best-of-k and single-submission scores (see ScoreDetail).

    Single-submission scores only the first declared entry: no max over a set,
    no shotgun penalty, and that entry's own symmetry claim drives the bonus.
    Best-of-k is the spec §7 score with the best-entry bonus binding.

    Phase 2 structural bonus: when ``spec`` + ``base_params`` are supplied and
    the cell has an applicable structural probe, a correct symmetry claim earns
    ``bonus · captured_fraction`` instead of the flat ``bonus``. This keeps the
    claim as the precondition (you must still NAME the broken symmetry) but now
    VERIFIES it — a predictor that names the right label yet collapses to the
    unbroken structure (captured_fraction≈0) earns ≈0 bonus, closing the
    "claim the label, drop the physics" free-rider. Cells with no probe (or no
    spec passed) fall back to the flat string-match bonus, so the change is
    backward-compatible.
    """
    if not submission_set:
        return ScoreDetail(best_of_k=0.0, single_submission=0.0, n_entries=0)
    entries = list(submission_set)[:SET_CAP]
    n = len(entries)

    scored = [
        _entry_score(e, target_dim, test_grids, canonical_inputs) for e in entries
    ]
    best_idx = max(range(n), key=lambda i: scored[i])
    best = scored[best_idx]

    use_structural = spec is not None and base_params is not None
    captured_recorded: Optional[float] = None

    def _bonus_for(entry: Mapping[str, Any]) -> float:
        """Bonus earned by ``entry``: 0 unless its claim matches; then either
        the flat bonus (no probe) or ``bonus · captured_fraction`` (probe)."""
        nonlocal captured_recorded
        if not _claim_matches(entry, gt_symmetry):
            return 0.0
        if use_structural:
            cf = _entry_captured_fraction(entry, spec, base_params, test_grids)
            if cf is not None:
                captured_recorded = cf
                return bonus * max(0.0, min(1.0, cf))
        return bonus

    # --- best-of-k: shotgun penalty + bonus bound to the best entry ----------
    penalty = 1.0 - rho * (n - 1)
    best_of_k = best * max(penalty, 0.0) + _bonus_for(entries[best_idx])

    # --- single-submission: first declared entry alone, no penalty -----------
    single = scored[0] + _bonus_for(entries[0])

    return ScoreDetail(
        best_of_k=float(best_of_k),
        single_submission=float(single),
        n_entries=n,
        captured_fraction=captured_recorded,
    )


__all__ = [
    "RHO_DEFAULT", "BONUS_DEFAULT", "SET_CAP",
    "ScoreDetail", "score_submission", "score_submission_detail",
]
