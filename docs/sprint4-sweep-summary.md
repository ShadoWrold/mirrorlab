# Sprint 4 Sweep — 5 models × 12 representative cells

_Generated 2026-06-18T02:32:08+0000; 144 entries._


## Score matrix (S_scen)

| Model | hooke/baseline | hooke/gamma_1_1 | hooke/delta_1_1 | coulomb/baseline | coulomb/gamma_5_1 | coulomb/delta_5_1 | thermal/baseline | thermal/gamma_7_1 | thermal/delta_7_1 | decay/baseline | decay/gamma_12_1 | decay/delta_12_1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.5 | 0.987 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.929 | 0.722 | 0.000 | 0.934 | 0.000 | 0.102 |
| gpt-5.4-20260305 | 0.987 | 0.039 | 0.000 | 0.950 | 0.000 | 0.000 | 0.929 | 0.446 | 0.000 | 0.934 | 0.950 | 0.102 |
| gemini-3.1-pro-preview | 0.986 | 0.000 | 0.934 | 0.000 | 0.000 | 0.000 | 0.929 | 0.717 | 0.000 | 0.934 | 0.000 | 0.000 |
| claude-opus-4.8 | 0.937 | 0.000 | 0.934 | 0.000 | 0.000 | 0.000 | 0.929 | 0.717 | 0.000 | 0.934 | 0.000 | 0.936 |

## Per-model aggregates by tier

| Model | baseline (mean) | γ (mean) | δ (mean) | overall | n_ok | n_fail |
|---|---|---|---|---|---|---|
| gpt-5.5 | 0.962 | 0.180 | 0.026 | 0.389 | 12 | 0 |
| gpt-5.4-20260305 | 0.950 | 0.359 | 0.026 | 0.445 | 12 | 0 |
| gemini-3.1-pro-preview | 0.712 | 0.179 | 0.233 | 0.375 | 12 | 0 |
| claude-opus-4.8 | 0.700 | 0.179 | 0.467 | 0.449 | 12 | 0 |

_Total LLM turns: **1902** (cap 2000, overrun-stop 2400)._

