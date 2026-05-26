"""Evaluation pipeline: stage-1 dim filter + stage-2 numeric probe + scoring.

Per spec §6–§7. CAL defaults are baked into the submodules and re-exported
here so callers can override them at the scoring entry point.
"""

from mirrorlab.eval.dimensional import Dim7, match_dim, parse_dim
from mirrorlab.eval.numeric import (
    CLAMP,
    SUBGRID_WEIGHTS,
    TAU_DEFAULT,
    evaluate_entry,
    rmsle,
)
from mirrorlab.eval.scoring import BONUS_DEFAULT, RHO_DEFAULT, SET_CAP, score_submission

__all__ = [
    "Dim7", "parse_dim", "match_dim",
    "rmsle", "evaluate_entry",
    "CLAMP", "TAU_DEFAULT", "SUBGRID_WEIGHTS",
    "score_submission",
    "RHO_DEFAULT", "BONUS_DEFAULT", "SET_CAP",
]
