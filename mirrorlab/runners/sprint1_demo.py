"""Sprint 1 end-to-end demo: loader -> agent stub -> eval -> score.

CLI:
    python -m mirrorlab.runners.sprint1_demo --scenario hooke,g_1_1 --seed 0
    python -m mirrorlab.runners.sprint1_demo --scenario hooke,baseline --seed 0

Programmatic:
    result = run_demo("hooke", "gamma_1_1", seed=0)
    print(result["s_scen"])

The runner converts the loader's x-only test grids into the
``(inputs_dict, ground_truth)`` form the evaluator expects, using the live
sim's force law as ground truth (same pattern as ``tests/eval/test_scoring.py``).
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any, Dict, Mapping

import numpy as np

from mirrorlab.eval.dimensional import match_dim
from mirrorlab.eval.numeric import SUBGRID_WEIGHTS, TAU_DEFAULT, evaluate_entry, rmsle
from mirrorlab.eval.scoring import score_submission
from mirrorlab.scenarios import agent_stub
from mirrorlab.scenarios.loader import ScenarioInstance, load

_SHIFT_ALIASES = {
    "g_1_1": "gamma_1_1",
    "γ-1-1": "gamma_1_1",
    "gamma-1-1": "gamma_1_1",
    "baseline": "baseline",
    "gamma_1_1": "gamma_1_1",
}

_GT_SYMMETRY = {
    "baseline": "none",
    "gamma_1_1": "PAR",
}

_GT_FORMULA = {
    "baseline": "F = -k x",
    "gamma_1_1": "F = -k x [1 + eta tanh(x / x_scale)]",
}


def _canon_shift(shift_id: str) -> str:
    key = shift_id.strip().lower()
    if key not in _SHIFT_ALIASES:
        raise SystemExit(
            f"unknown shift_id {shift_id!r}; known: {sorted(set(_SHIFT_ALIASES.values()))}"
        )
    return _SHIFT_ALIASES[key]


def _grids_with_ground_truth(scenario: ScenarioInstance) -> Dict[str, list]:
    """Map x-only loader grids into the evaluator's (inputs, gt) form.

    For the γ-1-1 nonlinearity to actually drive a score gap, the OOD sub-grid
    must extend past ``x_scale`` where ``tanh(x/x_scale)`` saturates. The
    loader's Sprint-1 placeholder grids are referenced to the IC amplitude
    ``x0 = 0.5·x_scale`` (per shift sampler), so its OOD only reaches
    ``2.5·x_scale`` and the stub passes. We override here using ``x_scale``
    as the reference length when present; baseline (no ``x_scale``) keeps
    the loader's grids. See ``docs/sprint1-report.md`` 'Known gaps'.
    """
    sim = scenario.sim
    force = sim._force  # noqa: SLF001 — matches existing test pattern
    params = sim.params

    def pack(xs: np.ndarray) -> list:
        return [({"x": float(x)}, float(force(float(x), params))) for x in xs]

    def pack_counterfactual(xs: np.ndarray) -> list:
        """Per-point GT from perturbed params (CAL-3, spec §6.2 sub-grid c)."""
        cf = scenario.counterfactual_params
        if len(cf) != xs.size:
            raise RuntimeError(
                f"counterfactual_params length {len(cf)} != (c) grid size {xs.size}"
            )
        return [
            ({"x": float(x)}, float(force(float(x), cf[i])))
            for i, x in enumerate(xs)
        ]

    x_scale = getattr(params, "x_scale", None)
    if x_scale is None or not np.isfinite(x_scale) or x_scale <= 0:
        out: Dict[str, list] = {}
        for key, grid in scenario.test_grids.items():
            out[key] = pack_counterfactual(grid) if key == "c" else pack(grid)
        return out

    # γ-1-1 path: rebuild (a)(b) referenced to ``x_scale`` so the OOD sub-grid
    # actually reaches the saturating tail; rebuild (c) the same way *but*
    # re-perturb the params per point so (c) is law-shifted, not just resampled.
    rng = np.random.default_rng(scenario.seed + 7)
    grid_a = np.linspace(-x_scale, x_scale, 11)
    grid_b = np.concatenate(
        [np.linspace(-4.0 * x_scale, -1.5 * x_scale, 5),
         np.linspace(1.5 * x_scale, 4.0 * x_scale, 5)]
    )
    grid_c = rng.uniform(-x_scale, x_scale, size=11)
    from mirrorlab.scenarios.counterfactual import perturb_params
    cf_rng = np.random.default_rng(scenario.seed + 11)
    cf_runner = [
        perturb_params(
            params,
            magnitude=scenario.counterfactual_magnitude,
            rng=cf_rng,
        )
        for _ in range(grid_c.size)
    ]
    grid_c_packed = [
        ({"x": float(x)}, float(force(float(x), cf_runner[i])))
        for i, x in enumerate(grid_c)
    ]
    return {"a": pack(grid_a), "b": pack(grid_b), "c": grid_c_packed}


def _per_subgrid_rmsle(entry: Mapping[str, Any], grids: Mapping[str, list]) -> Dict[str, float]:
    """Per-sub-grid RMSLE for the diagnostic report (mirrors evaluate_entry internals)."""
    from mirrorlab.eval.numeric import _entry_predictor, _safe_call  # noqa: SLF001

    predictor = _entry_predictor(entry)
    out: Dict[str, float] = {}
    for key, grid in grids.items():
        if not grid:
            continue
        preds = [_safe_call(predictor, ins) for ins, _ in grid]
        truths = [gt for _, gt in grid]
        out[key] = rmsle(preds, truths)
    return out


def run_demo(domain_id: str, shift_id: str, *, seed: int = 0) -> Dict[str, Any]:
    """Run loader -> stub -> eval -> score and return a structured report."""
    canon_shift = _canon_shift(shift_id)
    scenario = load(domain_id, canon_shift, seed=seed)
    entry = agent_stub.run(scenario)

    target_dim = scenario.dim_signature["outputs"]["F"]
    stage1_pass = match_dim(entry, target_dim)

    grids = _grids_with_ground_truth(scenario)
    s_entry = evaluate_entry(entry, grids) if stage1_pass else 0.0
    per_grid = _per_subgrid_rmsle(entry, grids) if stage1_pass else {}

    gt_sym = _GT_SYMMETRY.get(canon_shift)
    s_scen = score_submission(
        [entry],
        target_dim=target_dim,
        test_grids=grids,
        gt_symmetry=gt_sym,
    )

    return {
        "domain_id": domain_id,
        "shift_id": canon_shift,
        "seed": seed,
        "entry": entry,
        "stage1_pass": stage1_pass,
        "s_entry": s_entry,
        "s_scen": s_scen,
        "per_subgrid_rmsle": per_grid,
        "gt_formula": _GT_FORMULA.get(canon_shift, "?"),
        "gt_symmetry": gt_sym,
    }


def format_report(result: Mapping[str, Any]) -> str:
    lines = []
    lines.append(
        f"Scenario: {result['domain_id']} / {result['shift_id']} (seed {result['seed']})"
    )
    lines.append(f"Stub agent submitted: {result['entry']['formula']} (linear)")
    lines.append(f"Ground truth: {result['gt_formula']}")
    lines.append(f"Stage-1 (dim): {'PASS' if result['stage1_pass'] else 'FAIL'}")
    lines.append("Stage-2 (numeric):")
    pg = result["per_subgrid_rmsle"]
    label = {"a": "in-domain", "b": "OOD", "c": "counterfactual"}
    for key in ("a", "b", "c"):
        if key in pg:
            lines.append(f"  {label[key]} RMSLE: {pg[key]:.3f}")
    lines.append(f"  s_entry: {result['s_entry']:.3f}")
    lines.append(f"S_scen: {result['s_scen']:.3f}")
    return "\n".join(lines)


def _parse_scenario(raw: str) -> tuple[str, str]:
    if "," not in raw:
        raise SystemExit(f"--scenario expects 'domain,shift'; got {raw!r}")
    domain, shift = raw.split(",", 1)
    return domain.strip(), shift.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sprint1_demo")
    parser.add_argument(
        "--scenario",
        required=True,
        help="domain,shift (e.g. 'hooke,baseline' or 'hooke,g_1_1')",
    )
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    domain, shift = _parse_scenario(args.scenario)
    result = run_demo(domain, shift, seed=args.seed)
    print(format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
