"""CLI: ``python -m mirrorlab.attacker --slice gamma+delta --seeds 0,1,2``.

Produces an attack report as JSON to stdout plus a short summary table to
stderr. Requires a configured local proxy + API key (or you can pass
``--dry-run`` to validate the wiring with the stub-only attacker —
intended for smoke tests / pre-flight checks, not for the real CAL-9 gate).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import List, Sequence, Tuple

from mirrorlab.attacker.lookup import LookupAttacker
from mirrorlab.attacker.runner import (
    ATTACK_SLICE,
    DEFAULT_SEEDS,
    PASS_THRESHOLD,
    AttackReport,
    run_attack_sweep,
)
from mirrorlab.runners.openai_client import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    OpenAIClient,
)


def _parse_seeds(spec: str) -> Tuple[int, ...]:
    return tuple(int(s) for s in spec.split(",") if s.strip())


def _filter_slice(spec: str) -> Tuple[Tuple[str, str], ...]:
    spec = spec.strip().lower()
    if spec in ("gamma+delta", "all", "g+d"):
        return ATTACK_SLICE
    if spec == "gamma":
        return tuple(p for p in ATTACK_SLICE if "gamma_" in p[1])
    if spec == "delta":
        return tuple(p for p in ATTACK_SLICE if "delta_" in p[1])
    raise SystemExit(f"unknown slice {spec!r}; choose gamma+delta|gamma|delta")


def _print_summary(report: AttackReport, *, file=sys.stderr) -> None:
    print(f"\n=== lookup-attacker sweep summary ===", file=file)
    print(f"  scenarios   : {report.n_scenarios}", file=file)
    print(f"  seeds       : {list(report.seeds)}", file=file)
    print(f"  threshold   : S_bench^lookup < {report.threshold}", file=file)
    print(f"  result      : S_bench^lookup = {report.s_bench_lookup:.4f} "
          f"({'PASS' if report.passed else 'FAIL'})", file=file)
    print(f"\n  per-cell scores:", file=file)
    for (d, s), v in sorted(report.cell_scores.items()):
        print(f"    {d:>10}/{s:<14}  {v:.4f}", file=file)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mirrorlab.attacker")
    parser.add_argument("--slice", default="gamma+delta",
                        help="gamma+delta (default) | gamma | delta")
    parser.add_argument("--seeds", default=",".join(str(s) for s in DEFAULT_SEEDS),
                        help="comma-separated seed list (default 0,1,2)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV,
                        help=f"env var holding the bearer token "
                             f"(default {DEFAULT_API_KEY_ENV})")
    parser.add_argument("--max-tool-calls", type=int, default=20,
                        help="CAL-8 attacker budget K (default 20)")
    parser.add_argument("--max-wall-seconds", type=int, default=60)
    parser.add_argument("--threshold", type=float, default=PASS_THRESHOLD,
                        help="CAL-9 pass threshold (default 0.50)")
    parser.add_argument("--out", default="-",
                        help="JSON report path (default stdout)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    slice_pairs = _filter_slice(args.slice)
    seeds = _parse_seeds(args.seeds)

    client = OpenAIClient.from_env(
        model=args.model,
        base_url=args.base_url,
        env_var=args.api_key_env,
        timeout=float(args.max_wall_seconds),
    )
    attacker = LookupAttacker(
        model=args.model,
        base_url=args.base_url,
        api_key=client.api_key,
        max_tool_calls=args.max_tool_calls,
        max_wall_seconds=args.max_wall_seconds,
    )

    report = run_attack_sweep(
        attacker,
        slice_pairs=slice_pairs,
        seeds=seeds,
        threshold=args.threshold,
    )

    payload = json.dumps(report.as_dict(), indent=2)
    if args.out == "-":
        print(payload)
    else:
        with open(args.out, "w") as f:
            f.write(payload + "\n")
    _print_summary(report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
