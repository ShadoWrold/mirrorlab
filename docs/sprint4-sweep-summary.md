# Sprint 4 Sweep — 5 models × 12 representative cells

_Generated 2026-06-17T11:05:49+0000; 36 entries._


## Score matrix (S_scen)

| Model | hooke/baseline | hooke/gamma_1_1 | hooke/delta_1_1 | coulomb/baseline | coulomb/gamma_5_1 | coulomb/delta_5_1 | thermal/baseline | thermal/gamma_7_1 | thermal/delta_7_1 | decay/baseline | decay/gamma_12_1 | decay/delta_12_1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.5 | 0.970 | 0.000 | 0.950 | 0.894 | 0.000 | 0.000 | 0.932 | 0.000 | 0.000 | 0.942 | 0.000 | 0.941 |
| gpt-5.4-20260305 | 0.970 | 0.725 | 0.950 | 0.950 | 0.000 | 0.000 | 0.932 | 0.736 | 0.000 | 0.942 | 0.464 | 0.000 |
| gemini-3.1-pro-preview | 0.970 | 0.000 | FAIL (score_error:SyntaxError) | 1.000 | 0.000 | 0.000 | 0.932 | 0.030 | 0.000 | 0.000 | 0.706 | 0.000 |

## Per-model aggregates by tier

| Model | baseline (mean) | γ (mean) | δ (mean) | overall | n_ok | n_fail |
|---|---|---|---|---|---|---|
| gpt-5.5 | 0.935 | 0.000 | 0.473 | 0.469 | 12 | 0 |
| gpt-5.4-20260305 | 0.949 | 0.481 | 0.238 | 0.556 | 12 | 0 |
| gemini-3.1-pro-preview | 0.725 | 0.184 | 0.000 | 0.331 | 11 | 1 |

_Total LLM turns: **459** (cap 2000, overrun-stop 2400)._

