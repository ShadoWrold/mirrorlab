# Sprint 4 Sweep — 5 models × 12 representative cells

_Generated 2026-05-26T12:38:42+0000; 60 entries._

> **Model swap (2026-05-26, proxy-checker / task #8)**: `gpt-4o` returned 12/12 `llm_error` because the local proxy at `127.0.0.1:4142` has no healthy deployments for that model id (`litellm.BadRequestError: There are no healthy deployments for this model. Received Model Group=gpt-4o`). Replaced with **`gpt-4.1-20250414`** (already in proxy `/v1/models`); re-ran only those 12 cells (286 LLM turns) and merged into `docs/sprint4-sweep-data-merged.json`. The 0.000 scores in the matrix below are the pre-fix view — see scoring-fixer (#7) rescored output for true scores.


## Score matrix (S_scen)

| Model | hooke/baseline | hooke/gamma_1_1 | hooke/delta_1_1 | coulomb/baseline | coulomb/gamma_5_1 | coulomb/delta_5_1 | thermal/baseline | thermal/gamma_7_1 | thermal/delta_7_1 | decay/baseline | decay/gamma_12_1 | decay/delta_12_1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-4.6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| gpt-5.4-20260305 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| gemini-3.1-pro-preview | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| claude-sonnet-4.5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| gpt-4o | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Per-model aggregates by tier

| Model | baseline (mean) | γ (mean) | δ (mean) | overall | n_ok | n_fail |
|---|---|---|---|---|---|---|
| claude-opus-4.6 | 0.000 | 0.000 | 0.000 | 0.000 | 12 | 0 |
| gpt-5.4-20260305 | 0.000 | 0.000 | 0.000 | 0.000 | 12 | 0 |
| gemini-3.1-pro-preview | 0.000 | 0.000 | 0.000 | 0.000 | 12 | 0 |
| claude-sonnet-4.5 | 0.000 | 0.000 | 0.000 | 0.000 | 12 | 0 |
| gpt-4o | 0.000 | 0.000 | 0.000 | 0.000 | 12 | 0 |

_Total LLM turns: **877** (cap 2000, overrun-stop 2400). Elapsed: 4027 s (~67 min)._

## Diagnostic notes

**Every cell scored S_scen = 0.0**, but the failure modes differ by model. This is
not a sweep crash — all 60 runs completed `ok=true`. The breakdown of
`terminated_by` across the 60 runs is:

| terminated_by | count | meaning |
|---|---|---|
| `submit`      | 28 | LLM called `submit_answer` (delivered a candidate law) |
| `budget`      | 19 | LLM hit the 30 tool-call cap before calling `submit_answer` |
| `llm_error`   | 12 | client-side LLM call raised (all 12 are gpt-4o; proxy on :4142 likely does not host that model id) |
| `wall`        | 1  | 180 s wall-clock exceeded |

Per-model submission rates:

| Model | submitted | budget | llm_error | wall |
|---|---|---|---|---|
| claude-opus-4.6        | 3  | 9 | 0  | 0 |
| claude-sonnet-4.5      | 4  | 8 | 0  | 0 |
| gemini-3.1-pro-preview | 9  | 2 | 0  | 1 |
| gpt-5.4-20260305       | 12 | 0 | 0  | 0 |
| gpt-4o                 | 0  | 0 | 12 | 0 |

**Why S_scen = 0.0 for the 28 cells that submitted** — inspection of submission
payloads (see `sprint4-sweep-data.json`) shows the models name the right law
(e.g. claude-opus-4.6 on `coulomb/gamma_5_1` submits `F = k*q1*q2/r^2` with
`def f(q1, q2, r, k=...):` and the correct Coulomb constant), but the input
keys of their predictor (`q1`, `q2`, `r`) do not match the test grid's input
vocabulary that `mirrorlab.eval.scoring.score_submission` uses to evaluate the
predictor. The ceiling oracle (Task #2) avoids this by constructing its
predictor from the loader's grid signature directly.

**Open question for #4 / #5** — is this:

  (a) A scoring/signature-binding gap to be fixed before final paper data (in
      which case re-run #3 on the same JSON via `--resume` once binding is
      relaxed), or
  (b) A genuine Paper 1 finding ("frontier models name the law but cannot
      lock to the harness's input vocabulary") to be written up as-is.

The gpt-4o `llm_error` row is independently suspicious — the OpenAI proxy at
:4142 is likely not configured to route `gpt-4o`; team-lead may want to
swap that slot or have the proxy maintainer add the model.

