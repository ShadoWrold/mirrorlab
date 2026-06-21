"""Oracle ceiling agent.

Builds a §5-compliant submission whose predictor wraps the catalog ground-truth
law, with no LLM and no tool calls. This sets the *bench ceiling*: "if an agent
had perfect knowledge of the law and parameters, what S_scen could it reach?" —
which tells us whether sub-baseline scores from real LLMs are LLM-limited or
bench-limited.

The oracle predictor, declared params, and broken-symmetry tag are all DERIVED
from the cell's registered ``CellSpec`` (mirrorlab/spec.py): ``spec.law`` is the
single source of truth that also backs the loader's grid ground truth, so the
oracle and the GT are literally the same callable. On sub-grid (c) the
cf-perturbed law coefficients flow into the predictor under their canonical
names and the law re-evaluates the perturbed physics.
"""

from __future__ import annotations

from typing import Any, Dict, List

from mirrorlab.scenarios.loader import ScenarioInstance

Submission = List[Dict[str, Any]]


# ---- Helpers ---------------------------------------------------------------

def _dim_units(scenario: ScenarioInstance) -> tuple[list[dict], list[dict]]:
    dim = scenario.dim_signature
    inputs = [{"name": n, "units": u} for n, u in (dim.get("inputs") or {}).items()]
    outputs = [{"name": n, "units": u} for n, u in (dim.get("outputs") or {}).items()]
    return inputs, outputs


# ---------------------------------------------------------------------------
# Oracle construction — every cell builds its oracle from its CellSpec.
#
# The per-domain `_pred` predictors, the 48 `_xxx_params` declared-param
# functions, and the `_DISPATCH` / `_DECLARED_PARAMS` / `_BROKEN_SYMMETRY`
# dispatch tables were deleted here (P4 of the CellSpec refactor): the oracle
# predictor, declared params, and broken-symmetry tag are now DERIVED from the
# registered CellSpec (see mirrorlab/spec.py). The scoring eval contract
# (entry shape, sub-grid (c) cf override) is unchanged.

from mirrorlab.spec import (
    get_cell as _get_cell,
    has_cell as _has_cell,
    make_oracle_predictor as _make_oracle,
    declared_params as _declared_params,
)


def broken_symmetry_for(domain_id: str, shift_id: str) -> str:
    """Return the canonical broken-symmetry label (``"none"`` for baselines)."""
    if shift_id == "baseline":
        return "none"
    if _has_cell(domain_id, shift_id):
        return _get_cell(domain_id, shift_id).broken_symmetry
    return "none"


def build_submission(scenario: ScenarioInstance) -> Submission:
    """Return a §5-compliant 1-entry submission wrapping the catalog law.

    The oracle predictor, declared params, and broken-symmetry tag are all
    derived from the cell's registered ``CellSpec`` (one source of truth). The
    entry embeds a callable (``_predictor``) so the eval calls it directly; a
    trivial ``predictor.code`` stub satisfies the schema for consumers that
    re-serialize the submission.
    """
    if not _has_cell(scenario.domain_id, scenario.shift_id):
        raise KeyError(
            f"no CellSpec registered for {(scenario.domain_id, scenario.shift_id)!r}"
        )
    spec = _get_cell(scenario.domain_id, scenario.shift_id)
    base = scenario.sim.params
    inputs, outputs = _dim_units(scenario)
    entry: Dict[str, Any] = {
        "law_id": "L1",
        "formula": "oracle: catalog law wrapped via closure",
        "predictor": {
            "lang": "python",
            "code": "def f(**kw):\n    raise RuntimeError('use _predictor closure')\n",
        },
        "_predictor": _make_oracle(spec, base),
        "inputs": inputs,
        "outputs": outputs,
        "params": _declared_params(spec, base),
        "claim_broken_symmetry": (
            "none" if scenario.shift_id == "baseline" else spec.broken_symmetry
        ),
    }
    return [entry]


class CeilingAgent:
    """Oracle agent — no LLM, no tool calls."""

    def run(self, scenario: ScenarioInstance) -> Submission:
        return build_submission(scenario)


__all__ = [
    "CeilingAgent",
    "build_submission",
    "broken_symmetry_for",
]
