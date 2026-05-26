"""CLI: run one LLM scenario end-to-end via the local proxy.

Example
-------
::

    export MIRRORLAB_LLM_API_KEY=sk-...
    python -m mirrorlab.runners.run_one_scenario \\
        --domain hooke --shift gamma_1_1 --seed 0 \\
        --model claude-sonnet-4-6 \\
        --base-url http://127.0.0.1:4142/v1

The script is intentionally minimal: it loads a scenario, runs the LLM
agent under CAL-7 budgets, prints the submission + trace summary, and
scores it through ``mirrorlab.eval.scoring`` when a wired ``test_grids``
sub-grid exists for the domain (Sprint 3: hooke only). The point of a
manual smoke is to confirm the *pipe* works; do NOT assume a high score.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from mirrorlab.runners.llm_agent import LLMAgent
from mirrorlab.runners.openai_client import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    OpenAIClient,
)
from mirrorlab.scenarios.loader import load as load_scenario


def _maybe_score(scenario, submission) -> Optional[float]:
    if not scenario.test_grids:
        return None
    try:
        from mirrorlab.eval.scoring import score_submission
    except Exception:  # pragma: no cover
        return None
    # Pick the declared output dim as the target.
    out_dim = next(iter(scenario.dim_signature.get("outputs", {}).values()), None)
    if out_dim is None:
        return None
    try:
        return score_submission(
            submission,
            target_dim=out_dim,
            test_grids=scenario.test_grids,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] scoring failed: {exc}", file=sys.stderr)
        return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="run_one_scenario")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--shift", default="baseline")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--max-tool-calls", type=int, default=30)
    parser.add_argument("--max-wall-seconds", type=int, default=60)
    parser.add_argument("--no-fallback", action="store_true",
                        help="Disable rule-based stub fallback on budget exhaustion.")
    args = parser.parse_args(argv)

    client = OpenAIClient.from_env(
        model=args.model,
        base_url=args.base_url,
        env_var=args.api_key_env,
        timeout=float(args.max_wall_seconds),
    )
    agent = LLMAgent(
        model=args.model,
        base_url=args.base_url,
        api_key=client.api_key,
        max_tool_calls=args.max_tool_calls,
        max_wall_seconds=args.max_wall_seconds,
        llm_call=lambda messages, tools: client.chat(messages, tools),
        fallback_to_stub=not args.no_fallback,
    )

    scenario = load_scenario(args.domain, args.shift, seed=args.seed)
    submission, trace = agent.run_with_trace(scenario)
    score = _maybe_score(scenario, submission)

    print("=== submission ===")
    print(json.dumps(submission, indent=2, default=repr))
    print("=== trace ===")
    print(json.dumps({
        "tool_calls": trace.tool_calls,
        "llm_turns": trace.llm_turns,
        "elapsed_s": round(trace.elapsed_s, 3),
        "terminated_by": trace.terminated_by,
        "parse_errors": trace.parse_errors,
    }, indent=2))
    if score is not None:
        print(f"S_scen = {score:.4f}")
    else:
        print("S_scen = (no test grids wired for this domain)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
