"""Sprint 3 exit pilot (spec §9.2).

Runs a 5-scenario honest LLM sweep + the 24-cell γ∪δ lookup-attacker slice
under a constrained LLM-call budget (≤ 150 total).

Pilot scenarios are chosen for diversity per spec §9.2:
  1 baseline + 2 γ-shifts + 2 δ-shifts, spanning at least 3 (here 5)
  domains. Reduced ``max_tool_calls`` budgets keep the run inside the
  pilot ceiling; the harness exposes the budgets so future re-runs (e.g.
  the CAL-9 re-lock after the cal-tuner pilot data lands) can dial them
  back up.

Exit criterion: pilot pipeline runs through without exceptions on the
5 scenarios *and* attacker ``S_bench^lookup < 0.50``. PASS / FAIL is
explicit on stdout in the JSON ``passed`` field.

Per-scenario scoring fix-up
---------------------------
``mirrorlab.attacker.runner._pack_grids`` only handles the Hooke domain
(it pre-dates task #7's grid wiring for the other 11 domains). For pilot
purposes we re-implement a *universal* grid packer that:

  - Hooke → builds ``(inputs_dict, gt_value)`` tuples by calling
    ``sim._force`` over the loader's raw ``x`` arrays.
  - All other domains → uses the loader's already-packed
    ``list[(inputs_dict, gt_value)]`` directly.

This is a pilot-local helper, not a contract change: a follow-up sprint
will fold the same logic back into the attacker runner.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from mirrorlab.attacker.lookup import AttackResult, LookupAttacker
from mirrorlab.attacker.runner import (
    ATTACK_SLICE,
    PASS_THRESHOLD,
    AttackReport,
    _aggregate,
)
from mirrorlab.eval.scoring import score_submission
from mirrorlab.runners.llm_agent import AgentTrace, LLMAgent
from mirrorlab.runners.openai_client import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LLMCallable,
    OpenAIClient,
)
from mirrorlab.scenarios.loader import ScenarioInstance, load as load_scenario

log = logging.getLogger(__name__)


# ---- Pilot scenario selection (locked) ----------------------------------
#
# 1 baseline + 2 γ + 2 δ, 5 distinct domains. Each tuple is
# ``(domain_id, shift_id, gt_symmetry_label)``. ``gt_symmetry`` is set to
# ``None`` (no symmetry bonus checked) for non-baseline shifts in this
# pilot — the catalog R2-final symmetry labels are fixed and could be
# wired in once the CAL-5 bonus logic is locked. Baseline is "none".

PilotPair = Tuple[str, str, Optional[str]]

PILOT_SCENARIOS: Tuple[PilotPair, ...] = (
    ("hooke",    "baseline",   "none"),  # 1 baseline (PAR + everything)
    ("pendulum", "gamma_4_1",  None),    # γ — PAR break via (1-cos θ) drive
    ("decay",    "gamma_12_1", None),    # γ — T-translation break
    ("rlc",      "delta_6_1",  None),    # δ — energy violation (parametric drive)
    ("kinetics", "delta_11_1", None),    # δ — memory-kernel (non-Markovian)
)


# ---- Per-scenario universal grid packer --------------------------------

def _hooke_force_fn(scenario: ScenarioInstance):
    """Resolve a (x, params) → F callable for any Hooke (baseline or shift).

    The baseline ``HookeBaseline`` exposes ``sim._force`` directly. The
    γ-1-1 shift inherits from ``SimInstance`` so it does too. The γ-1-2
    (2-D anisotropic) and δ-1-1 (velocity-dependent) shifts use their own
    ``_Sim`` classes that do NOT expose ``_force``, so we fall back to the
    shift module's catalog ``shifted_force`` and project it down to the
    1-D ``x`` channel the Hooke grid samples on:

      - γ-1-2 ``shifted_force((x, y), p)`` → take x-component at y=0.
      - δ-1-1 ``shifted_force(x, v, p)`` → evaluate at v=0.

    Both projections match how the ceiling oracle's predictor maps the
    same shift down to the grid's ``x``-only input vocabulary, so honest
    LLM agents are scored on the same channel the ceiling reports.
    """
    sim = scenario.sim
    direct = getattr(sim, "_force", None)
    if direct is not None:
        return direct
    shift_id = scenario.shift_id
    if shift_id == "gamma_1_2":
        from mirrorlab.shifts import hooke_g_1_2

        def _force(x, params):
            fx, _ = hooke_g_1_2.shifted_force((float(x), 0.0), params)
            return float(fx)

        return _force
    if shift_id == "delta_1_1":
        from mirrorlab.shifts import hooke_d_1_1

        def _force(x, params):
            return float(hooke_d_1_1.shifted_force(float(x), 0.0, params))

        return _force
    if shift_id == "gamma_1_1":
        from mirrorlab.shifts import hooke_g_1_1

        def _force(x, params):
            return float(hooke_g_1_1.shifted_force(float(x), params))

        return _force
    return None


def pack_grids(scenario: ScenarioInstance) -> Dict[str, List[Tuple[Dict[str, float], float]]]:
    grids = scenario.test_grids
    if not grids:
        return {}
    consts = _scenario_constants(scenario)
    if scenario.domain_id == "hooke":
        sim = scenario.sim
        force = _hooke_force_fn(scenario)
        params = getattr(sim, "params", None)
        if force is None or params is None:
            return {}
        out: Dict[str, List[Tuple[Dict[str, float], float]]] = {}
        for key, arr in grids.items():
            try:
                out[key] = [
                    ({**consts, "x": float(x)}, float(force(float(x), params)))
                    for x in arr
                ]
            except Exception:  # noqa: BLE001
                out[key] = []
        return out
    # Other domains: loader already returns packed list[(inputs, gt)].
    out_other: Dict[str, List[Tuple[Dict[str, float], float]]] = {}
    for key, val in grids.items():
        try:
            packed = list(val)
        except TypeError:
            packed = []
        if packed and isinstance(packed[0], tuple):
            # Sub-grid (c) carries a third element (cf_params_obj) per
            # blueprint-xy §2.3; (a)/(b) are 2-tuples. Preserve the cf
            # payload so downstream evaluation can still override
            # declared predictor params on (c).
            enriched: list = []
            for entry in packed:
                ins, gt = entry[0], entry[1]
                merged_ins = {**consts, **dict(ins)}
                if len(entry) == 3:
                    enriched.append((merged_ins, float(gt), entry[2]))
                else:
                    enriched.append((merged_ins, float(gt)))
            out_other[key] = enriched
        else:
            out_other[key] = []
    return out_other


def _scenario_constants(scenario: ScenarioInstance) -> Dict[str, float]:
    """Extract scalar sim params so they are available to LLM predictors.

    Many LLM submissions treat scenario constants (q1, q2, k_e, ...) as
    formula inputs even though the test grid only varies one or two of
    them. Injecting them into every grid input dict lets the predictor's
    declared signature receive them — the eval-side signature filter then
    drops any names the predictor does not consume.

    Some shift modules rename canonical params (e.g. ``q_src`` for ``q1``);
    we canonicalize those back to the names declared in the scenario's
    ``dim_signature.params`` block via a small alias table so an LLM that
    used the textbook name still hits the right value.
    """
    sim = getattr(scenario, "sim", None)
    params = getattr(sim, "params", None)
    if params is None:
        return {}
    raw: Dict[str, float] = {}
    for name in dir(params):
        if name.startswith("_"):
            continue
        try:
            val = getattr(params, name)
        except Exception:  # noqa: BLE001
            continue
        if callable(val):
            continue
        try:
            f = float(val)
        except (TypeError, ValueError):
            continue
        import math as _math
        if not _math.isfinite(f):
            continue
        raw[name] = f

    # Canonicalize via aliases keyed by dim_signature.params names.
    aliases: Dict[str, Tuple[str, ...]] = {
        "q1": ("q1", "q_src", "src1_q"),
        "q2": ("q2", "q_test", "src2_q"),
        "k_e": ("k_e",),
        "G": ("G", "G0"),
        "g_over_L": ("g_over_L", "g0_over_L"),
        "g": ("g", "g0"),
        "L": ("L", "L0", "L1"),
        "R": ("R", "R0", "R1"),
        "C": ("C", "C0", "C1"),
        "n1": ("n1",),
        "n2": ("n2", "n0"),
        "lam": ("lam", "lam0", "lambda_"),
        "k": ("k", "k0", "alpha"),
    }
    dim_params = (scenario.dim_signature.get("params") or {}) if scenario.dim_signature else {}
    canon: Dict[str, float] = dict(raw)
    for canon_name in dim_params:
        if canon_name in canon:
            continue
        for alias in aliases.get(canon_name, (canon_name,)):
            if alias in raw:
                canon[canon_name] = raw[alias]
                break
    return canon


def _target_dim(scenario: ScenarioInstance) -> Optional[str]:
    outputs = scenario.dim_signature.get("outputs") or {}
    if not outputs:
        return None
    return next(iter(outputs.values()))


def score_against_scenario(
    scenario: ScenarioInstance,
    submission: List[Mapping[str, Any]],
    *,
    gt_symmetry: Optional[str] = None,
) -> float:
    target = _target_dim(scenario)
    if target is None:
        return 0.0
    packed = pack_grids(scenario)
    if not packed:
        return 0.0
    canonical = list((scenario.dim_signature.get("inputs") or {}).keys())
    return float(
        score_submission(
            submission,
            target_dim=target,
            test_grids=packed,
            gt_symmetry=gt_symmetry,
            canonical_inputs=canonical,
        )
    )


# ---- Pilot result containers -------------------------------------------

@dataclass
class HonestRunResult:
    domain_id: str
    shift_id: str
    seed: int
    s_scen: float
    n_tool_calls: int
    n_llm_turns: int
    elapsed_s: float
    terminated_by: str
    submission_len: int
    submission: List[Dict[str, Any]] = field(default_factory=list)
    parse_errors: int = 0
    gt_symmetry: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["s_scen"] = round(self.s_scen, 6)
        d["elapsed_s"] = round(self.elapsed_s, 4)
        return d


@dataclass
class PilotReport:
    honest: List[HonestRunResult] = field(default_factory=list)
    attacker: Optional[AttackReport] = None
    model: str = DEFAULT_MODEL
    n_llm_calls_estimate: int = 0
    pilot_pipeline_ok: bool = False  # all 5 scenarios produced a non-crashing run
    attacker_passed: bool = False
    overall_passed: bool = False
    threshold: float = PASS_THRESHOLD
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "threshold": self.threshold,
            "pilot_pipeline_ok": self.pilot_pipeline_ok,
            "attacker_passed": self.attacker_passed,
            "overall_passed": self.overall_passed,
            "n_llm_calls_estimate": self.n_llm_calls_estimate,
            "honest": [r.as_dict() for r in self.honest],
            "attacker": self.attacker.as_dict() if self.attacker is not None else None,
            "notes": list(self.notes),
        }


# ---- Honest pilot driver -----------------------------------------------

def run_honest_pilot(
    agent_factory: Callable[[], LLMAgent],
    scenarios: Sequence[PilotPair] = PILOT_SCENARIOS,
    *,
    seed: int = 0,
) -> List[HonestRunResult]:
    results: List[HonestRunResult] = []
    for domain_id, shift_id, gt_sym in scenarios:
        scenario = load_scenario(domain_id, shift_id, seed=seed)
        agent = agent_factory()
        t0 = time.monotonic()
        try:
            submission, trace = agent.run_with_trace(scenario)
        except Exception as exc:  # noqa: BLE001 — pilot tolerates per-scenario failure
            log.error("honest run crashed: %s/%s seed=%d: %s",
                      domain_id, shift_id, seed, exc)
            submission, trace = [], AgentTrace(terminated_by=f"crash:{type(exc).__name__}")
        elapsed = time.monotonic() - t0
        s_scen = score_against_scenario(scenario, submission, gt_symmetry=gt_sym)
        results.append(
            HonestRunResult(
                domain_id=domain_id,
                shift_id=shift_id,
                seed=seed,
                s_scen=s_scen,
                n_tool_calls=trace.tool_calls,
                n_llm_turns=trace.llm_turns,
                elapsed_s=elapsed,
                terminated_by=trace.terminated_by,
                submission_len=len(submission),
                submission=[dict(e) for e in submission[:5]],
                parse_errors=trace.parse_errors,
                gt_symmetry=gt_sym,
            )
        )
        log.info(
            "honest %s/%s seed=%d → S_scen=%.4f calls=%d turns=%d term=%s",
            domain_id, shift_id, seed, s_scen,
            trace.tool_calls, trace.llm_turns, trace.terminated_by,
        )
    return results


# ---- Attacker pilot driver ---------------------------------------------

def run_attacker_pilot(
    attacker_factory: Callable[[], LookupAttacker],
    *,
    seeds: Sequence[int] = (0,),
    slice_pairs: Sequence[Tuple[str, str]] = ATTACK_SLICE,
    threshold: float = PASS_THRESHOLD,
) -> AttackReport:
    """Reduced-budget attacker sweep with universal grid packing."""
    results: List[AttackResult] = []
    scores: List[float] = []
    for domain_id, shift_id in slice_pairs:
        for seed in seeds:
            try:
                scenario = load_scenario(domain_id, shift_id, seed=int(seed))
            except Exception as exc:  # noqa: BLE001
                log.warning("skip %s/%s seed=%d: %s",
                            domain_id, shift_id, seed, exc)
                continue
            attacker = attacker_factory()
            try:
                result = attacker.run(scenario)
            except Exception as exc:  # noqa: BLE001
                log.error("attacker run crashed %s/%s: %s",
                          domain_id, shift_id, exc)
                continue
            score = score_against_scenario(scenario, result.submission)
            results.append(result)
            scores.append(score)
            log.info("attack %s/%s seed=%d → S=%.4f claim=%s",
                     domain_id, shift_id, seed, score, result.claimed_law)
    cell_scores, s_bench = _aggregate(results, scores)
    return AttackReport(
        results=results,
        scores=scores,
        cell_scores=cell_scores,
        s_bench_lookup=s_bench,
        passed=s_bench < threshold,
        threshold=threshold,
        seeds=tuple(seeds),
        n_scenarios=len(results),
    )


# ---- Top-level driver --------------------------------------------------

def run_pilot(
    *,
    honest_llm_call: Optional[LLMCallable] = None,
    attacker_llm_call: Optional[LLMCallable] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str = "",
    honest_max_tool_calls: int = 12,
    honest_max_wall_seconds: int = 90,
    attacker_max_tool_calls: int = 2,
    attacker_max_wall_seconds: int = 45,
    attacker_seeds: Sequence[int] = (0,),
    seed: int = 0,
    scenarios: Sequence[PilotPair] = PILOT_SCENARIOS,
    threshold: float = PASS_THRESHOLD,
) -> PilotReport:
    """End-to-end pilot.

    Pass ``honest_llm_call`` / ``attacker_llm_call`` to inject mock LLMs
    (tests). Omitting them constructs real ``OpenAIClient`` instances
    against the local proxy — credentials picked up from ``api_key`` or
    from ``MIRRORLAB_LLM_API_KEY`` if ``api_key`` is empty.
    """

    def _honest_factory() -> LLMAgent:
        return LLMAgent(
            model=model,
            base_url=base_url,
            api_key=api_key,
            max_tool_calls=honest_max_tool_calls,
            max_wall_seconds=honest_max_wall_seconds,
            llm_call=honest_llm_call,
            fallback_to_stub=False,  # pilot wants the *real* LLM signal
        )

    def _attacker_factory() -> LookupAttacker:
        return LookupAttacker(
            model=model,
            base_url=base_url,
            api_key=api_key,
            max_tool_calls=attacker_max_tool_calls,
            max_wall_seconds=attacker_max_wall_seconds,
            llm_call=attacker_llm_call,
        )

    honest = run_honest_pilot(_honest_factory, scenarios, seed=seed)
    attacker = run_attacker_pilot(
        _attacker_factory,
        seeds=attacker_seeds,
        threshold=threshold,
    )

    # LLM-call accounting: each tool call corresponds to one assistant
    # turn (the assistant emits the tool call then a follow-up turn after
    # the tool result). Counting ``llm_turns`` from the honest trace plus
    # ``llm_turns`` from each attacker result is the closest we get.
    n_calls = sum(r.n_llm_turns for r in honest) + sum(
        getattr(r, "llm_turns", 0) for r in attacker.results
    )

    pipeline_ok = all(
        r.terminated_by not in ("llm_error",) and not r.terminated_by.startswith("crash:")
        for r in honest
    )
    overall = pipeline_ok and attacker.passed

    notes: List[str] = []
    pathological = [
        r for r in honest
        if r.s_scen in (0.0, 1.0) or r.submission_len == 0
    ]
    if pathological:
        notes.append(
            "pathological-looking honest score (0/1 or empty submission) — "
            "investigate parse / dispatch before declaring verdict; "
            f"cells={[(r.domain_id, r.shift_id, r.s_scen, r.terminated_by) for r in pathological]}"
        )
    if not attacker.passed:
        notes.append(
            f"attacker S_bench^lookup={attacker.s_bench_lookup:.4f} ≥ {threshold:.2f}; "
            "spec §8 requires catalog Round-3 escalation flag (NOT auto-triggered)."
        )

    return PilotReport(
        honest=honest,
        attacker=attacker,
        model=model,
        n_llm_calls_estimate=n_calls,
        pilot_pipeline_ok=pipeline_ok,
        attacker_passed=attacker.passed,
        overall_passed=overall,
        threshold=threshold,
        notes=notes,
    )


# ---- CLI ---------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sprint3_pilot")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--honest-max-tool-calls", type=int, default=12)
    parser.add_argument("--honest-max-wall-seconds", type=int, default=90)
    parser.add_argument("--attacker-max-tool-calls", type=int, default=2)
    parser.add_argument("--attacker-max-wall-seconds", type=int, default=45)
    parser.add_argument("--attacker-seeds", default="0",
                        help="comma-separated seed list (default '0')")
    parser.add_argument("--seed", type=int, default=0,
                        help="seed for honest scenarios")
    parser.add_argument("--threshold", type=float, default=PASS_THRESHOLD)
    parser.add_argument("--out", default="-", help="JSON output path (default stdout)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        raise SystemExit(
            f"env var {args.api_key_env!r} is empty; export the key before running "
            "the pilot. (Pilot does not log or persist the key.)"
        )

    attacker_seeds = tuple(int(s) for s in args.attacker_seeds.split(",") if s.strip())

    report = run_pilot(
        model=args.model,
        base_url=args.base_url,
        api_key=api_key,
        honest_max_tool_calls=args.honest_max_tool_calls,
        honest_max_wall_seconds=args.honest_max_wall_seconds,
        attacker_max_tool_calls=args.attacker_max_tool_calls,
        attacker_max_wall_seconds=args.attacker_max_wall_seconds,
        attacker_seeds=attacker_seeds,
        seed=args.seed,
        threshold=args.threshold,
    )

    payload = json.dumps(report.as_dict(), indent=2, default=repr)
    if args.out == "-":
        print(payload)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)

    # Concise stderr verdict.
    verdict = "PASS" if report.overall_passed else "FAIL"
    print(
        f"\n=== sprint3 pilot {verdict} ===\n"
        f"  pipeline_ok = {report.pilot_pipeline_ok}\n"
        f"  attacker S_bench^lookup = {report.attacker.s_bench_lookup:.4f} "
        f"(threshold < {report.threshold}) → "
        f"{'PASS' if report.attacker_passed else 'FAIL'}\n"
        f"  llm calls (turns)        = {report.n_llm_calls_estimate}\n"
        f"  notes: {len(report.notes)}",
        file=sys.stderr,
    )
    return 0 if report.overall_passed else 1


__all__ = [
    "PILOT_SCENARIOS",
    "HonestRunResult",
    "PilotPair",
    "PilotReport",
    "pack_grids",
    "run_attacker_pilot",
    "run_honest_pilot",
    "run_pilot",
    "score_against_scenario",
]


if __name__ == "__main__":
    sys.exit(main())
