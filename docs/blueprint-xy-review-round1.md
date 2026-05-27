# Blueprint X+Y — Round 1 Audit

**Auditor**: auditor-round1 (mirrorlab-blueprint team)
**Date**: 2026-05-27
**Target**: `docs/blueprint-xy.md` v1 (commit working tree)
**Approach**: adversarial — find holes, do not validate.

---

## §1 Verdict

**REVISE** (not BLOCK; not SHIP).

The blueprint is well-structured and the X+Y direction is correct. P0 (γ-2-1) is a sound proof-of-concept and §5 DAG ordering is defensible. However six issues must be addressed before v2 can be executed by sub-agents: three are factually wrong about the codebase (§2.1–§2.3 of this review), two are load-bearing §9 questions that the auditor cannot answer for the author (§2.4–§2.5), and one is an under-specified evaluator branch (§2.6). None of them invalidate the overall plan; all are fixable in v2 without architectural changes.

---

## §2 Critical issues (must fix before next round)

### 2.1 §4 matrix is wrong about 5 (actually 6) shifts having an exported `shifted_*` callable

The author flagged kinetics δ-11-1, decay γ-12-1, decay δ-12-1, optics δ-9-1, wave δ-8-1 as unread (§4 footer + §9 Q3). I verified each module — confirmed: **none** of them export any `shifted_*` function. They export only `sampler`, `validator`, `build`, an `Instance` class, and `Instance.step(t)`.

Evidence:
- `mirrorlab/shifts/kinetics_d_11_1.py` — only `__init__`, `params`, `_integrate`, `step`, `sampler`, `validator`, `build`.
- `mirrorlab/shifts/wave_d_8_1.py:51-68` — `_integrate` + `step` only; no closed form.
- `mirrorlab/shifts/optics_d_9_1.py:45` — `step` only.
- `mirrorlab/shifts/decay_g_12_1.py:50-65` — `_integrate` + `step` only.
- `mirrorlab/shifts/decay_d_12_1.py:44` — `step` only.

**Bonus finding the blueprint missed**: `mirrorlab/shifts/kinetics_g_11_2.py` (row 32 in §4) also has **no** `shifted_*` or `_step_*` export. The author lists row 32 as "similar; inspect" but did not flag it in §9 Q3. So Q3 covers 5 modules; reality is 6.

Consequence: §4 rows 24, 27, 32, 33, 34, 36 cannot follow the "call `shifted_*(...)` from the builder" template. Either (a) the builder runs `Instance(...).step(t)` per grid point (slow, and `step` returns a *dict of observables* — the builder still has to pick a scalar projection), or (b) the maintainers add `shifted_*` closed forms to those 6 modules first. Neither path is in §3.

**Required fix in v2**: §3.2 must add a new sub-section "step()-only shifts" naming these 6 cells and committing to one of (a)/(b). §4 rows 24/27/32/33/34/36 must list the observable projection chosen. Until then the 6 cells cannot be implemented by a sub-agent from the blueprint alone (fails §E executability test).

### 2.2 §9 Q2 (ROT GT projection) is load-bearing for P0 and must be answered before T3

§4 row 4 (γ-2-1) says "GT = signed projection onto r̂" but §9 Q2 lists three competing options and explicitly defers the choice to the auditor. The auditor cannot make this choice without buy-in from the author and the consensus-lead, because:

- Option (a) signed-|F| along r̂: this is what `blocker-physics.md` analyses assume. Recommended.
- Option (b) one component Fx: collapses anisotropy on rotated configurations — defeats X.B.
- Option (c) magnitude |F|: loses sign; on coulomb (attractive vs repulsive) it makes sub-grid (c) cliff strictly shallower.

P0 gate (§8.1) depends on this choice because it sets the ceiling-vs-baseline spread. **My recommendation: lock (a), and rename §4 to "signed projection of F onto query r̂ = (x,y,z)/‖(x,y,z)‖"**, and apply the same convention to coulomb γ-5-1/2, thermal γ-7-1 (flux vector·n̂), fluid γ-10-2, wave γ-8-2 (k·r phase already scalar — n/a). v2 must inline this.

### 2.3 §2.3 predictor signature: walkthrough exposes two unstated requirements

Walking through one concrete (c) call for `entry["predictor"]["code"] = "def f(r, G, M, m): return -G*M*m/(r*r)"` on γ-2-1 (which after X.B emits grid keys `{x,y,z}`):

1. `_entry_predictor_raw(entry)` would `exec(pred["code"], ns)` → bare `f` callable. Blueprint §2.3 implies this works, but does NOT specify how `_predictor_signature(f)` filtering applies to the raw form. The current `_entry_predictor` returns a `bound` wrapper that filters kwargs against `allowed` (numeric.py:117-123). The blueprint's `_eval_subgrid_c` sketch (lines 109-116) calls `_safe_call(raw_predictor, kwargs)` directly without showing that signature filtering still happens. **v2 must clarify**: either `_safe_call` is enhanced to do the filtering itself, or `_entry_predictor_raw` returns a filtered wrapper (analogous to `bound` but without the closure).

2. For the example predictor with signature `def f(r, G, M, m)` (no `**_`), `allowed = {r, G, M, m}`. The grid emits `ins = {"x": 1.0, "y": 2.0, "z": 3.0}`. `_alias_inputs(ins, canonical_order=("x","y","z"), entry_inputs=[{"name":"r"}])` calls `zip(canonical_order, entry_inputs)` (numeric.py:145) — zip stops at min length, so **only `x → r` is aliased and `y, z` are dropped silently**. Then `kwargs = {**declared, **cf_overrides, "r": 1.0}` — `r` is set to the x-value, not √(x²+y²+z²). This is actually the intended X.B failure mode (baseline-form submission scoring badly because it can't see y, z), so it works. But the blueprint never says so. **v2 must add an explicit paragraph**: "Baseline-form submissions whose `inputs` declare fewer names than `canonical_inputs` will only receive the first N grid keys (positional). This is by design — that's how X.B exposes them."

3. The `**declared_params` → `**cf_overrides` → `**_alias_inputs(ins,...)` merge order in §2.3 line 112 puts inputs last, so cf-overridden coefficients win over declared but lose to input keys. Correct, but: **what if `_params_to_predictor_kwargs(cf_p)` emits a key whose name collides with an input name?** e.g. `m` (mass) is both a law coefficient field and could be declared as an input by some LLM. Input wins (probably wrong — cf override should win for coefficient fields). Edge case but should be documented.

### 2.4 §9 Q8 (input-encoded-in-params vs law-coefficient split) is load-bearing for ALL P1 thermal/fluid/optics rows

Thermal γ-7-1 (P1, §4 row 19) uses `shifted_flux_magnitude(params)` — inputs encoded as params. The builder mutates `params.T_hot`, `params.T_cold`, `params.L`, `params.grad_dir` per grid point. On sub-grid (c), cf_params *also* mutates the same params object. Without an explicit rule about which fields are "input-encoding" (free for builder) vs "law-coefficient" (only cf_params), the two will silently conflict and (c) will either (i) leak builder-side input values into cf overrides or (ii) leak cf-side coefficient values into the input encoding.

`counterfactual._LAW_PARAM_FIELDS` (counterfactual.py:87+) already names the law-coefficient fields. **v2 must state the invariant**: "builder may mutate any field NOT in `_LAW_PARAM_FIELDS[type(params)]`; cf_params mutates only fields IN that set". Add a test enforcing the disjointness. This affects thermal γ-7-1/γ-7-2/δ-7-1, fluid γ-10-1/γ-10-2/δ-10-1, optics γ-9-1/γ-9-2/δ-9-1 — 9 of the 13 P1 cells.

### 2.5 §9 Q10 (param-name canonicalization) is load-bearing for RLC γ-6-2 and coulomb γ-5-1/2

The blueprint's example `G0 → G` and `lam0 → lam` is fine for single-coefficient laws. But RLC γ-6-2 has `L0, L1, L2, M01, M02, M12` (coupled inductors); coulomb γ-5-1/2 has `q_src, q_test` or `src1_q, src2_q, test_q`. LLM submissions tend to write `def f(q1, q2, ...)` — the mapping `q_src → q1, q_test → q2` is a *choice*, not a derivation. **v2 must pin a rule** (suggestion: "lowercase the field name; preserve numeric suffix; drop `_e/_src/_test` modifiers"), and the rule must round-trip for every type in `_LAW_PARAM_FIELDS`. Without it, T14 (counterfactual.py P1 entries) cannot be assigned to a sub-agent.

### 2.6 §3.5 ceiling_agent fallback is logically inverted

§3.5 says "the `except Exception` clause should NOT silently default to baseline; it should log via `warnings.warn(...)` and return CLAMP." Good — but the current `ceiling_agent.py` flow already returns CLAMP via `_safe_call`; the *real* problem (per `blocker-trace.md`) is that the wrapper's signature-filter silently drops kwargs the predictor doesn't list, masking the bug. **v2 must add**: "log the kwargs that were filtered out, at WARN level, the first time per (cell, seed)" — otherwise the new builders' 3-D/t-bearing inputs will be filtered into oblivion and look like a numeric problem, not a signature problem.

---

## §3 Suggestions (would improve, not blocking)

- **§5 DAG**: T2 (eval/numeric subgrid-c branch) currently depends on T1 (loader_shifts scaffold). It need not: subgrid-c branch can be unit-tested against a synthetic 3-tuple grid before any loader code lands. Recommend swapping T1 ↔ T2 so Y plumbing ships first, fully decoupled. The author already states the intent ("Y plumbing lands in T2 — earlier than X") but the DAG arrow makes T2 still depend on T1.

- **§6.5 test count**: "~370 new tests" and a wall-clock of zero is implausible if 290 of them are loader snapshots that call `solve_ivp` (thermal δ-7-1, kinetics γ/δ-11-*, decay γ/δ-12-*, wave δ-8-1, optics δ-9-1). Recommend a per-cell budget estimate; if the snapshot pytest run exceeds 5 min wall-clock it will break the inner loop for sub-agents.

- **§7.2 cache invalidation**: `git mv docs/sprint*-*.json` to `docs/archive/pre-xy/` does not protect against rerun-in-place if a sub-agent re-creates a file at the old path. Add a one-line `pre-xy/.gitkeep` and a CI check or pre-commit hook flagging any `docs/sprint*-data*.json` that lacks `"xy_version": 1`.

- **§8.1 P0 gate**: "ceiling - baseline ≥ 0.10" is the only quantitative bound. Add a third assertion: "ceiling submission re-scored on the OLD (pre-XY) test grids reproduces sprint-3.5's published ceiling (≥ 0.95 on γ-2-1)" — proves no regression in the legacy pathway before throwing it away.

- **§9 Q1 (CAL-5 bonus)**: deferrable, not load-bearing. Author should pick (b) reduce-to-0.05 themselves and move on; this is a paper-1 ablation story choice, not a blocker for code.

- **§3.7 agent_stub**: the "rule-based baseline must emit a predictor with 3-D signature on ROT shifts" is fine, but **add a fixture test** that the stub's emitted code parses, evaluates, and has the declared kwargs. Otherwise a typo in stub generation silently makes ALL baseline numbers wrong (recapitulating the sprint4 `q1,q2,r` bug exactly).

- **Reader pointer**: §1 says "self-contained for a fresh AI session that has read HANDOVER.md" but the §4 matrix legend assumes the reader has internalised `blocker-fix-options.md` §1.5 ("⟨μ²⟩ = 1/3 zero-mean angular average" — never explained here). v2 should add a one-line gloss when first using it.

---

## §4 Detailed findings (one bullet per audit checklist item)

### A. Completeness

- **loader.py `_<domain>_test_grids` coverage**: §3.1 names hooke at L127-146 explicitly and "L223-505 (all `_X_test_grids`) DELETE" — covers all 12 domains by range. OK.
- **ceiling_agent.py `_<domain>_pred` coverage**: §3.5 says "Rewrite each `_<domain>_pred(scenario)`" without enumerating the 12. Cross-checked: ceiling_agent.py L98-367 holds all 12. OK but enumeration would help sub-agent assignment.
- **36 shift modules in §4**: all 36 present (rows 1-36). OK.
- **Tests broken by truth-form GT**: §3.4 mentions "tests under tests/scenarios/test_loader_*.py that assert exact GT == baseline formula are rewritten (∼25 cases)". I did not enumerate those files myself — the count "~25" is unaudited; v2 should give file paths.

### B. Correctness — three shifts sampled

- **Row 4 (gravity γ-2-1)**: `gravity_g_2_1.py:44` exports `shifted_force(pos: Tuple[float,float,float], params) -> tuple` — sig matches §4. ROT-break in (x,y,z), new keys {x,y,z} discriminate. Sampling concern (biased direction) is real per `blocker-fix-options.md` §1.5. OK.
- **Row 19 (thermal γ-7-1)**: `thermal_g_7_1.py:43` exports `shifted_flux_magnitude(params: ThermalGamma71Params) -> float` — sig matches §4 ("uses params"). Builder must `replace(sim.params, T_hot=..., grad_dir=...)`. Sampling concern (biased grad_dir) is real (the -0.44 case from `blocker-physics.md`). OK — but see §2.4 above about disjointness with cf_params.
- **Row 35 (decay γ-12-2)**: `decay_g_12_2.py:35` exports `_integrated_rate(t, params) -> float`. The name is `_integrated_rate`, not `shifted_*` — §4 says "uses `_integrated_rate(t, params)`" which is correct, but it's a private helper (leading underscore). v2 should either (i) expose it as `shifted_N(t, params)` in the shift module or (ii) acknowledge the builder will reach across the privacy boundary.

### C. Dependency graph

- **§5 ordering**: T1 (loader scaffold) → T2 (eval branch) is **inverted from intent**. See §3 first bullet.
- **ceiling vs loader ordering**: §5 T3 (gravity γ-2-1 builder) before T4 (ceiling γ-2-1 predictor) — correct. ceiling_agent reads the new test_grids shape, so loader must produce it first. OK.
- **Is γ-2-1 the right P0?**: ROT-3D is the most invasive vocabulary expansion (1 key → 3 keys, biased direction sampling). It's the *hardest* per-cell change, which makes it a good stress test for the scaffolding. But if it fails the gate, you don't know whether the failure is X.B-specific or generic. **Alternative**: pick δ-2-1 (T_TRANS, adds just `t`) as P0 — strictly simpler, less ambiguous gate. I'd accept either, but the author should note the tradeoff. Recommendation: keep γ-2-1, add δ-2-1 as a secondary P0 smoke before T7 dispatches.

### D. Risk

- **§8.1 rollback observable within 1h**: yes — single cell, single seed, ceiling agent only. OK.
- **§8.2 rollback observable within 1h**: 13 cells × 3 seeds × ceiling = ~40 evaluations, sub-second each. OK.
- **§8.3 P2 per-domain**: observability fine; but the "team-lead may park that domain" exit is loose — define what "park" means (does the cell get a NaN in the final sweep, or is the cell removed?).
- **§8.4 attacker-gate**: observable post-R2 (~1.5 h). OK.

- **§9 load-bearing markers** (verdicts):

| Q | Topic | Load-bearing? | Why |
|---|---|---|---|
| Q1 | CAL-5 bonus | **NO — deferrable** | Affects paper-1 ablation story, not code. Auditor recommends (b) 0.05, author can decide post-T6. |
| Q2 | ROT GT projection | **YES — load-bearing for T3 (P0)** | γ-2-1 builder cannot ship without picking one. Auditor recommends (a) signed-|F|·r̂. |
| Q3 | 5 (actually 6) unread signatures | **YES — load-bearing for T16-T22 (P2)** | See §2.1 above. Adds row 32 to the list. |
| Q4 | damped_ho γ-3-1 x2_mean proxy | **NO — deferrable to T16** | Only affects one P2 cell. Author's "accept proxy" is fine; can be revisited if §6.1 snapshot tolerance fails. |
| Q5 | thermal δ-7-1 PDE-only | **YES — load-bearing for T9 (P1)** | Without picking cache-by-t-bin vs per-point solve, T9 can't be assigned. Recommendation: cache by (seed, round(t, 6)). |
| Q6 | agent_stub upgrade scope | **YES — load-bearing for T5/T13** | "Baseline" reference in figures shifts depending on this. Author's plan to upgrade is fine but must be ratified. |
| Q7 | TODO-2 step() leak interaction | **NO — verification task, per-cell** | Each builder author cross-checks during implementation. |
| Q8 | Input-encoded-in-params vs law-coefficient split | **YES — load-bearing for 9 of 13 P1 cells** | See §2.4 above. |
| Q9 | (b) OOD semantics under expanded vocab | **YES — load-bearing for T3 (P0)** | γ-2-1 has (b). Auditor accepts "5× magnitude, direction sampling identical to (a)". |
| Q10 | Param-name canonicalization edge cases | **YES — load-bearing for T14 (P1 counterfactual)** | See §2.5 above. |

Net: 7 of 10 are load-bearing. v2 must answer Q2, Q3, Q5, Q6, Q8, Q9, Q10 before T3 dispatches.

### E. Agent-executability

- Smallest work item is **T0** (archive pre-XY caches). Could be done from blueprint alone — `git mv` commands listed verbatim in §7.2. OK.
- Smallest *code* work item is **T1** (loader_shifts scaffold). Could be done from blueprint alone — module layout in §3.2, dispatch table in §2.1. Marginal: the sub-agent needs to know the `BuildFn` type signature (return shape). §3.2 "Per-builder contract" provides it. OK.
- **T3** (gravity γ-2-1 builder): **NOT executable from blueprint alone** until §9 Q2 + Q9 are resolved (GT projection + OOD direction). Currently a fresh sub-agent would have to read `blocker-fix-options.md` §1.5 and make the projection choice themselves — that's a design decision, not an implementation task.

---

— end audit round 1 —
