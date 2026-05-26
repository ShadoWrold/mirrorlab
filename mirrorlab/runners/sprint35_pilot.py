"""Sprint 3.5 pilot — re-run with fixed budget contract + gpt-5.4 default.

This is a thin wrapper around :mod:`mirrorlab.runners.sprint3_pilot` that:
  - restores CAL-7 honest budget = 30 / CAL-8 attacker budget = 20
    (Sprint 3 ran them at 20 / 6 to fit a 150-call ceiling; #1
    fixed the prompt-vs-runtime contract so 30/20 is now usable)
  - defaults to two attacker seeds per cell (24 × 2 = 48 attacker runs)
  - keeps a HARD 1000 LLM-call ceiling and aborts attacker mid-sweep
    if the honest phase has eaten too much budget already.

The verdict logic mirrors Sprint 3 but adds STILL CONDITIONAL between
TRUE PASS and TRUE FAIL.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from mirrorlab.attacker.lookup import AttackResult, LookupAttacker
from mirrorlab.attacker.runner import ATTACK_SLICE, PASS_THRESHOLD, AttackReport, _aggregate
from mirrorlab.runners.llm_agent import LLMAgent
from mirrorlab.runners.openai_client import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LLMCallable,
)
from mirrorlab.runners.sprint3_pilot import (
    PILOT_SCENARIOS,
    HonestRunResult,
    PilotPair,
    PilotReport,
    run_honest_pilot,
    score_against_scenario,
)
from mirrorlab.scenarios.loader import load as load_scenario

log = logging.getLogger(__name__)


SPRINT35_HONEST_MAX_TOOL_CALLS = 30   # CAL-7 default
SPRINT35_ATTACKER_MAX_TOOL_CALLS = 20  # CAL-8 default
SPRINT35_HONEST_MAX_WALL = 180
SPRINT35_ATTACKER_MAX_WALL = 90
SPRINT35_HARD_CAP = 1000
SPRINT35_ATTACKER_SEEDS: Tuple[int, ...] = (0, 1)


@dataclass
class Sprint35Report(PilotReport):
    n_honest_calls: int = 0
    n_attacker_calls: int = 0
    attacker_seeds_used: Tuple[int, ...] = SPRINT35_ATTACKER_SEEDS
    attacker_truncated: bool = False
    verdict: str = "UNKNOWN"  # TRUE PASS | STILL CONDITIONAL | TRUE FAIL

    def as_dict(self) -> Dict[str, Any]:
        d = super().as_dict()
        d.update({
            "n_honest_calls": self.n_honest_calls,
            "n_attacker_calls": self.n_attacker_calls,
            "attacker_seeds_used": list(self.attacker_seeds_used),
            "attacker_truncated": self.attacker_truncated,
            "verdict": self.verdict,
        })
        return d


def run_attacker_pilot_capped(
    attacker_factory: Callable[[], LookupAttacker],
    *,
    seeds: Sequence[int],
    budget_remaining: int,
    slice_pairs: Sequence[Tuple[str, str]] = ATTACK_SLICE,
    threshold: float = PASS_THRESHOLD,
) -> Tuple[AttackReport, int, bool]:
    """Like sprint3_pilot.run_attacker_pilot but stops if budget exhausted."""
    results: List[AttackResult] = []
    scores: List[float] = []
    calls_used = 0
    truncated = False
    cells = [(d, s, seed) for d, s in slice_pairs for seed in seeds]
    for domain_id, shift_id, seed in cells:
        if calls_used >= budget_remaining:
            log.warning("attacker budget exhausted at %s/%s seed=%d; stop",
                        domain_id, shift_id, seed)
            truncated = True
            break
        try:
            scenario = load_scenario(domain_id, shift_id, seed=int(seed))
        except Exception as exc:  # noqa: BLE001
            log.warning("skip %s/%s seed=%d: %s", domain_id, shift_id, seed, exc)
            continue
        attacker = attacker_factory()
        try:
            result = attacker.run(scenario)
        except Exception as exc:  # noqa: BLE001
            log.error("attacker run crashed %s/%s seed=%d: %s",
                      domain_id, shift_id, seed, exc)
            continue
        score = score_against_scenario(scenario, result.submission)
        results.append(result)
        scores.append(score)
        calls_used += int(getattr(result, "llm_turns", 0))
        log.info("attack %s/%s seed=%d → S=%.4f claim=%s turns=%d",
                 domain_id, shift_id, seed, score, result.claimed_law,
                 getattr(result, "llm_turns", 0))
    cell_scores, s_bench = _aggregate(results, scores)
    report = AttackReport(
        results=results,
        scores=scores,
        cell_scores=cell_scores,
        s_bench_lookup=s_bench,
        passed=s_bench < threshold,
        threshold=threshold,
        seeds=tuple(seeds),
        n_scenarios=len(results),
    )
    return report, calls_used, truncated


def _verdict(
    honest: List[HonestRunResult],
    attacker: Optional[AttackReport],
) -> str:
    if attacker is None or not attacker.results:
        return "STILL CONDITIONAL"
    n_submitted = sum(1 for r in honest if r.submission_len > 0)
    attacker_safe = attacker.s_bench_lookup < attacker.threshold
    if n_submitted >= 4 and attacker_safe:
        return "TRUE PASS"
    if not attacker_safe:
        return "TRUE FAIL"
    return "STILL CONDITIONAL"


def run_sprint35_pilot(
    *,
    honest_llm_call: Optional[LLMCallable] = None,
    attacker_llm_call: Optional[LLMCallable] = None,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str = "",
    honest_max_tool_calls: int = SPRINT35_HONEST_MAX_TOOL_CALLS,
    honest_max_wall_seconds: int = SPRINT35_HONEST_MAX_WALL,
    attacker_max_tool_calls: int = SPRINT35_ATTACKER_MAX_TOOL_CALLS,
    attacker_max_wall_seconds: int = SPRINT35_ATTACKER_MAX_WALL,
    attacker_seeds: Sequence[int] = SPRINT35_ATTACKER_SEEDS,
    seed: int = 0,
    scenarios: Sequence[PilotPair] = PILOT_SCENARIOS,
    threshold: float = PASS_THRESHOLD,
    hard_cap: int = SPRINT35_HARD_CAP,
) -> Sprint35Report:
    def _honest_factory() -> LLMAgent:
        return LLMAgent(
            model=model,
            base_url=base_url,
            api_key=api_key,
            max_tool_calls=honest_max_tool_calls,
            max_wall_seconds=honest_max_wall_seconds,
            llm_call=honest_llm_call,
            fallback_to_stub=False,
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

    log.info("sprint3.5 honest phase: 5 scenarios, max_tool_calls=%d",
             honest_max_tool_calls)
    honest = run_honest_pilot(_honest_factory, scenarios, seed=seed)
    n_honest = sum(r.n_llm_turns for r in honest)
    log.info("sprint3.5 honest phase done: %d llm turns", n_honest)

    attacker_budget = max(0, hard_cap - n_honest)
    log.info("sprint3.5 attacker phase: %d cells × %d seeds, budget=%d",
             len(ATTACK_SLICE), len(attacker_seeds), attacker_budget)
    attacker, n_attacker, truncated = run_attacker_pilot_capped(
        _attacker_factory,
        seeds=attacker_seeds,
        budget_remaining=attacker_budget,
        threshold=threshold,
    )
    log.info("sprint3.5 attacker phase done: %d llm turns (truncated=%s)",
             n_attacker, truncated)

    pipeline_ok = all(
        r.terminated_by not in ("llm_error",) and not r.terminated_by.startswith("crash:")
        for r in honest
    )
    overall = pipeline_ok and attacker.passed

    notes: List[str] = []
    n_submitted = sum(1 for r in honest if r.submission_len > 0)
    if n_submitted < len(honest):
        notes.append(
            f"{len(honest) - n_submitted}/{len(honest)} honest cells did not submit "
            "— investigate per-cell terminated_by"
        )
    if truncated:
        notes.append(
            f"attacker sweep truncated to fit {hard_cap}-call hard cap "
            f"(honest={n_honest}, attacker={n_attacker})"
        )
    if not attacker.passed:
        notes.append(
            f"attacker S_bench^lookup={attacker.s_bench_lookup:.4f} ≥ {threshold:.2f}; "
            "spec §8 catalog Round-3 escalation flagged (NOT auto-triggered)."
        )

    verdict = _verdict(honest, attacker)

    return Sprint35Report(
        honest=honest,
        attacker=attacker,
        model=model,
        n_llm_calls_estimate=n_honest + n_attacker,
        pilot_pipeline_ok=pipeline_ok,
        attacker_passed=attacker.passed,
        overall_passed=overall,
        threshold=threshold,
        notes=notes,
        n_honest_calls=n_honest,
        n_attacker_calls=n_attacker,
        attacker_seeds_used=tuple(attacker_seeds),
        attacker_truncated=truncated,
        verdict=verdict,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sprint35_pilot")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--honest-max-tool-calls", type=int, default=SPRINT35_HONEST_MAX_TOOL_CALLS)
    parser.add_argument("--honest-max-wall-seconds", type=int, default=SPRINT35_HONEST_MAX_WALL)
    parser.add_argument("--attacker-max-tool-calls", type=int, default=SPRINT35_ATTACKER_MAX_TOOL_CALLS)
    parser.add_argument("--attacker-max-wall-seconds", type=int, default=SPRINT35_ATTACKER_MAX_WALL)
    parser.add_argument("--attacker-seeds", default="0,1")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--threshold", type=float, default=PASS_THRESHOLD)
    parser.add_argument("--hard-cap", type=int, default=SPRINT35_HARD_CAP)
    parser.add_argument("--out", default="-")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        raise SystemExit(f"env var {args.api_key_env!r} is empty; export the key")

    attacker_seeds = tuple(int(s) for s in args.attacker_seeds.split(",") if s.strip())

    report = run_sprint35_pilot(
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
        hard_cap=args.hard_cap,
    )

    payload = json.dumps(report.as_dict(), indent=2, default=repr)
    if args.out == "-":
        print(payload)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)

    print(
        f"\n=== sprint3.5 pilot {report.verdict} ===\n"
        f"  honest submitted          = {sum(1 for r in report.honest if r.submission_len > 0)}/{len(report.honest)}\n"
        f"  attacker S_bench^lookup   = {report.attacker.s_bench_lookup:.4f} "
        f"(threshold < {report.threshold}) → "
        f"{'PASS' if report.attacker_passed else 'FAIL'}\n"
        f"  llm calls (turns)         = {report.n_llm_calls_estimate} "
        f"(honest={report.n_honest_calls}, attacker={report.n_attacker_calls})\n"
        f"  attacker truncated        = {report.attacker_truncated}\n"
        f"  notes: {len(report.notes)}",
        file=sys.stderr,
    )
    return 0 if report.verdict == "TRUE PASS" else 1


__all__ = [
    "Sprint35Report",
    "run_sprint35_pilot",
    "SPRINT35_HONEST_MAX_TOOL_CALLS",
    "SPRINT35_ATTACKER_MAX_TOOL_CALLS",
    "SPRINT35_HARD_CAP",
    "SPRINT35_ATTACKER_SEEDS",
]


if __name__ == "__main__":
    sys.exit(main())
