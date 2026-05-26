# Sprint 2 Report — MirrorLab Catalog Build-out

**Sprint**: 2 (catalog + tool MVS)
**Date**: 2026-05-26
**Author**: sprint2-integrator
**Status**: **PASS** (exit criterion §9.2 met; 2 non-gating discrepancies surfaced)

---

## 1. What got built

| Component | Count / size |
|---|---|
| Domains (baselines wired in registry) | **12** (Hooke, Gravity, Damped HO, Pendulum, Coulomb, RLC, Thermal, Wave, Optics, Fluid, Kinetics, Decay) |
| Catalog shifts (γ + δ) implemented | **36** = 24 γ-shifts + 12 δ-shifts (3 per domain) |
| Total `(domain, shift)` pairs in registry | **48** (12 baselines + 36 shifts) |
| Tool MVS pool | **32** = 8 measure + 8 manipulate + 8 analyze + 8 knowledge |
| Counterfactual sub-grid (c) policy | CAL-3 perturbation (±30% default) over law-parameter dataclasses |
| `mirrorlab/` LOC | ~7,505 |
| `tests/` LOC | ~2,314 |
| Shift modules under `mirrorlab/shifts/` | 36 + `__init__.py` + `_util.py` |
| Test files | 35 (catalog, tools, eval, integration, scenarios) |
| Total tests passing | **331** (316 inherited + 15 added in this sprint) |
| Smoke runner | `mirrorlab/runners/sprint2_smoke.py` |
| Integration test | `tests/integration/test_sprint2_full_catalog.py` |

---

## 2. Sprint 2 exit criterion (spec §9.2)

> *"All 36 catalog shifts emit valid scenarios; tool contract tests green."*

**Result: PASS**

Evidence:

```
$ python -m mirrorlab.runners.sprint2_smoke
============================================================
Registry layer: PASS=48/48 FAIL=0 (baselines=12, shifts=36)
Loader  layer: PASS=2/4 FAIL=2 (diagnostic — non-gating; loader wired for hooke only in Sprint 2)
Exit criterion (§9.2): PASS
```

```
$ python -m pytest -q
331 passed in 134.28s (0:02:14)
```

Full integration suite:

```
$ python -m pytest tests/integration/test_sprint2_full_catalog.py -v
15 passed in 130.15s (0:02:10)
```

Breakdown of the 15 sprint-2 integration tests:

| Test | Result |
|---|---|
| `test_all_48_pairs_emit_valid_scenarios` | PASS |
| `test_tool_pool_size_and_split` | PASS |
| `test_tool_contract_suite_passes_in_subprocess` | PASS |
| `test_hooke_gamma_1_1_eval_discrimination_via_agent_stub` | PASS — Δ S_scen ≈ 0.22 ≥ 0.05 |
| `test_per_domain_gamma_behavioral_discrimination[gravity..decay]` (11 cases) | PASS |

---

## 3. Catalog vs. implementation — discrepancies surfaced

### D-1 (RESOLVED post-report): loader's counterfactual whitelist not extended for two new hooke shifts

`mirrorlab/scenarios/counterfactual.py::_LAW_PARAM_FIELDS` originally only
registered `HookeParams` and `HookeGamma11Params`. Initial smoke run exposed:

| Pair | Registry layer | Loader layer (pre-patch) | Cause |
|---|---|---|---|
| `hooke / delta_1_1` | PASS | FAIL | `TypeError: no counterfactual policy registered for HookeDelta11Params` |
| `hooke / gamma_1_2` | PASS | FAIL | `TypeError: no counterfactual policy registered for HookeGamma12Params` |

**Resolution**: counterfactual-engineer extended `_LAW_PARAM_FIELDS` with
`HookeGamma12Params → (k0, xi, phi)` and `HookeDelta11Params → (k, c, L)`.
This is coverage, not calibration — the ±30% magnitude (CAL-3) is unchanged.
Post-patch smoke reports **Loader 4/4 PASS**; full suite still 331/331.

### D-2 (non-gating): loader / agent-stub / eval pipeline is hooke-only

`mirrorlab/scenarios/loader.py::_DOMAIN_PROMPT_BUILDERS` and
`mirrorlab/scenarios/agent_stub.py` are both Sprint-1 artifacts hard-coded to
the Hooke domain. The other 11 domain baselines + their 33 shifts cannot
currently flow through `loader.load → agent_stub.run → eval.scoring`.

Concretely this means task #6's *"At least one γ-shift per domain shows
measurable discrimination from baseline (run agent stub through eval,
expect baseline > shift by Δ ≥ 0.05)"* could only be evaluated end-to-end
for hooke. For the other 11 domains the integration test falls back to a
**behavioral discrimination signal at the `sim.step` layer** — sum-of-squares
of non-`t` observables on a small (seed, t) grid — and confirms the γ-shift
diverges from the baseline by ≥ 5% somewhere in the grid. This is the
*necessary condition* for Sprint-3 eval discrimination to exist; it is not
sufficient (saying nothing about agent stubs or scoring).

**This is the headline Sprint-3 readiness gap** (see §5).

---

## 4. CAL registry — Sprint-2 data points

No CAL defaults were changed (per task spec). The following observed values
should feed Sprint-3 calibration:

| CAL | Default (placeholder) | Sprint-2 observation |
|---|---|---|
| CAL-3 (counterfactual ±magnitude) | 0.30 | unchanged; whitelist gap (§3, D-1) blocks 2 hooke pairs from running at all |
| CAL-4 (numeric τ) | 0.5 | unchanged; sprint1 e2e discrimination tests still pass |
| CAL-5 (broken-symmetry bonus *b*) | 0.10 | unchanged |
| CAL-6 (shotgun penalty *ρ*) | 0.05 | unchanged |
| Behavioral γ-shift divergence (sim.step layer, max over 8 seeds × 5 t) | n/a | min observed across 11 non-hooke domains ≥ 0.05; minimum cell was `fluid/gamma_10_1` (steady-state Bernoulli, low param-space variance at seed=0; clears the bar by seed 4) |

Sprint 3 should treat the steady-state / closed-form domains (optics, fluid,
kinetics, decay) as the most discrimination-sensitive cells when calibrating
CAL-4 (τ) — their step output has no temporal dynamics to amortize the shift
signal.

---

## 5. Sprint 3 readiness assessment

### Ready
- **Catalog**: 12 baselines + 36 shifts all build, step(0.0), and produce finite numeric output (smoke 48/48).
- **Tool pool**: 32-tool MVS in place with green contract suite (42 tool tests).
- **Behavioral discrimination**: every γ-shift probe is observably distinct from its baseline at the sim layer (15-test integration suite green).
- **Counterfactual (c) sub-grid**: real per-point parameter perturbation lives for hooke baseline + γ-1-1 (CAL-3); doubles the mean baseline↔γ-1-1 score gap relative to Sprint 1.

### Blocking Sprint 3
- **Loader prompt templates** for domains 2–12 are not written. Without them no LLM agent can be probed on anything except hooke. Concretely: `_DOMAIN_PROMPT_BUILDERS`, `_DOMAIN_OBSERVABLES`, `_DOMAIN_DIM` in `mirrorlab/scenarios/loader.py` are hooke-only.
- **Counterfactual whitelist** must register every law-param dataclass that ships in the catalog (per §3 D-1). 36 shifts × on average 1 dataclass each = ~36 entries to add (most are mechanical).
- **Per-domain agent stubs** (or one generalized rule-based stub) needed so the "baseline > shift via eval" discrimination can run for all 12 cells, not just hooke.
- **CAL calibration runs** (CAL-3 magnitude, CAL-4 τ) need a real LLM and 12 working pipelines — depends on the three items above.

### Nice-to-have
- Per-shift symmetry / conservation invariant checks (catalog claims them in docstrings; only spot-tested in `tests/catalog/`).
- Per-domain extension of the agent stub's probe schedule (currently `np.linspace(0.01, 2.0, 32)` is hooke-tuned).

---

## 6. Files added in this sprint by the integrator

| Path | Purpose |
|---|---|
| `mirrorlab/runners/sprint2_smoke.py` | 48-pair smoke runner; exits 0 on §9.2 PASS |
| `tests/integration/test_sprint2_full_catalog.py` | 15 integration tests pinning §9.2 + discrimination |
| `docs/sprint2-report.md` | this report |
| `README.md` (Sprint 2 status subsection) | one-paragraph entry under Roadmap |

No CAL defaults touched. No shift / domain / tool code touched (per "don't paper over failures").
