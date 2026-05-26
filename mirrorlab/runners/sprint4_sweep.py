"""Sprint 4 sweep — 5 frontier models × 12 representative (domain, shift) cells.

Headline Paper 1 dataset. Each cell is one honest LLMAgent run scored by
:func:`mirrorlab.runners.sprint3_pilot.score_against_scenario`.

Design
------
* **Resilient**: each cell is a `try`/`except` island. A crash in one cell
  records a failure entry and the sweep continues.
* **Resumable**: results are streamed to the on-disk JSON log (one rewrite
  per completed cell). Re-running with `--resume` skips cells already
  present.
* **Provider-agnostic**: uses :func:`mirrorlab.runners.provider.make_client`
  via :class:`LLMAgent`'s `provider=` field — no hard-coded client.

Budgets (per cell): CAL-7 honest 30 tool calls, 180 s wall (task #3 spec).

Cells (4 representative domains × 3 tiers):

  | Domain   | baseline | γ-shift  | δ-shift  |
  |----------|----------|----------|----------|
  | hooke    | baseline | gamma_1_1  | delta_1_1  |
  | coulomb  | baseline | gamma_5_1  | delta_5_1  |
  | thermal  | baseline | gamma_7_1  | delta_7_1  |
  | decay    | baseline | gamma_12_1 | delta_12_1 |

Models (slots 1-5, user-confirmed):
  1. claude-opus-4.6           (anthropic, 4141)
  2. gpt-5.4-20260305          (openai,    4142/v1)
  3. gemini-3.1-pro-preview    (anthropic, 4141)
  4. claude-sonnet-4.5         (anthropic, 4141)
  5. gpt-4.1-20250414          (openai,    4142/v1)  [Sprint 4 swap: gpt-4o unrouted on proxy]

Hard cap: 2000 LLM turns. Stops the sweep mid-stride and writes a
``stopped_at_cap`` flag if exceeded by 20 % (i.e. ≥ 2400).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mirrorlab.runners.llm_agent import AgentTrace, LLMAgent
from mirrorlab.runners.sprint3_pilot import score_against_scenario
from mirrorlab.scenarios.loader import load as load_scenario

log = logging.getLogger(__name__)


# ---- Sweep matrix ------------------------------------------------------

SweepCell = Tuple[str, str, str]  # (domain_id, shift_id, tier_label)

REPRESENTATIVE_CELLS: Tuple[SweepCell, ...] = (
    ("hooke",   "baseline",    "baseline"),
    ("hooke",   "gamma_1_1",   "gamma"),
    ("hooke",   "delta_1_1",   "delta"),
    ("coulomb", "baseline",    "baseline"),
    ("coulomb", "gamma_5_1",   "gamma"),
    ("coulomb", "delta_5_1",   "delta"),
    ("thermal", "baseline",    "baseline"),
    ("thermal", "gamma_7_1",   "gamma"),
    ("thermal", "delta_7_1",   "delta"),
    ("decay",   "baseline",    "baseline"),
    ("decay",   "gamma_12_1",  "gamma"),
    ("decay",   "delta_12_1",  "delta"),
)


@dataclass(frozen=True)
class ModelSpec:
    slot: int
    model: str
    provider: str
    base_url: str
    api_key_env: Optional[str]  # None ⇒ literal `api_key_literal`
    api_key_literal: Optional[str] = None


MODEL_PANEL: Tuple[ModelSpec, ...] = (
    ModelSpec(1, "claude-opus-4.6",        "anthropic", "http://127.0.0.1:4141", None, "dummy"),
    ModelSpec(2, "gpt-5.4-20260305",       "openai",    "http://127.0.0.1:4142/v1", "MIRRORLAB_LLM_API_KEY"),
    ModelSpec(3, "gemini-3.1-pro-preview", "anthropic", "http://127.0.0.1:4141", None, "dummy"),
    ModelSpec(4, "claude-sonnet-4.5",      "anthropic", "http://127.0.0.1:4141", None, "dummy"),
    ModelSpec(5, "gpt-4.1-20250414",       "openai",    "http://127.0.0.1:4142/v1", "MIRRORLAB_LLM_API_KEY"),
)


SWEEP_HONEST_MAX_TOOL_CALLS = 30
SWEEP_HONEST_MAX_WALL = 180
SWEEP_HARD_CAP = 2000
SWEEP_HARD_CAP_OVERRUN = 2400  # 2000 × 1.2 — stop here even if cells remain


# ---- Per-cell result ---------------------------------------------------

@dataclass
class CellResult:
    model: str
    provider: str
    domain_id: str
    shift_id: str
    tier: str
    seed: int
    ok: bool
    s_scen: Optional[float]
    n_tool_calls: int
    n_llm_turns: int
    elapsed_s: float
    terminated_by: str
    submission_len: int
    submission: List[Dict[str, Any]] = field(default_factory=list)
    parse_errors: int = 0
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.s_scen is not None:
            d["s_scen"] = round(float(self.s_scen), 6)
        d["elapsed_s"] = round(float(self.elapsed_s), 4)
        return d

    @property
    def key(self) -> Tuple[str, str, str, int]:
        return (self.model, self.domain_id, self.shift_id, int(self.seed))


# ---- Sweep driver ------------------------------------------------------

def _resolve_api_key(spec: ModelSpec) -> str:
    if spec.api_key_env:
        key = os.environ.get(spec.api_key_env, "").strip()
        if not key:
            raise RuntimeError(
                f"env var {spec.api_key_env!r} is empty; export it before running the sweep"
            )
        return key
    return spec.api_key_literal or ""


def _run_one_cell(
    spec: ModelSpec,
    cell: SweepCell,
    *,
    seed: int,
    max_tool_calls: int,
    max_wall_seconds: int,
) -> CellResult:
    domain_id, shift_id, tier = cell
    api_key = _resolve_api_key(spec)
    t0 = time.monotonic()
    try:
        scenario = load_scenario(domain_id, shift_id, seed=seed)
    except Exception as exc:  # noqa: BLE001
        return CellResult(
            model=spec.model, provider=spec.provider,
            domain_id=domain_id, shift_id=shift_id, tier=tier, seed=seed,
            ok=False, s_scen=None, n_tool_calls=0, n_llm_turns=0,
            elapsed_s=time.monotonic() - t0,
            terminated_by=f"load_error:{type(exc).__name__}",
            submission_len=0, error=f"load_scenario: {exc}",
        )

    agent = LLMAgent(
        model=spec.model,
        provider=spec.provider,
        base_url=spec.base_url,
        api_key=api_key,
        max_tool_calls=max_tool_calls,
        max_wall_seconds=max_wall_seconds,
        fallback_to_stub=False,
    )

    try:
        submission, trace = agent.run_with_trace(scenario)
    except Exception as exc:  # noqa: BLE001
        return CellResult(
            model=spec.model, provider=spec.provider,
            domain_id=domain_id, shift_id=shift_id, tier=tier, seed=seed,
            ok=False, s_scen=None, n_tool_calls=0, n_llm_turns=0,
            elapsed_s=time.monotonic() - t0,
            terminated_by=f"crash:{type(exc).__name__}",
            submission_len=0, error=str(exc)[:500],
        )

    try:
        s_scen = score_against_scenario(scenario, submission)
    except Exception as exc:  # noqa: BLE001
        return CellResult(
            model=spec.model, provider=spec.provider,
            domain_id=domain_id, shift_id=shift_id, tier=tier, seed=seed,
            ok=False, s_scen=None,
            n_tool_calls=trace.tool_calls, n_llm_turns=trace.llm_turns,
            elapsed_s=time.monotonic() - t0,
            terminated_by=f"score_error:{type(exc).__name__}",
            submission_len=len(submission),
            submission=[dict(e) for e in submission[:5]],
            parse_errors=trace.parse_errors,
            error=f"score_against_scenario: {exc}",
        )

    return CellResult(
        model=spec.model, provider=spec.provider,
        domain_id=domain_id, shift_id=shift_id, tier=tier, seed=seed,
        ok=True, s_scen=float(s_scen),
        n_tool_calls=trace.tool_calls, n_llm_turns=trace.llm_turns,
        elapsed_s=time.monotonic() - t0,
        terminated_by=trace.terminated_by,
        submission_len=len(submission),
        submission=[dict(e) for e in submission[:5]],
        parse_errors=trace.parse_errors,
    )


def _load_resume(path: str) -> List[CellResult]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        blob = json.load(fh)
    entries = blob.get("entries", []) if isinstance(blob, dict) else blob
    out: List[CellResult] = []
    for e in entries:
        out.append(CellResult(
            model=e["model"], provider=e["provider"],
            domain_id=e["domain_id"], shift_id=e["shift_id"], tier=e["tier"],
            seed=int(e["seed"]),
            ok=bool(e["ok"]),
            s_scen=(None if e.get("s_scen") is None else float(e["s_scen"])),
            n_tool_calls=int(e.get("n_tool_calls", 0)),
            n_llm_turns=int(e.get("n_llm_turns", 0)),
            elapsed_s=float(e.get("elapsed_s", 0.0)),
            terminated_by=str(e.get("terminated_by", "unknown")),
            submission_len=int(e.get("submission_len", 0)),
            submission=list(e.get("submission", [])),
            parse_errors=int(e.get("parse_errors", 0)),
            error=e.get("error"),
        ))
    return out


def _dump(path: str, results: List[CellResult], meta: Dict[str, Any]) -> None:
    payload = {
        "meta": meta,
        "entries": [r.as_dict() for r in results],
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=repr)
    os.replace(tmp, path)


def run_sweep(
    *,
    out_json: str,
    cells: Sequence[SweepCell] = REPRESENTATIVE_CELLS,
    models: Sequence[ModelSpec] = MODEL_PANEL,
    seed: int = 0,
    max_tool_calls: int = SWEEP_HONEST_MAX_TOOL_CALLS,
    max_wall_seconds: int = SWEEP_HONEST_MAX_WALL,
    hard_cap: int = SWEEP_HARD_CAP,
    hard_cap_overrun: int = SWEEP_HARD_CAP_OVERRUN,
    resume: bool = False,
) -> Dict[str, Any]:
    prior = _load_resume(out_json) if resume else []
    done_keys = {r.key for r in prior}
    results: List[CellResult] = list(prior)

    total_turns = sum(r.n_llm_turns for r in results)
    n_runs_total = len(models) * len(cells)
    stopped_at_cap = False
    t_start = time.monotonic()

    meta = {
        "schema_version": 1,
        "n_models": len(models),
        "n_cells": len(cells),
        "n_runs_planned": n_runs_total,
        "seed": seed,
        "hard_cap": hard_cap,
        "hard_cap_overrun": hard_cap_overrun,
        "max_tool_calls": max_tool_calls,
        "max_wall_seconds": max_wall_seconds,
        "stopped_at_cap": stopped_at_cap,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    _dump(out_json, results, meta)

    for spec in models:
        for cell in cells:
            key = (spec.model, cell[0], cell[1], int(seed))
            if key in done_keys:
                log.info("SKIP (resume) %s / %s / %s", *key[:3])
                continue
            if total_turns >= hard_cap_overrun:
                stopped_at_cap = True
                log.error("HARD CAP OVERRUN at %d turns — stopping sweep", total_turns)
                break
            log.info("RUN  model=%s domain=%s shift=%s seed=%d (turns so far=%d)",
                     spec.model, cell[0], cell[1], seed, total_turns)
            res = _run_one_cell(
                spec, cell,
                seed=seed,
                max_tool_calls=max_tool_calls,
                max_wall_seconds=max_wall_seconds,
            )
            results.append(res)
            total_turns += res.n_llm_turns
            meta["stopped_at_cap"] = stopped_at_cap
            meta["n_turns_so_far"] = total_turns
            meta["n_completed"] = len(results)
            _dump(out_json, results, meta)
            log.info("  → ok=%s S=%s turns=%d term=%s",
                     res.ok, res.s_scen, res.n_llm_turns, res.terminated_by)
        if stopped_at_cap:
            break

    meta["stopped_at_cap"] = stopped_at_cap
    meta["n_turns_total"] = total_turns
    meta["n_completed"] = len(results)
    meta["elapsed_s"] = round(time.monotonic() - t_start, 3)
    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    _dump(out_json, results, meta)
    return {"meta": meta, "results": results}


# ---- Summary ----------------------------------------------------------

def write_summary_md(
    results: List[CellResult],
    out_md: str,
    *,
    models: Sequence[ModelSpec] = MODEL_PANEL,
    cells: Sequence[SweepCell] = REPRESENTATIVE_CELLS,
) -> None:
    """5 × 12 score matrix + per-model aggregates by tier."""
    by_key = {(r.model, r.domain_id, r.shift_id): r for r in results}

    lines: List[str] = []
    lines.append("# Sprint 4 Sweep — 5 models × 12 representative cells\n")
    lines.append(f"_Generated {time.strftime('%Y-%m-%dT%H:%M:%S%z')}; "
                 f"{len(results)} entries._\n")

    # Score matrix
    header = "| Model | " + " | ".join(f"{c[0]}/{c[1]}" for c in cells) + " |"
    sep = "|---|" + "---|" * len(cells)
    lines.append("\n## Score matrix (S_scen)\n")
    lines.append(header)
    lines.append(sep)
    for spec in models:
        row = [spec.model]
        for c in cells:
            r = by_key.get((spec.model, c[0], c[1]))
            if r is None:
                row.append("—")
            elif not r.ok or r.s_scen is None:
                row.append(f"FAIL ({r.terminated_by})")
            else:
                row.append(f"{r.s_scen:.3f}")
        lines.append("| " + " | ".join(row) + " |")

    # Per-model tier aggregates
    lines.append("\n## Per-model aggregates by tier\n")
    lines.append("| Model | baseline (mean) | γ (mean) | δ (mean) | overall | n_ok | n_fail |")
    lines.append("|---|---|---|---|---|---|---|")
    for spec in models:
        by_tier: Dict[str, List[float]] = {"baseline": [], "gamma": [], "delta": []}
        n_ok = n_fail = 0
        all_scores: List[float] = []
        for c in cells:
            r = by_key.get((spec.model, c[0], c[1]))
            if r is None or not r.ok or r.s_scen is None:
                n_fail += 1
                continue
            n_ok += 1
            by_tier[c[2]].append(float(r.s_scen))
            all_scores.append(float(r.s_scen))

        def mean(xs: List[float]) -> str:
            return f"{sum(xs)/len(xs):.3f}" if xs else "—"

        lines.append(
            f"| {spec.model} | {mean(by_tier['baseline'])} | "
            f"{mean(by_tier['gamma'])} | {mean(by_tier['delta'])} | "
            f"{mean(all_scores)} | {n_ok} | {n_fail} |"
        )

    # Footnotes
    total_turns = sum(r.n_llm_turns for r in results)
    lines.append(f"\n_Total LLM turns: **{total_turns}** "
                 f"(cap {SWEEP_HARD_CAP}, overrun-stop {SWEEP_HARD_CAP_OVERRUN})._\n")

    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ---- CLI --------------------------------------------------------------

def _parse_cells(arg: Optional[str]) -> List[SweepCell]:
    if not arg:
        return list(REPRESENTATIVE_CELLS)
    out: List[SweepCell] = []
    by_id = {(c[0], c[1]): c for c in REPRESENTATIVE_CELLS}
    for token in arg.split(","):
        token = token.strip()
        if not token:
            continue
        if "/" not in token:
            raise SystemExit(f"--cells token {token!r} must be 'domain/shift'")
        dom, shift = token.split("/", 1)
        if (dom, shift) not in by_id:
            raise SystemExit(f"unknown cell {token!r}; not in REPRESENTATIVE_CELLS")
        out.append(by_id[(dom, shift)])
    return out


def _parse_models(arg: Optional[str]) -> List[ModelSpec]:
    if not arg:
        return list(MODEL_PANEL)
    wanted = [t.strip() for t in arg.split(",") if t.strip()]
    by_model = {m.model: m for m in MODEL_PANEL}
    by_slot = {str(m.slot): m for m in MODEL_PANEL}
    out: List[ModelSpec] = []
    for tok in wanted:
        if tok in by_model:
            out.append(by_model[tok])
        elif tok in by_slot:
            out.append(by_slot[tok])
        else:
            raise SystemExit(f"unknown model {tok!r}; supported: "
                             f"{list(by_model)} or slots {list(by_slot)}")
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sprint4_sweep")
    parser.add_argument("--out-json",
                        default="docs/sprint4-sweep-data.json")
    parser.add_argument("--out-md",
                        default="docs/sprint4-sweep-summary.md")
    parser.add_argument("--cells", default=None,
                        help="comma-separated domain/shift filter")
    parser.add_argument("--models", default=None,
                        help="comma-separated model id or slot filter")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-tool-calls", type=int,
                        default=SWEEP_HONEST_MAX_TOOL_CALLS)
    parser.add_argument("--max-wall-seconds", type=int,
                        default=SWEEP_HONEST_MAX_WALL)
    parser.add_argument("--hard-cap", type=int, default=SWEEP_HARD_CAP)
    parser.add_argument("--hard-cap-overrun", type=int,
                        default=SWEEP_HARD_CAP_OVERRUN)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--summary-only", action="store_true",
                        help="regenerate --out-md from existing --out-json; no LLM calls")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    cells = _parse_cells(args.cells)
    models = _parse_models(args.models)

    if args.summary_only:
        prior = _load_resume(args.out_json)
        write_summary_md(prior, args.out_md, models=models, cells=cells)
        print(f"summary regenerated: {args.out_md}", file=sys.stderr)
        return 0

    out = run_sweep(
        out_json=args.out_json,
        cells=cells,
        models=models,
        seed=args.seed,
        max_tool_calls=args.max_tool_calls,
        max_wall_seconds=args.max_wall_seconds,
        hard_cap=args.hard_cap,
        hard_cap_overrun=args.hard_cap_overrun,
        resume=args.resume,
    )
    write_summary_md(out["results"], args.out_md, models=models, cells=cells)

    meta = out["meta"]
    n_ok = sum(1 for r in out["results"] if r.ok)
    n_fail = sum(1 for r in out["results"] if not r.ok)
    print(
        f"\n=== sprint4 sweep done ===\n"
        f"  cells planned          = {meta['n_runs_planned']}\n"
        f"  cells completed        = {meta['n_completed']}\n"
        f"  ok / fail              = {n_ok} / {n_fail}\n"
        f"  total LLM turns        = {meta.get('n_turns_total', 0)} "
        f"(cap {meta['hard_cap']}, overrun-stop {meta['hard_cap_overrun']})\n"
        f"  stopped_at_cap         = {meta.get('stopped_at_cap', False)}\n"
        f"  json                   = {args.out_json}\n"
        f"  summary                = {args.out_md}",
        file=sys.stderr,
    )
    return 0 if not meta.get("stopped_at_cap") else 2


__all__ = [
    "REPRESENTATIVE_CELLS",
    "MODEL_PANEL",
    "ModelSpec",
    "CellResult",
    "SWEEP_HONEST_MAX_TOOL_CALLS",
    "SWEEP_HONEST_MAX_WALL",
    "SWEEP_HARD_CAP",
    "SWEEP_HARD_CAP_OVERRUN",
    "run_sweep",
    "write_summary_md",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())
