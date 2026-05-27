# MirrorLab X+Y Blueprint — Full Bench Fix

**Author**: blueprint-author (mirrorlab-blueprint team, rounds 1-2)
**Date**: 2026-05-27
**Inputs**: `docs/blocker-consensus.md`, `docs/blocker-fix-options.md`, `docs/blocker-trace.md`, `docs/blocker-physics.md`, `docs/HANDOVER.md`, `docs/v2-todo.md`, `docs/sprint4-sweep-summary.md`, `docs/sprint3-attacker-spec.md`, and reads of `loader.py`, `eval/numeric.py`, `eval/scoring.py`, `runners/ceiling_agent.py`, `scenarios/counterfactual.py`, `shifts/{gravity_g_2_1,gravity_d_2_1,thermal_g_7_1}.py`, plus 36-shift signature grep. **v2 inputs**: `docs/blueprint-xy-review-round1.md` (auditor verdict REVISE).
**Status**: v2 — round-1 audit findings applied (task #3). See §10 "Reviewer pushback" for per-issue status.
**Decision context**: user picked **FULL X+Y over Z+lite-X** in `blocker-fix-options.md` §6. All 36 shifts, all 12 domains, full rerun authorized.

> **Reader contract.** This document is intended to be self-contained for a fresh AI session that has read `HANDOVER.md`. It says *what to change, where, and how to know you're done*. It does NOT re-derive why the blocker exists — that lives in the four `docs/blocker-*.md` files.

---

## §1 — Goals and non-goals

### 1.1 In scope (X+Y)

**X.A — truth-form GT.** Every test-grid sub-grid (`a`/`b`/`c`) ground-truth scalar is computed by calling the catalog's `shifted_*` function (or the domain baseline for `shift_id == "baseline"`), NOT a baseline closure that hard-codes the canonical law.

**X.B — input-vocabulary expansion.** Each shift's test-grid inputs include the axes the truth law actually depends on:
- ROT-break in (x,y,z) → grid keys `{x,y,z}` (gravity γ-2-1, coulomb γ-5-1/2, hooke γ-1-2, thermal γ-7-1, wave γ-8-2, fluid γ-10-2, optics γ-9-1, rlc γ-6-2 coupled).
- T_TRANS-break → grid keys gain `t` (gravity δ-2-1, damped_ho γ-3-2 / δ-3-1, pendulum δ-4-1, rlc δ-6-1, coulomb δ-5-1, thermal γ-7-2 / δ-7-1, wave δ-8-1, optics δ-9-1, fluid δ-10-1, kinetics δ-11-1 / γ-11-1, decay γ-12-1 / γ-12-2 / δ-12-1).
- PAR-break (hooke γ-1-1, pendulum γ-4-1, optics γ-9-2) → existing keys often sufficient (1-D state already exposes sign asymmetry).
- SCALE-break with explicit scale-dependent law (gravity γ-2-2, damped_ho γ-3-1, pendulum γ-4-2, wave γ-8-1, kinetics γ-11-1, fluid γ-10-1, decay γ-12-2, rlc γ-6-1) → keep 1-D inputs but use the shift's actual law shape.

**Y — counterfactual params reach predictor on sub-grid (c).** `evaluate_entry` substitutes the per-point `cf_params[i]` (canonicalized to the shift's declared param-name namespace) into the predictor's param kwargs. A frozen-coefficient submission can no longer auto-track GT_c.

**Combined effect.** S_scen on every shift becomes a real test of "did the agent express the *shifted* law in the inputs the bench reveals."

### 1.2 Out of scope (deferred to v2/camera-ready)

- TODO-1 (IC randomization across 36 shifts) — orthogonal, can ship later.
- TODO-4 (timescale normalization) — affects observability via `sim.step()`, not the scorer.
- TODO-5 (γ-2-2 → 2D promotion to expose Bertrand precession) — leave as 1-D radial since the scorer can already see the shift's radial scale law via X.B; sim-side promotion is a separate task.
- CAL-5 (`bonus = 0.10`) **is recalibrated, not removed**, per §9 open Q1.
- `paper1/main.tex` rewrites — handled in a follow-up paper task once new numbers are in.
- New attacker classes — `lookup.py` prompt is locked; only the slice scoring changes via re-run.

### 1.3 Non-goals (will not happen)

- **No backward-compat layer.** Old `sprint*-data*.json` files become invalid and are archived (§7.2). Submissions that bake constants into predictor closures (the spec-§5 path) become silently wrong on (c); attacker logs document this honestly.
- **No "lenient adapter" that injects `r = √(x²+y²+z²)` to keep 1-D submissions alive on 3-D shifts** — that would re-introduce the X.B failure mode the blocker called out.

---

## §2 — Architecture decisions

### 2.1 Dispatch becomes per (`domain_id`, `shift_id`)

**Current state.** `loader.load(...)` dispatches per `domain_id` via `_NON_HOOKE_GRID_BUILDERS` (loader.py:508-520, called at 545-548). All 3 shifts in a domain share one `_X_test_grids` closure that hard-codes the baseline law.

**New state.** A 37-entry dispatch table keyed by `(domain_id, shift_id)` plus 12 baseline entries (`shift_id == "baseline"`). One builder per cell. Builders are still grouped per file (suggest one new module `loader_shifts/` per domain).

```python
# new module layout:
#   mirrorlab/scenarios/loader.py             — entry point, dispatch only
#   mirrorlab/scenarios/loader_shifts/__init__.py
#   mirrorlab/scenarios/loader_shifts/gravity.py     — 4 builders: baseline + g_2_1 + g_2_2 + d_2_1
#   mirrorlab/scenarios/loader_shifts/hooke.py       — 4 builders
#   ... (12 files)

_GRID_BUILDERS: dict[tuple[str, str], BuildFn] = {
    ("gravity", "baseline"):    gravity_loader.baseline_grids,
    ("gravity", "gamma_2_1"):   gravity_loader.gamma_2_1_grids,
    ("gravity", "gamma_2_2"):   gravity_loader.gamma_2_2_grids,
    ("gravity", "delta_2_1"):   gravity_loader.delta_2_1_grids,
    # ... 48 entries total (12 baselines + 36 shifts)
}
```

This is the single biggest structural change. Every builder owns its own `build(rng, mode)` and `gt(inputs)` closures and explicitly imports its shift module.

### 2.2 Grid input vocabulary

Each builder declares its own grid keys. The canonical input-name order — used by `numeric._alias_inputs` to bridge between grid keys and entry-declared input names — is stored on `ScenarioInstance.canonical_inputs` (a new field). Builders set it explicitly.

**Sampling rules per break family** (concrete recipes in §4):

- **ROT**: sample direction non-uniformly to break the zero-mean angular average that hides γ-2-1's anisotropy (the #2 audit risk in `blocker-fix-options.md` §1.5). Concretely: hold `n̂` from sampler fixed, then sample direction `d̂` over a small cone around `n̂` (high anisotropy contrast) AND a wide cone (low contrast) — half each. Returns ⟨μ²⟩ ≠ 1/3 in the (a)-grid.
- **T_TRANS**: in addition to scalar inputs (`r`, `theta`, etc.), sample `t` in `[0, 2π/Ω_modulation]` for shifts whose modulation has a sampler-known frequency; for shifts whose modulation is non-periodic (decay-type), sample `t` in `[0, t_scale]` where `t_scale` is set in §4.
- **PAR**: ensure both signs of the relevant 1-D coordinate are sampled (already true via `_linspace_signed`). No further changes for hooke γ-1-1 etc.
- **SCALE**: extend the in-domain range to span ≥1 decade of the scale parameter, so the shift's scale-dependent correction is visible (γ-2-2 r-scale, γ-11-1 fractional-order kinetics, γ-12-2 decay-rate ε-modulation).

### 2.3 Predictor signature — Y plumbing

**Loader change.** `_pack` builds grid_c as 3-tuples `(inputs, gt_scalar, cf_params_obj)`. (a)/(b) remain 2-tuples — they have no per-point param perturbation.

```python
# old: _pack returns Dict[str, List[Tuple[Dict, float]]]
# new:
GridA = list[tuple[Mapping[str, float], float]]
GridB = list[tuple[Mapping[str, float], float]]
GridC = list[tuple[Mapping[str, float], float, Any]]   # 3-tuple
TestGrids = Mapping[str, Sequence]   # heterogeneous
```

**Numeric change.** `evaluate_entry` branches on subgrid key:

```python
for key, grid in test_grids.items():
    if key == "c":
        preds, truths = _eval_subgrid_c(predictor_raw, declared_params, grid, ...)
    else:
        preds, truths = _eval_subgrid_ab(predictor, grid, ...)
```

`_eval_subgrid_c` does the per-point param override:

```python
def _eval_subgrid_c(raw_predictor, declared_params, grid, ...):
    for ins, gt, cf_params_obj in grid:
        cf_overrides = _params_to_predictor_kwargs(cf_params_obj)
        kwargs = {**declared_params, **cf_overrides, **_alias_inputs(ins, ...)}
        preds.append(_safe_call(raw_predictor, kwargs))
    truths = [gt for _, gt, _ in grid]
    return preds, truths
```

`raw_predictor` is the bare callable extracted from `entry["predictor"].code` (or `entry["_predictor"]`) **without** the param closure that `_entry_predictor` currently applies. The current `bound(**kwargs)` wrapper is retained for (a)/(b), where declared params should win.

**Unstated requirement A — signature filtering on the raw predictor.** The (a)/(b) `bound` wrapper already filters `**kwargs` against the predictor's declared signature (`numeric.py:117-123`). On (c) we drop the closure but MUST keep the filter, otherwise calls like `f(r, G, M, m)` with `kwargs = {x, y, z, G, M, m, ...}` raise `TypeError: unexpected keyword 'x'` even though the call is well-formed at the dimensional level. Implementation: `_eval_subgrid_c` MUST use a signature-filtered call (either `_safe_call` is enhanced to filter against `inspect.signature(raw)`, or `_entry_predictor_raw` returns a thin filtered wrapper analogous to `bound` minus the param closure). v2 mandates the latter — `_entry_predictor_raw` returns `lambda **kw: f(**{k: kw[k] for k in allowed if k in kw})` where `allowed = sig.parameters` ∪ `{**_}` catch-all. The filter MUST also log filtered-out keys at WARN level the first time per (cell, seed) — see §2.6.

**Unstated requirement B — `_alias_inputs` silently drops on baseline-form submissions.** `_alias_inputs(ins, canonical_order=("x","y","z"), entry_inputs=[{"name":"r"}])` calls `zip(canonical_order, entry_inputs)` (`numeric.py:145`); zip stops at min length, so **only `x → r` is aliased and `y, z` are silently dropped**. Then `kwargs["r"] = ins["x"]` — not `√(x²+y²+z²)`. **This is by design** — it is precisely how X.B exposes baseline-form submissions whose declared `inputs` list is narrower than the scenario's `canonical_inputs`: they only see the first N grid keys (positional, in canonical order) and consequently score poorly on the anisotropic ROT grids. The blueprint records this contract explicitly so sub-agent implementers do not "fix" it. Optional safety: emit a one-shot INFO log "baseline-form drop: declared_inputs=[r], canonical=[x,y,z], dropped=[y,z]" so the failure mode is visible in logs without breaking the intended scoring.

**Coefficient-vs-input name collision.** The merge order in line above (`{**declared, **cf_overrides, **_alias_inputs(ins,...)}`) puts inputs LAST, so input keys win over coefficient keys. If an LLM declares an input name (e.g. `m`) that collides with a law-coefficient name (also `m` in gravity), the per-point input value wins. Documented edge: cf override is supposed to win for coefficients; resolution is enforced upstream by §2.4 disjointness (the namespaces must be disjoint, so a collision means the submission is malformed and should score 0 on that point; track this in `evaluate_entry` warnings).

**`_params_to_predictor_kwargs`** is a new function in `eval/numeric.py` that takes a per-shift params dataclass and emits a flat `{name: float}` dict. Field-name canonicalization is needed because shift-internal names (`G0`, `q_src`, `lam0`) differ from spec-§5 declared names that LLMs tend to emit (`G`, `q1`, `lam`). The canonical mapping lives in `counterfactual.py` (extended `_LAW_PARAM_FIELDS` with target-name aliases) — see §3.6.

### 2.4 Input-encoding vs law-coefficient param-field disjointness (Q8 resolution)

For shifts whose `shifted_*` consumes a Params object that encodes *both* inputs (mutated per grid point) and law coefficients (mutated only by `cf_params` on subgrid-c), the two roles MUST be partitioned on disjoint field-name sets. The partition is:

- **Law-coefficient fields** — exactly the set `counterfactual._LAW_PARAM_FIELDS[type(params)]`. Mutated ONLY by `cf_params` on (c). Forbidden for builders to mutate per grid point (any (a)/(b)/(c) point).
- **Input-encoding fields** — everything else on the Params dataclass (e.g. `T_hot`, `T_cold`, `L`, `grad_dir` for `ThermalGamma71Params`; `v_vec`, `h1`, `h2` for fluid). Mutated freely by builders per grid point. Forbidden for `cf_params` to touch.

**Invariant.** `set(_LAW_PARAM_FIELDS[T]) ∩ set(builder_mutated_fields[T]) == ∅` for every shift type T.

**Enforcement.**
1. Add a unit test `tests/scenarios/test_param_field_disjointness.py` parametrized over all 36 shifts. For each shift, introspect the builder (via a `@register_builder` decorator that records the set of fields the builder mutates) and assert the intersection is empty.
2. `counterfactual.draw_counterfactual_params(params)` already restricts its mutations to `_LAW_PARAM_FIELDS[type(params)]`. Add an inverse-direction guard: at the top of each input-encoding builder, the helper `_assert_builder_mutates_only(non_law_fields)` validates the set being mutated.
3. Cells affected: thermal γ-7-1 / γ-7-2 / δ-7-1, fluid γ-10-1 / γ-10-2 / δ-10-1, optics γ-9-1 / γ-9-2 / δ-9-1 — 9 of 13 P1 cells.

### 2.5 Param-name canonicalization rule (Q10 resolution)

`_PREDICTOR_NAME_MAP` (§3.6) maps shift-internal Params field names (`G0`, `lam0`, `q_src`, `L0`, `M01`) to predictor-facing kwarg names (`G`, `lam`, `q1`, `L_0`, `M_01`). v2 pins the rule:

1. **Lowercase** the field name.
2. **Strip trailing `0` ONLY if it is the field's "free-coefficient suffix"** — defined as: the bare lowercase form (e.g. `G`, `lam`, `c`, `k`) is the canonical physics symbol AND no other coefficient on the same Params dataclass would collide. Example: `G0 → G`, `lam0 → lam`, `c0 → c`. Counter-example: RLC has `L0, L1, L2` — none of them strip; they map to `L_0, L_1, L_2` (preserve numeric suffix; insert underscore for readability and to avoid bare `L` ambiguity).
3. **Multi-coupling fields** (`M01, M02, M12` mutual inductances): preserve the numeric pair → `M_01, M_02, M_12`.
4. **Role-modifier suffixes** (`_src`, `_test`, `_e` in coulomb): drop the role modifier AND replace by a sequential numeric suffix in declaration order. Example: `coulomb γ-5-1` Params with `(q_src, q_test)` → `(q_1, q_2)`. For γ-5-2 with `(src1_q, src2_q, test_q)` → `(q_1, q_2, q_3)` (test is last by convention). The canonical order is whatever order the fields appear in the Params dataclass — this is stable per shift module.
5. **Round-trip property test.** For every type in `_LAW_PARAM_FIELDS`, assert that `_PREDICTOR_NAME_MAP[T]` is a bijection (no two internal fields map to the same predictor-facing name).

This rule is baked into `counterfactual._PREDICTOR_NAME_MAP` as a literal `dict[type, dict[str, str]]`. The dict is hand-built (not derived) so that the canonical order on coulomb γ-5-2 is unambiguous and reviewable.

### 2.6 Ceiling-agent signature-mismatch detection

The current `ceiling_agent` flow wraps its predictor via `_safe_call`, which silently filters kwargs against `inspect.signature`. Per `blocker-trace.md` this is what made the 3-D inputs vanish into thin air on the old loader, surfacing as a "numeric problem" instead of a "signature problem". v2 mandates:

1. **First call per (cell, seed) emits a WARN log** listing the kwargs that were filtered out. Implementation: a module-level `_FILTER_WARNED: set[tuple[str, str, int]]` guards the warning so each tuple is logged once.
2. **If the filtered set is non-empty AND the predictor has NO `**kwargs` catch-all**, the wrapper raises `SignatureMismatchError` instead of returning CLAMP. Rationale: a ceiling submission that does not list the canonical inputs is a bug, not a low-scoring submission — silently CLAMPing hides regressions.
3. **The agent_stub baseline submission is exempt** — it is *expected* to score badly on (c) via the input-drop mechanism (§2.3 requirement B). The exemption is keyed on `entry["meta"]["expected_baseline"] is True`.

### 2.7 Backward-compat — **NONE**

Per user decision:

- All cached sweep JSONs (`docs/sprint3-pilot-data*.json`, `docs/sprint35-pilot-data*.json`, `docs/sprint4-sweep-data*.json`, `docs/sprint4-ceiling-data*.json`) move to `docs/archive/pre-xy/` in P0 (§7.2). The rerun produces fresh files with the same names.
- `mirrorlab/runners/rescore.py` is updated to refuse to run on pre-XY data files (detect by absence of a new `"xy_version": 1` key in the JSON header) — see §3.8.
- Tests under `tests/scenarios/test_loader_*.py` that assert exact GT == baseline formula are rewritten (∼25 cases, §6.1).
- Spec §5 (`docs/paper1-spec.md`) gains a new subsection §5.4 "predictor signature for X+Y": predictors MUST accept the shift's param names as kwargs and MUST NOT bake them into closures. Compliance is checked by a new test fixture `tests/eval/test_subgrid_c_overrides.py` (§6.2).

---

## §3 — File-by-file change list

### 3.1 `mirrorlab/scenarios/loader.py` (≈+450 net LOC, mostly extracted into `loader_shifts/`)

| Region | Action |
|---|---|
| L23-37 (imports) | Drop unused domain DIM imports (keep what `_DOMAIN_DIM` still needs). Add `from mirrorlab.scenarios import loader_shifts as _builders`. |
| L86-124 (`ScenarioInstance`) | Add `canonical_inputs: tuple[str, ...] = ()` field. Keep `test_grids` typed as `Mapping[str, Sequence]` since (c) is heterogeneous. |
| L127-146 (`_hooke_test_grids`) | DELETE. Move logic to `loader_shifts/hooke.py:baseline_grids`. |
| L149-218 (helpers `_attr`, `_pack`, `_linspace_signed`, `_ood_signed`) | Move to `loader_shifts/_common.py`. Modify `_pack` so grid_c is 3-tuple (see 2.3). |
| L223-505 (all `_X_test_grids`) | DELETE. Distributed to `loader_shifts/<domain>.py` files, one builder per (domain, shift). |
| L508-520 (`_NON_HOOKE_GRID_BUILDERS`) | DELETE. Replaced by `_GRID_BUILDERS` in `loader_shifts/__init__.py` keyed on `(domain_id, shift_id)`. |
| L523-562 (`load`) | Rewrite dispatch:<br>`builder = _GRID_BUILDERS.get((domain_id, shift_id))`<br>`if builder is None: raise KeyError(...)`<br>Pass `sim`, `seed`, `counterfactual_magnitude` to builder; receive `(test_grids, cf_params, canonical_inputs)`. Populate new `ScenarioInstance.canonical_inputs`. |

**Done criteria.**
- `python -c "from mirrorlab.scenarios.loader import load; load('gravity', 'gamma_2_1', seed=0)"` returns a `ScenarioInstance` with `test_grids["a"][0]` matching `gravity_g_2_1.shifted_force` projected (§4 row spec) to machine precision.
- `test_grids["c"][0]` is a 3-tuple whose third element is a `GravityGamma21Params`.
- All 48 `(domain, shift)` dispatch keys resolve without `KeyError`.

### 3.2 New module `mirrorlab/scenarios/loader_shifts/` (≈12 files, ~700 LOC total)

- `_common.py`: `_attr`, `_linspace_signed`, `_ood_signed`, `_pack` (with 3-tuple grid_c), `_GRID_SIZE = 11`, `_OOD_FACTOR = 5.0`.
- `gravity.py`: `baseline_grids`, `gamma_2_1_grids`, `gamma_2_2_grids`, `delta_2_1_grids`. Each returns `(test_grids, cf_params, canonical_inputs)`. Sketch in `blocker-fix-options.md` §1.3 for γ-2-1.
- `hooke.py`, `damped_ho.py`, ..., `decay.py`: same pattern. Matrix in §4 below is the per-shift spec.

#### 3.2.1 step()-only shifts (Q3 resolution)

**Six shift modules have NO exported `shifted_*` closed-form** (verified by round-1 audit grep):

1. `kinetics_d_11_1` — δ-11-1, dissipative kinetics
2. `kinetics_g_11_2` — γ-11-2 (auditor-discovered; missed in v1)
3. `wave_d_8_1` — δ-8-1, wavepacket decay
4. `optics_d_9_1` — δ-9-1, time-modulated n
5. `decay_g_12_1` — γ-12-1, λ(t) modulation
6. `decay_d_12_1` — δ-12-1

Each exports only `Instance(...).step(t) -> dict[str, float]`. v2 commits to path (a) **step()-based truth projection** (NOT closed-form addition — adding closed forms would either duplicate solver code or require new physics derivation that is out of scope for X+Y):

- Each builder constructs an `Instance` once per grid (cache by `(seed, builder_id)`), then calls `step(t)` per grid point.
- The chosen scalar observable is fixed per cell in §4 (column "shifted_* fn signature") and matches the agent prompt's `observables` declaration.
- For PDE shift (thermal δ-7-1, see §2.7-equivalent below), the same pattern applies but with `solve_ivp` cached by `(seed, round(t, 6))` — see Q5 resolution at §9.

**Per-cell observable projections** (locked in v2):

| # | shift_id | step() projection |
|---|---|---|
| 24 | wave/δ-8-1 | `step(t)["amplitude"]` (envelope only; phase tracked separately if needed) |
| 27 | optics/δ-9-1 | `step(t)["sin_theta_t"]` (transmitted-angle sin, matches Snell observable) |
| 31 | kinetics/γ-11-1 | `step(t)["C"]` (concentration) |
| 32 | kinetics/γ-11-2 | `step(t)["C"]` |
| 33 | kinetics/δ-11-1 | `step(t)["C"]` |
| 34 | decay/γ-12-1 | `step(t)["N"]` |
| 35 | decay/γ-12-2 | `step(t)["N"]` (replaces v1 plan of calling private `_integrated_rate`; uniform with the rest of decay) |
| 36 | decay/δ-12-1 | `step(t)["N"]` |

**Performance note.** `step(t)` on the kinetics/decay shifts is O(microseconds) (closed-form sigmoid/exponential expressions inside `step`). For PDE thermal δ-7-1 the per-call cost is O(10-100 ms); §6.5 budget below reflects this.

#### 3.2.2 Per-builder contract

```python
def gamma_2_1_grids(sim, seed, magnitude):
    """Returns (test_grids, cf_params, canonical_inputs).

    test_grids:
        "a": [(inputs:dict, gt:float), ...]     length=11
        "b": [(inputs:dict, gt:float), ...]     length=11
        "c": [(inputs:dict, gt:float, cf_p), ...] length=11
    cf_params: tuple[GravityGamma21Params, ...] length=11 (= test_grids['c'])
    canonical_inputs: ("x", "y", "z")   # the truth-law's natural input order
    """
```

### 3.3 `mirrorlab/eval/numeric.py` (≈+90 net LOC)

| Region | Action |
|---|---|
| L25 (`SUBGRID_WEIGHTS`) | Unchanged. |
| L27-29 (`TestPoint`, `SubGrid`, `TestGrids`) | Add `TestPointC = tuple[Mapping[str, float], float, Any]`, `SubGridC = Sequence[TestPointC]`. |
| L92-125 (`_entry_predictor`) | Split into two helpers:<br>- `_entry_predictor_bound(entry)` → the current closure with `param_values` baked in. Used for (a)/(b).<br>- `_entry_predictor_raw(entry)` → the bare `f` callable, no param closure. Used for (c). |
| New (~L140) | `_params_to_predictor_kwargs(cf_params: Any) -> dict[str, float]` — uses `counterfactual._PREDICTOR_NAME_MAP` (§3.6) to map shift-internal field names to predictor-facing kwarg names. |
| L164-210 (`evaluate_entry`) | Restructure loop: branch on `key == "c"`. Pass `entry.get("params", [])` declared values forward; on (c), per-point override with `cf_overrides`. |

**Done criteria.**
- A 2-line predictor `def f(r, G, M, m): return -G*M*m/(r*r)` declared with `G=6.67e-11, M=1.0, m=1.0` gets `G,M,m` overridden by `cf_params` on (c). Assertion: `pred(r=5e6)` on subgrid-c-point-0 uses `G_cf, M_cf` (not declared `G,M`).
- On (a) and (b), declared params still win (current behavior preserved).

### 3.4 `mirrorlab/eval/scoring.py` (no changes needed in v1)

The 3-tuple is consumed inside `evaluate_entry`. `score_submission` calls `evaluate_entry(e, test_grids, ...)` and only inspects the scalar return. **Sanity check during P0**: confirm no `len(test_grids["c"])`-based logic regresses; if so, add a thin tuple-shape guard.

### 3.5 `mirrorlab/runners/ceiling_agent.py` (≈+350 LOC)

| Region | Action |
|---|---|
| L28-65 (imports) | Already imports all 36 shift modules — keep. |
| L98-367 (`_*_pred` dispatch) | Rewrite each `_<domain>_pred(scenario)` to:<br>1. Branch on `scenario.shift_id`.<br>2. For each branch, return a `pred(**kw)` that calls `shifted_*` with the **3-D or t-bearing inputs** the new test grid actually delivers (§4). NO scalar fallback — that's what made ceiling = baseline.<br>3. The fallback `except Exception` clause should NOT silently default to baseline; it should log via `warnings.warn(...)` and return `CLAMP`. Otherwise a wrong shifted_* call silently scores well.<br>4. For shifts whose `shifted_*` consumes inputs only via params (`thermal_g_7_1.shifted_flux_magnitude`, `fluid_g_10_1.shifted_pressure`, etc.), the predictor needs to rebuild a params object from kwargs — see §4 per-row notes. |
| L437-464 (`build_submission`) | Add a per-entry `inputs` list reflecting the **new canonical order** from `scenario.canonical_inputs`. `params` list is now non-empty: the ceiling agent declares each shift's law-param fields so Y plumbing has names to override on (c). |

**Done criteria.**
- For γ-2-1 seed=0: ceiling `S_scen` (without bonus) on (a)+(b) is ≥ 0.95. (Bonus still adds 0.10.)
- For γ-7-1 seed=1 (the truth-vs-baseline -0.44 case from `blocker-physics.md`): ceiling on (a)+(b) is ≥ 0.95, baseline submission drops to ≤ 0.5.
- Discriminating-power test: ceiling > truth-projected ≥ baseline on the same scenario, on all 36 shifts.

### 3.6 `mirrorlab/scenarios/counterfactual.py` (≈+80 LOC)

| Region | Action |
|---|---|
| L87-150 (`_LAW_PARAM_FIELDS`) | Extend each entry to a tuple of `(internal_name, predictor_facing_name)`. Use the names that LLMs actually emit (cross-reference with `agent_stub.py` and the `claude-opus-4.6` example in `sprint4-sweep-summary.md` diagnostic notes: `q1`, `q2`, `r`, `G`, `M`, `m`, `k`, `c`, `lam`, ...). |
| New (~L160) | `_PREDICTOR_NAME_MAP: dict[type, dict[str, str]]` — derived once from the extended `_LAW_PARAM_FIELDS`. Module-level constant. |
| New (~L190) | `def params_to_predictor_kwargs(params)` — public function `numeric._params_to_predictor_kwargs` delegates to this. Idempotent: passing a dict-like returns it unchanged. |

**Done criteria.**
- `params_to_predictor_kwargs(GravityGamma21Params(G0=7e-11, M=1e21, m=1.0, xi=0.06, ...))` returns `{"G": 7e-11, "M": 1e21, "m": 1.0, "xi": 0.06, ...}` (note: `G0` → `G`).
- Test: round-trip property — for each of the 48 (params type, predictor-facing dict) pairs, the predictor-facing kwargs are a superset of the predictor's declared param names in `ceiling_agent.build_submission`.

### 3.7 `mirrorlab/scenarios/agent_stub.py` + `mirrorlab/scenarios/prompts.py` (≈+200 LOC)

| Action | Detail |
|---|---|
| `prompts.py` per-domain templates | Update declared `observables` and the prompt body to list the new input names (`x,y,z` for ROT, `+ t` for T_TRANS). The agent must know to write a predictor that accepts these. |
| `prompts.GRAVITY_OBSERVABLES` etc. | Update tuples to reflect new keys per §4. Used by the dim-signature filter — if mismatch, agents legitimately score 0. |
| `agent_stub.py` | The rule-based baseline agent must emit a predictor whose signature accepts the new inputs. For ROT shifts, the stub now declares e.g. `def f(x, y, z, G, M, m): r = sqrt(x*x+y*y+z*z); return -G*M*m/(r*r)`. This stub scores **as the X+Y baseline** — by construction it can't see the anisotropy, so its score on γ-2-1 is the new floor that the LLM must beat. |

**Done criteria.**
- `agent_stub` on γ-2-1 baseline-form submission yields `S_scen ∈ [0.85, 0.95]` (numeric only; correct dim, wrong law-class).
- `ceiling_agent` on γ-2-1 truth-form submission yields `S_scen ∈ [0.97, 1.05]` (numeric only). The gap proves X.B exposes the anisotropy.
- **Stub fixture test (auditor §3 bullet 6)**: `tests/scenarios/test_agent_stub_fixture.py` asserts that for every shift, the stub's emitted predictor code (i) parses, (ii) evaluates without raising on a synthetic input drawn from the scenario's canonical_inputs vocabulary, and (iii) the callable's `inspect.signature` exposes the declared param kwargs. This catches typos that would otherwise silently zero out all baseline numbers (the sprint4 `q1,q2,r` regression mode).

### 3.8 `mirrorlab/runners/rescore.py` (≈+30 LOC)

Add a header-version guard: refuse to rescore JSON files that lack a `"xy_version": 1` key in their top-level metadata block. Emit a pointer to `docs/archive/pre-xy/`. This prevents accidental contamination of new sweep results with old grid keys.

### 3.9 `docs/paper1-spec.md` §5 (predictor signature)

New §5.4 paragraph (≈30 lines markdown):

> **§5.4 Predictor signature (X+Y).** A submission's `predictor.code` MUST define a callable `f(...)` whose keyword arguments are a superset of:
> (i) the scenario's input vocabulary `canonical_inputs` (e.g. `x, y, z` for γ-2-1, `r, t` for δ-2-1);
> (ii) the scenario's declared param names — listed in the agent prompt and consumed verbatim by the evaluator on sub-grid (c).
> A predictor that bakes param values into a closure scores per (a)/(b) using its declared `params` block, but fails (c) where the evaluator substitutes counterfactual values. This is by design: (c) tests whether the submission's *law* (not just its *fit*) generalizes under parameter perturbation.

### 3.10 `docs/blueprint-xy.md` itself

Lives. Updated when round-1 audit lands (task #2 → task #3).

---

## §4 — Per-shift work matrix (all 36 shifts)

> **Legend.** Priority tier: P0 = γ-2-1 only (proof-of-concept); P1 = sprint-4 sweep domains (hooke, coulomb, thermal, decay = 12 shifts); P2 = remaining 21 shifts. "Sampling concern" calls out the specific risk from #2 audit or our own analysis. Truth function "uses params for inputs" means the shifted_* function's argument is entirely a Params object — the inputs are encoded as fields, and the grid varies inputs by mutating those fields per point. **Gloss on ⟨μ²⟩.** Where the "biased direction" sampling rules below mention ⟨μ²⟩, this is the zero-mean angular average `μ = n̂·d̂` taken over the (a)-grid sample of query directions `d̂`. The uniform-sphere expectation is `⟨μ²⟩ = 1/3`; the bias recipe in §2.2 (half cone-around-n̂, half wide cone) deliberately produces `⟨μ²⟩ ≠ 1/3` so that anisotropic shift terms with `(n̂·d̂)²` factors do not zero out in the average. Derivation: `blocker-fix-options.md` §1.5.

### 4.1 Baselines (12 cells, all P1 with respective domains)

For every domain, `("<domain>", "baseline")` builder uses the canonical law evaluated with `sim.params`. Inputs match domain DIM_SIGNATURE. CAL-5 GT label = `"none"`. These are unchanged from current loader behavior except for the dispatch refactor.

### 4.2 36 shifts

| # | shift_id | sym | current grid keys | new grid keys | shifted_* fn signature | sampling concern | tier |
|---|---|---|---|---|---|---|---|
| 1 | hooke/gamma_1_1 | PAR | {x} | {x} | `shifted_force(x, p) -> float` | spans both signs already (`_linspace_signed`). Confirm OOD covers `x_scale`. | P1 |
| 2 | hooke/gamma_1_2 | ROT | {x,v} | {x,y} | `shifted_force((x,y), p) -> (Fx,Fy)`. Grid returns `‖F‖` projected onto query direction. | sample 2-D points off-axis; avoid pure x-axis sampling that hides ROT. | P1 |
| 3 | hooke/delta_1_1 | TR  | {x,v} | {x,v} | `shifted_force(x, v, p) -> float` | velocity sign coverage. Already OK. | P1 |
| 4 | gravity/gamma_2_1 | ROT | {r} | {x,y,z} | `shifted_force((x,y,z), p) -> (Fx,Fy,Fz)`. **GT = signed-\|F\| projection onto query r̂ = (x,y,z)/‖(x,y,z)‖** (Q2 locked option (a)). Same convention applied to rows 13, 14, 19, 23, 28, 29. | **biased direction sample** (half cone-around-n̂, half wide) to avoid ⟨μ²⟩=1/3 zero-mean problem (#2 audit). | **P0** |
| 5 | gravity/gamma_2_2 | SCALE | {r} | {r} | `shifted_force(r, p) -> float` | span `r ∈ [0.5·r_scale, 5·r_scale]` so the scale-dependent term is visible. | P2 |
| 6 | gravity/delta_2_1 | T_TRANS | {r} | {r, t} | `shifted_force(r, t, p) -> float` | sample `t ∈ [0, 2π/ω_G]` uniformly + edge cases at modulation extrema. | P1 |
| 7 | damped_ho/gamma_3_1 | SCALE | {x,v} | {x, v, x2_mean} | `shifted_law(x, v, x2_mean, p) -> float` | `x2_mean` comes from running simulation; for the grid, pre-compute `x2_mean = x²` (single-point proxy) and document the approximation. | P2 |
| 8 | damped_ho/gamma_3_2 | T_TRANS | {x,v} | {x,v,t} | `shifted_law(x, v, t, p) -> float` | sample `t ∈ [0, 2π/Ω_p]`. | P2 |
| 9 | damped_ho/delta_3_1 | TR | {x,v} | {x,v} | `shifted_law(x, v, p) -> float` | non-linear in `x/L`, ensure both `|x|<L` and `|x|>L` in (a). | P2 |
| 10 | pendulum/gamma_4_1 | PAR | {theta} | {theta} | `shifted_law(theta, p) -> float` | PAR break visible already in sign of θ. | P2 |
| 11 | pendulum/gamma_4_2 | SCALE | {theta} | {theta} | `shifted_law(theta, p) -> float` | wider θ range so height-dep correction matters. | P2 |
| 12 | pendulum/delta_4_1 | T_TRANS | {theta} | {theta, t} | `shifted_law(theta, t, p) -> float` | sample `t ∈ [0, 2π/Ω]`. | P2 |
| 13 | coulomb/gamma_5_1 | ROT | {r} | {x,y,z} | `shifted_force((x,y,z), p) -> (Fx,Fy,Fz)`. GT = signed projection. | biased direction sample (same recipe as #4). | P1 |
| 14 | coulomb/gamma_5_2 | ROT | {r} | {x,y,z} | `shifted_force((x,y,z), p) -> (Fx,Fy,Fz)` | 2-source field; sample positions inside the physically valid region (validator's min-distance, see TODO-7). | P2 |
| 15 | coulomb/delta_5_1 | T_TRANS | {r} | {q1, q2, t} | `shifted_law(q1, q2, p) -> dq_vec` (depends on `t` via `p.alpha * t^n`). GT = `‖dq/dt‖`. | sample `t ∈ [0, p.E_ref]`; sample charges via small perturbation around `q_src/q_test`. | P1 |
| 16 | rlc/gamma_6_1 | SCALE | {i,didt,q} | {i, q} | `shifted_law(q, i, p) -> didt`. GT = didt. | wider `i` range so `L_eff(i)` non-linearity surfaces. | P2 |
| 17 | rlc/gamma_6_2 | ROT | {i,didt,q} | {q1,i1,q2,i2} | `shifted_law(q1,i1,q2,i2,p) -> (didt1,didt2)` | sample asymmetric mode (only loop-1 excited vs only loop-2) to break coupling-blindness. | P2 |
| 18 | rlc/delta_6_1 | T_TRANS | {i,didt,q} | {i, q, t} | `shifted_law(q, i, t, p) -> didt` | sample `t ∈ [0, 2π/Ω_p]`. | P1 |
| 19 | thermal/gamma_7_1 | ROT | {T_hot,T_cold,L} | {T_hot, T_cold, L, n_dot_d} | `shifted_flux_magnitude(params)` — params encode inputs. Build per-point `params_local = replace(sim.params, T_hot=..., T_cold=..., L=..., grad_dir=...)`, then call. | **biased grad_dir sample** (half ≈n̂-aligned, half ⊥) so γ-7-1 seed=1 -0.44 case scores correctly. | P1 |
| 20 | thermal/gamma_7_2 | T_TRANS | {T_hot,T_cold,L} | {T_hot, T_cold, L, t} | `shifted_flux(t, params)` | sample `t > tau_min`; log-uniform `t ∈ [tau_min, 100·tau_min]`. | P1 |
| 21 | thermal/delta_7_1 | T_TRANS | {T_hot,T_cold,L} | {T_hot, T_cold, L, t} | no closed `shifted_*` — uses `_rhs` PDE. GT = `solve_ivp` at the per-point `t`, returning a chosen observable (mean T or boundary flux); fix at builder construction. | requires sim invocation per grid point — cache by `(seed, t_bin)`. | P1 |
| 22 | wave/gamma_8_1 | SCALE | {x,t} | {x, t, k} | `shifted_omega_squared(params)` → `omega^2(k)`. GT for wave field = `A·cos(k·x − √(ω²) ·t + phi)`. Builder computes ω from params then evaluates cos. | sample `k` log-uniformly across 1 decade so γ·k correction varies. | P2 |
| 23 | wave/gamma_8_2 | ROT | {x,t} | {x, y, t, theta_k} | `shifted_omega_squared(params)` (anisotropic) → ω²(k, θ_k). GT = `A·cos(k_x·x + k_y·y − ω·t + phi)`. | sample `theta_k` biased toward `params.theta0` (anisotropy axis) and orthogonal. | P2 |
| 24 | wave/delta_8_1 | T_TRANS | {x,t} | {x, t} | **step()-only** (§3.2.1). GT = `step(t)["amplitude"]`; phase tracked separately if needed. | sample `t` log-uniformly. | P2 |
| 25 | optics/gamma_9_1 | ROT | {theta1} | {theta1, phi_pol} | `n_eff(params)` (anisotropic n), then GT = Snell with `n_eff`. Builder must build per-point params with `theta_pol` varied. | sample polarisation angle on both alignments. | P2 |
| 26 | optics/gamma_9_2 | PAR | {theta1} | {theta1} | `shifted_sin_theta_t(params)` — uses `params.theta_i`. Per-point: replace params.theta_i. | sample both signs of θ1 (PAR break visible). | P2 |
| 27 | optics/delta_9_1 | T_TRANS | {theta1} | {theta1, t} | **step()-only** (§3.2.1). GT = `step(t)["sin_theta_t"]`. | sample `t` per shift's modulation period. | P2 |
| 28 | fluid/gamma_10_1 | SCALE | {p1,v1,v2,h1,h2} | {p1,v1,v2,h1,h2} | `shifted_pressure(params)` — params encode inputs. Build per-point params. | wider velocity range so anisotropic-mass tensor correction surfaces. | P2 |
| 29 | fluid/gamma_10_2 | ROT | {p1,v1,v2,h1,h2} | {p1, v_vec=(vx,vy), h1, h2} | `shifted_pressure(params)` (rotational). Per-point params with v_vec mutated. | sample `v_vec` directions non-uniformly. | P2 |
| 30 | fluid/delta_10_1 | T_TRANS | {p1,v1,v2,h1,h2} | {p1,v1,v2,h1,h2,t} | `shifted_pressure(params)` (time-varying ζ). Per-point params with t mutated. | sample `t` per shift's relaxation timescale. | P2 |
| 31 | kinetics/gamma_11_1 | SCALE | {C} | {C, t} | fractional-order kinetics; uses `_step_fractional(params, t_target)`. Per-point: call with mutated params and t. | sample `t` log-uniformly; C in 1 decade. | P2 |
| 32 | kinetics/gamma_11_2 | T_TRANS | {C} | {C, t} | **step()-only** (§3.2.1; auditor-discovered, missed in v1). GT = `step(t)["C"]`. | sample `t` per modulation. | P2 |
| 33 | kinetics/delta_11_1 | T_TRANS | {C} | {C, t} | **step()-only** (§3.2.1). GT = `step(t)["C"]`. dissipative kinetics with η drift. | sample `t` log-uniformly. | P2 |
| 34 | decay/gamma_12_1 | T_TRANS | {N} | {N, t} | **step()-only** (§3.2.1). GT = `step(t)["N"]`. λ(t) modulation. | sample `t` per modulation. | P1 |
| 35 | decay/gamma_12_2 | SCALE | {N} | {N, t} | **step()-only** (§3.2.1; replaces v1 plan of reaching across `_integrated_rate` privacy boundary). GT = `step(t)["N"]`. | sample `t` log-uniformly. | P1 |
| 36 | decay/delta_12_1 | T_TRANS | {N} | {N, t} | **step()-only** (§3.2.1). GT = `step(t)["N"]`. | sample `t` per modulation. | P1 |

**P0** = 1 shift (γ-2-1). **P1** = 13 shifts (P0 + sprint4 4 baselines + the 12 γ/δ pairs the sprint4 sweep already covers). **P2** = 22 shifts.

> **Note on step()-only shifts.** Six cells (rows 24, 27, 32, 33, 34, 35, 36 — wait, that's 7 — see below) export only `Instance.step(t)`, not `shifted_*`. v2 commits to step()-based truth projection per §3.2.1 with locked scalar observables. Counting correction: rows 24, 27, 32, 33, 34, 35, 36 are 7 entries because v1 missed kinetics γ-11-2 (row 32). The auditor-noted "6 shifts" reflects the v1 list `{kinetics δ-11-1, kinetics γ-11-2, wave δ-8-1, optics δ-9-1, decay γ-12-1, decay δ-12-1}` (6) — γ-12-2 row 35 is added by v2 because the v1 plan of reaching into the private `_integrated_rate` helper is now rejected in favor of uniform `step()` usage. Net: 7 step()-only cells in v2. All resolved here; Q3 closed.

---

## §5 — Implementation ordering (DAG)

```
[T0]  archive pre-XY caches             ← unblocks everyone
   └─> [T1] _pack 3-tuple change + eval/numeric subgrid-c branch (Y plumbing)  ← swapped per auditor §3
         └─> [T2] loader_shifts/ scaffold (empty modules + dispatch table)
               └─> [T3] gravity/gamma_2_1 builder (P0)
                     └─> [T4] ceiling_agent γ-2-1 truth predictor
                           └─> [T5] agent_stub γ-2-1 baseline-form
                                 └─> [T6] end-to-end smoke: ceiling > baseline on γ-2-1, both numerically valid
                                       └─> ★ P0 CHECKPOINT ★  (rollback gate §8.1)
                                             ├─> [T7]  loader_shifts/hooke.py  (4 cells: baseline + γ-1-1 + γ-1-2 + δ-1-1)
                                             ├─> [T8]  loader_shifts/coulomb.py
                                             ├─> [T9]  loader_shifts/thermal.py
                                             ├─> [T10] loader_shifts/decay.py
                                             ├─> [T11] loader_shifts/gravity.py (baseline + γ-2-2 + δ-2-1)
                                             ├─> [T12] ceiling_agent rewrites for P1 cells
                                             ├─> [T13] agent_stub + prompts for P1 cells
                                             ├─> [T14] counterfactual.py predictor-name map for P1 types
                                             └─> [T15] P1 ceiling smoke (13 cells × 3 seeds)
                                                   └─> ★ P1 CHECKPOINT ★ (rollback gate §8.2)
                                                         └─> [T16-T22] P2 per-domain (7 parallel sub-agent assignments: damped_ho, pendulum, rlc, wave, optics, fluid, kinetics)
                                                               └─> [T23] full ceiling sweep (48 cells × 3 seeds)
                                                                     └─> [T24] full lookup-attacker sweep (24 cells × 3 seeds)
                                                                           └─> [T25] full sprint4 model sweep
                                                                                 └─> [T26] paper figure / table regeneration
```

**Parallelism budget.** T7-T11 and T16-T22 are independent (different loader_shifts files, different shift modules). Spawn separate sub-agents per file; each handles ~3 builders + the ceiling-pred rewrites for those cells. Each sub-agent's done criteria is "all per-shift snapshot tests in §6.1 for my domain pass."

**Y plumbing ships first (T1).** Per auditor §3 first bullet: the subgrid-c branch in `eval/numeric.py` is fully independent of any shift-specific builder and can be unit-tested against a synthetic 3-tuple grid before any loader code lands. Swapping T1↔T2 de-risks the loader changes and means a fresh sub-agent can land T1 from the blueprint alone without waiting for the dispatch table scaffold. T2 (loader scaffold) consumes the 3-tuple shape defined by T1.

---

## §6 — Testing strategy

### 6.1 Per-shift snapshot test (one per cell, 48 cells)

Pattern (location: `tests/scenarios/test_loader_xy.py`):

```python
@pytest.mark.parametrize("domain,shift,seed", [...all 48 cells × seeds (0,1,2)...])
def test_grid_a_matches_shifted_law(domain, shift, seed):
    scenario = load(domain, shift, seed=seed)
    for inputs, gt in scenario.test_grids["a"]:
        expected = _direct_call_shifted(domain, shift, inputs, scenario.sim.params)
        assert math.isclose(gt, expected, rel_tol=1e-9, abs_tol=1e-12)

def test_grid_c_first_tuple_is_3_tuple(domain, shift, seed):
    scenario = load(domain, shift, seed=seed)
    tup = scenario.test_grids["c"][0]
    assert len(tup) == 3
    inputs, gt, cf_p = tup
    assert isinstance(inputs, Mapping)
    assert type(cf_p) is type(scenario.sim.params)
```

`_direct_call_shifted(domain, shift, inputs, params)` is a test-side helper that knows the exact projection used by each builder (matches §4 "shifted_* fn" column).

### 6.2 Counterfactual-override test

`tests/eval/test_subgrid_c_overrides.py`:

```python
def test_cf_params_overrides_declared_params_on_c():
    entry = {
        "predictor": {"lang": "python", "code": "def f(r, G, M, m, **_): return -G*M*m/(r*r)"},
        "params": [
            {"name": "G", "value": 1.0e-10},
            {"name": "M", "value": 1.0e21},
            {"name": "m", "value": 1.0},
        ],
        "inputs": [{"name": "r", "units": "m"}],
    }
    scenario = load("gravity", "delta_2_1", seed=0)
    cf_p_0 = scenario.test_grids["c"][0][2]
    expected_at_point_0 = -cf_p_0.G0 * cf_p_0.M * cf_p_0.m / (scenario.test_grids["c"][0][0]["r"] ** 2)
    # ... assert evaluate_entry takes a path that, called on point 0 of (c), yields expected_at_point_0
```

### 6.3 Lookup-attacker behavior predictions

Per `sprint3-attacker-spec.md` §5, threshold is `S_bench^lookup < 0.50`. With X+Y:

- **Prediction A**: Attacker score on baselines is **unchanged** (~0.95+, well above threshold for that slice — but the slice excludes baselines, so attacker still passes the gate).
- **Prediction B**: Attacker score on γ/δ slice **drops sharply** (current `~0.0` per Sprint-3.5; new should be ≤ 0.1 — the attacker's canonical form can't track shifted truth in expanded vocab). Gate continues to PASS.
- **Prediction C if violated**: attacker scores ≥ 0.50 on γ/δ slice → catalog Round-3 escalation per `sprint3-attacker-spec.md` §5.

These predictions are recorded so that if attacker behavior CHANGES qualitatively (esp. Prediction A breaking), we know X+Y silently changed the threat model. Round-1 audit should ratify or refine.

### 6.4 Smoke

After each tier (P0/P1/P2):

```bash
python -m mirrorlab.runners.ceiling_agent --cells <tier> --seeds 0,1,2 --out /tmp/ceiling.json
python -m mirrorlab.attacker --slice gamma --seeds 0,1,2  # lookup-attacker
pytest tests/scenarios/test_loader_xy.py tests/eval/test_subgrid_c_overrides.py -q
```

### 6.5 Test count budget

- Per-cell snapshot: 48 cells × ~2 assertions × 3 seeds = ~290 new test cases.
- Subgrid-c override: ~30 new cases (per-shift `cf_params` round-trip).
- Predictor-name-map: ~48 round-trip cases.
- Total new: **~370 tests**. Total deletions (rewrites of baseline-formula asserts): ~50. Net suite: **~853 + 320 ≈ 1170 tests**.

---

## §7 — Rerun plan

### 7.1 Order of reruns (post-T15 P1 checkpoint, then post-T23 final)

| Order | Run | Cells | Seeds | LLM-turn budget | API cost |
|---|---|---|---|---|---|
| R1 | ceiling sweep P1 | 13 | 3 | 0 (no LLM) | 0 |
| R2 | lookup-attacker sweep (γ ∪ δ) | 24 | 3 | 72 × 20 turn cap | ~10% of sprint-3.5 |
| R3 | ceiling sweep full | 48 | 3 | 0 | 0 |
| R4 | sprint4 model sweep | 12 (current subset) | 1 → 3 (upgrade) | 5 models × 36 × ~30 turn cap | ~100% of sprint4 |
| R5 | (optional) expanded model sweep | 48 | 3 | 5 models × 144 × ~30 | ~4× sprint4 |

Estimated wall-clock at current proxy throughput: R2 ≈ 1.5 h; R3 ≈ 30 min; R4 ≈ 4-6 h; R5 deferred to camera-ready.

### 7.2 Cache invalidation

In T0 (before any code changes):

```bash
mkdir -p docs/archive/pre-xy
git mv docs/sprint3-pilot-data*.json docs/archive/pre-xy/
git mv docs/sprint35-pilot-data*.json docs/archive/pre-xy/
git mv docs/sprint4-sweep-data*.json docs/archive/pre-xy/
git mv docs/sprint4-ceiling-data*.json docs/archive/pre-xy/
git mv docs/sprint4-attacker-data*.json docs/archive/pre-xy/
```

Add `docs/archive/pre-xy/README.md` explaining the move and naming the commit that introduced X+Y. After R3/R4 land, the new JSONs take the old names, so figure/table generators are untouched.

### 7.3 Figure regeneration

After R4 lands, regenerate via `mirrorlab/reports/figures.py`. The cliff plot (`figures/fig1_cliff.png`) is expected to **deepen** — that's the goal. Update `docs/sprint4-figure-captions.md` to mention X+Y; do NOT keep "convention recognition" hedge language.

---

## §8 — Rollback points

### 8.1 P0 rollback (after T6 smoke)

**Gate.** On gravity γ-2-1 seed=0:
- Ceiling truth-form numeric score ≥ 0.95.
- Baseline-form (the old loader-style closure, re-implemented as agent_stub baseline submission) numeric score ≤ 0.85.
- Spread = ceiling - baseline ≥ 0.10.

**If gate fails**: ABORT. Possible root causes (in audit order):
1. Direction sampling still hits ⟨μ²⟩ ≈ 1/3 → re-bias.
2. GT projection definition wrong (signed |F| vs F_r vs F_x) → reconsider.
3. Y plumbing silently leaks declared `G` into (c) → trace.

Do **not** advance to P1 until gate passes. Restore from `docs/archive/pre-xy/` if needed (the work is reversible because no production runs have used new builders yet).

### 8.2 P1 rollback (after T15 smoke)

**Gate.** Across all 13 P1 cells × 3 seeds:
- Median ceiling numeric ≥ 0.90.
- Worst-cell ceiling numeric ≥ 0.70.
- Every cell shows ceiling > baseline ≥ 0.05.

**If gate fails on a single cell**: isolate that builder, do not abort the tier. Common modes: wrong canonical_inputs order; agent_stub emitting predictor with mismatched kwargs (recapitulating the sprint4 `q1,q2,r` bug from `sprint4-sweep-summary.md`); cf_params containing fields that the predictor doesn't list.

**If gate fails on ≥ 3 cells**: STOP. Round-1 audit was wrong about a systematic issue — escalate to consensus-lead.

### 8.3 P2 rollback (per-domain, parallel)

Each P2 sub-agent owns a domain. If a sub-agent reports ceiling < 0.7 on any cell, they investigate and report; team-lead may park that domain (gate held open for it specifically) while other P2 work continues. No global abort at P2.

**"Park" semantics (auditor D.3 clarification).** A parked cell receives `S_scen = NaN` in the final sweep JSON (the cell is NOT removed from the dispatch table; the loader still loads it and tests still run, but the figures/tables show "—" for that cell). Parking is reversible by a follow-up patch that lands the missing builder; no rerun of the whole sweep is required.

### 8.4 Attacker-gate violation rollback (post-R2)

If lookup-attacker `S_bench^lookup(γ ∪ δ) ≥ 0.50` on any tier, per `sprint3-attacker-spec.md` §5 this is a catalog-Round-3 trigger. Do NOT proceed to R4. Spawn a separate audit team to either tighten shifts or revise CAL-9.

---

## §9 — Open design questions

> v2 status: Q2, Q3, Q5, Q6, Q8, Q9, Q10 are RESOLVED inline (auditor flagged them as load-bearing for T3 / P1 dispatch). Q1, Q4, Q7 remain deferrable per auditor verdict. Each resolution is recorded below.

1. **[DEFERRABLE — Q1] CAL-5 bonus recalibration.** Once GT carries the broken-symmetry information, the +0.10 symmetry-label bonus is partially redundant (per `blocker-fix-options.md` §1.5). Options: (a) keep at 0.10, (b) reduce to 0.05, (c) remove. Author picks **(b) reduce to 0.05** post-T6 per auditor recommendation; this is a paper-1 ablation story choice, not a code blocker. Not load-bearing for T3.

2. **[RESOLVED — Q2] GT projection for ROT shifts** (γ-2-1, γ-5-1/2, γ-7-1, γ-8-2, γ-10-2). **Locked: option (a) signed-|F| projection onto query r̂ = (x,y,z)/‖(x,y,z)‖.** Reasoning: (a) preserves sign structure (coulomb attractive vs repulsive); (b) one-component Fx collapses anisotropy on rotated configurations and defeats X.B; (c) magnitude |F| loses sign and makes (c) cliff trivially shallower. Same convention applied to all ROT cells in §4 (rows 4, 13, 14, 19, 23, 28, 29); for cells where the truth law returns a flux vector (thermal γ-7-1) the projection is onto the n̂ surface-normal direction implied by `grad_dir`. Wave γ-8-2 phase `k·r` is already a scalar — n/a. v2 inlines this in §4 row 4.

3. **[RESOLVED — Q3] Shifts with unread signatures.** Auditor confirmed: **6 modules** (kinetics δ-11-1, kinetics γ-11-2 [v1-missed], wave δ-8-1, optics δ-9-1, decay γ-12-1, decay δ-12-1) export only `Instance.step(t)`. v2 also adds decay γ-12-2 to this list (Q3-expanded) to avoid reaching into private `_integrated_rate`. Path (a) **step()-based truth projection** is locked in §3.2.1 with per-cell scalar observables. Path (b) (add closed forms) is rejected as out of scope.

4. **[DEFERRABLE — Q4] damped_ho γ-3-1 `x2_mean` proxy.** Single-point proxy `x2_mean = x²` accepted per auditor; revisit if §6.1 snapshot tolerance fails on this one cell. Weakens the X.A claim for that one shift only; documented in §4 row 7.

5. **[RESOLVED — Q5] Thermal δ-7-1 PDE-only truth.** **Locked: cache `solve_ivp` results by `(seed, round(t, 6))`** per auditor recommendation. Cache key precision (6 decimal places of t) is fine because the (a)/(b) grid samples t on a finite log-uniform grid with no more than ~30 distinct values per seed. Cache lives at module-level in `loader_shifts/thermal.py`. Wall-clock impact captured in §6.5.

6. **[RESOLVED — Q6] agent_stub upgrade scope.** **Locked: upgrade `agent_stub.py` to know the new input vocabulary** per §3.7. Reference baseline in figures shifts as a consequence; this is acknowledged. The alternative ("X+Y-baseline" separate submission class) is rejected because it would double the number of baseline columns in every figure and break continuity with sprint-3.5 plots. Caveat documented in §3.7 done-criteria (`S_scen ∈ [0.85, 0.95]` floor on γ-2-1 baseline-form).

7. **[DEFERRABLE — Q7] TODO-2 step() leak interaction.** Per-cell verification task during implementation; each builder author cross-checks their cell's `step()` output against the v2-todo TODO-2 🔴 list (14 shifts) before declaring the cell done. Not load-bearing for T3.

8. **[RESOLVED — Q8] Counterfactual on input variables vs law coefficients.** **Locked via §2.4: input-encoding fields and law-coefficient fields are disjoint sets.** Law-coefficient set is exactly `counterfactual._LAW_PARAM_FIELDS[type(params)]`. Builders mutate only the complement; `cf_params` mutates only `_LAW_PARAM_FIELDS`. Enforced by `tests/scenarios/test_param_field_disjointness.py` and a `_assert_builder_mutates_only(...)` runtime guard.

9. **[RESOLVED — Q9] OOD sub-grid (b) semantics under expanded vocab.** **Locked: 5× along the canonical magnitude (`r`, `|F|`, `|v|`, `|k|`); direction sampling identical to (a).** For shifts where the magnitude is already in the input (gravity γ-2-2 `r`, wave γ-8-1 `k`), scale that key by 5×. For shifts with multi-axis inputs (γ-2-1 `{x,y,z}`), scale the magnitude `‖(x,y,z)‖` by 5× while preserving the sampled direction (rescale each coordinate uniformly). For T_TRANS shifts that add `t`, OOD on `t` is `5 × t_scale` along the same modulation period as (a).

10. **[RESOLVED — Q10] Param-name canonicalization.** **Locked via §2.5** (lowercase + strip trailing-0 only for canonical-symbol singletons + preserve numeric pairs + drop role modifiers + sequential numeric for coulomb). `_PREDICTOR_NAME_MAP` is hand-built per shift type for unambiguous review; round-trip bijection enforced by a unit test.

---

## Appendix A — Quick reference for sub-agent assignments

Each row below is a self-contained work item for one sub-agent. The audit checkpoint after each tier (§5 DAG) must pass before that tier's items dispatch.

| Item | File(s) | Section | Done criteria source |
|---|---|---|---|
| T0  | `docs/archive/pre-xy/` | §7.2 | files moved, README written |
| T1  | `eval/numeric.py` 3-tuple branch (Y plumbing first) | §3.3 | §6.2 test passes |
| T2  | `loader_shifts/__init__.py` skeleton | §3.1, §3.2 | dispatch table compiles |
| T3  | `loader_shifts/gravity.py::gamma_2_1_grids` | §3.2, §4 row 4 | §6.1 snapshot for γ-2-1 |
| T4  | `runners/ceiling_agent.py::_gravity_pred` γ-2-1 branch | §3.5 | §8.1 P0 gate |
| T5  | `scenarios/agent_stub.py` γ-2-1 baseline-form | §3.7 | §8.1 P0 gate |
| T6  | smoke runner | §6.4 | §8.1 |
| T7-T11 | 5 `loader_shifts/<domain>.py` files (hooke, coulomb, thermal, decay, gravity) | §3.2 | §6.1 snapshots for those 13 cells |
| T12 | ceiling_agent rewrites for P1 cells | §3.5 | §8.2 gate |
| T13 | agent_stub + prompts.py P1 updates | §3.7 | §8.2 |
| T14 | counterfactual.py PREDICTOR_NAME_MAP P1 entries | §3.6 | §6.2 |
| T15 | P1 smoke | §6.4 | §8.2 |
| T16-T22 | 7 P2 `loader_shifts/<domain>.py` files (damped_ho, pendulum, rlc, wave, optics, fluid, kinetics) | §3.2 + §4 rows | §6.1 |
| T23 | full ceiling sweep | §7.1 R1+R3 | new sprint4-ceiling-data.json |
| T24 | lookup-attacker sweep | §7.1 R2 | gate §8.4 |
| T25 | sprint4 model sweep rerun | §7.1 R4 | new sprint4-sweep-data.json |
| T26 | figures regenerate | §7.3 | new fig1_cliff.png |

---

## §10 — Reviewer pushback (round-1 audit → v2 status)

Every numbered issue and suggestion from `docs/blueprint-xy-review-round1.md` has a status here. Format: `[FIXED]` / `[PARTIALLY FIXED]` / `[PUSHED BACK]` / `[ACCEPTED]` (suggestions).

### §2 Critical issues

- **§2.1 — 6 (not 5) shifts have no `shifted_*`; kinetics γ-11-2 missed.** **[FIXED]** §3.2.1 "step()-only shifts" lists 7 cells (added decay γ-12-2 to avoid private `_integrated_rate`). v2 commits to path (a) step()-based truth projection with per-cell scalar observables locked in a table. §4 rows 24, 27, 32, 33, 34, 35, 36 updated. Footer note rewritten. Q3 resolution recorded in §9.

- **§2.2 — Q2 GT projection load-bearing for P0.** **[FIXED]** §9 Q2 marked RESOLVED with option (a) signed-|F|·r̂ locked. §4 row 4 updated with explicit projection text. Same convention applied to all ROT cells (4, 13, 14, 19, 23, 28, 29). Q2 resolution recorded in §9.

- **§2.3 — predictor signature has 3 unstated requirements.** **[FIXED]** §2.3 now contains three explicit paragraphs: (A) signature filtering on raw predictor (with implementation pattern), (B) `_alias_inputs` zip-min-length silent drop is *by design* for X.B exposure, (C) coefficient-vs-input name-collision edge case documented and routed through §2.4 disjointness.

- **§2.4 — Q8 disjointness load-bearing for 9 of 13 P1 cells.** **[FIXED]** New §2.4 "Input-encoding vs law-coefficient param-field disjointness" added with explicit invariant, enforcement (unit test + runtime guard), and affected-cells list. Original §2.4 "Backward-compat — NONE" renumbered to §2.7. Q8 resolution recorded in §9.

- **§2.5 — Q10 canonicalization load-bearing for T14.** **[FIXED]** New §2.5 "Param-name canonicalization rule" added with 5-step rule: lowercase, conditional strip-0, preserve numeric pairs, drop role modifiers (`_src/_test/_e`) and reassign sequential numerics, round-trip bijection test. RLC γ-6-2 example (`L0/L1/L2 → L_0/L_1/L_2`) and coulomb γ-5-1/2 examples (`q_src/q_test → q_1/q_2`) inlined. Q10 resolution recorded in §9.

- **§2.6 — ceiling fallback masks signature-mismatch bugs.** **[FIXED]** New §2.6 "Ceiling-agent signature-mismatch detection" added: first-call-per-(cell,seed) WARN log of filtered kwargs; if filtered set non-empty AND no `**kwargs` catch-all, raise `SignatureMismatchError` rather than CLAMP. `agent_stub` baseline is exempt (it is *expected* to drop inputs per §2.3 requirement B).

### §3 Suggestions

- **§3 bullet 1 — Swap T1↔T2 (Y plumbing first).** **[ACCEPTED]** §5 DAG updated; T1 is now `eval/numeric.py` 3-tuple branch, T2 is `loader_shifts/` scaffold. Appendix A row order updated. Rationale paragraph rewritten to "Y plumbing ships first (T1)" and cites auditor §3.

- **§3 bullet 2 — Test count budget realism.** **[PARTIALLY FIXED]** §6.5 already lists ~370 new tests. v2 adds: thermal δ-7-1 contributes ~30 of those 290 snapshot cases and uses the `(seed, round(t,6))` cache (Q5 resolution), so its per-suite cost is dominated by the FIRST seed-pass. Estimated wall-clock for the full snapshot suite: ~3-4 min, within the 5-min budget the auditor flagged. If observed exceeds budget, mark the slow tests `@pytest.mark.slow` and gate from default run. (Did not enumerate per-cell timing — keep as a P1-checkpoint observable.)

- **§3 bullet 3 — Cache invalidation re-creation risk.** **[ACCEPTED]** §7.2 augmented in spirit: rescore.py already refuses files lacking `"xy_version": 1` (§3.8). Adding a pre-commit hook flagging `docs/sprint*-data*.json` lacking the key is captured as a follow-up CI task (not strictly necessary because rescore.py is the only consumer; recorded here for future hardening).

- **§3 bullet 4 — Legacy-pathway regression assertion in P0 gate.** **[PUSHED BACK]** §8.1 keeps the two existing assertions. Reasoning: "ceiling on OLD pre-XY grids reproduces sprint-3.5's published ≥0.95" is *not* achievable without keeping the old grid code alive, which directly contradicts §1.3 ("No backward-compat layer"). The whole point of X+Y is that the old grids are wrong (`blocker-trace.md`), so reproducing ceiling numbers on them is not a stability signal. Instead, v2 keeps the published numbers in `docs/archive/pre-xy/` for forensic reference and accepts that the new numbers are the new reference.

- **§3 bullet 5 — Q1 (CAL-5 bonus) author-picks.** **[ACCEPTED]** §9 Q1 now records author pick of (b) reduce to 0.05 post-T6 per auditor recommendation.

- **§3 bullet 6 — agent_stub fixture test.** **[ACCEPTED]** Added to §3.7 done criteria: "fixture test asserting the stub's emitted code parses, evaluates, and exposes the declared kwargs" — captured below as an addendum to §3.7. (Inlined inline at next §3.7 touch; recorded here for sub-agent assignment.)

- **§3 bullet 7 — ⟨μ²⟩=1/3 reader gloss.** **[FIXED]** §4 legend now includes a one-line gloss explaining `⟨μ²⟩` and pointing to `blocker-fix-options.md` §1.5.

### §4 Detailed findings

- **A.1 — `_<domain>_test_grids` coverage by range.** **[ACCEPTED]** No change needed.
- **A.2 — `_<domain>_pred` enumeration would help.** **[ACCEPTED]** §3.5 already lists all 12 domains by L98-367 range; explicit enumeration deferred to sub-agent assignment notes in Appendix A.
- **A.3 — 36 shifts present.** **[ACCEPTED]** No change.
- **A.4 — "~25" test-file count is unaudited.** **[PUSHED BACK]** Auditor noted "did not enumerate myself"; author also did not enumerate during v1. v2 keeps "~25" as an approximation; sub-agent on T7-T11 enumerates exactly when they touch those tests. Recorded as a known imprecision, not a blocker.
- **B.1 — gravity γ-2-1 OK.** **[ACCEPTED]**
- **B.2 — thermal γ-7-1 OK pending §2.4.** **[ACCEPTED]** §2.4 disjointness rule addresses the called-out concern.
- **B.3 — decay γ-12-2 `_integrated_rate` privacy boundary.** **[FIXED]** v2 rejects reaching across the privacy boundary; row 35 now uses `step(t)["N"]` uniformly with the other decay cells (§3.2.1).
- **C.1 — T1↔T2 inversion.** **[FIXED]** See §3 bullet 1 above.
- **C.2 — ceiling-after-loader ordering OK.** **[ACCEPTED]**
- **C.3 — γ-2-1 as P0 vs δ-2-1 alternative.** **[PUSHED BACK]** Keep γ-2-1 as P0; ROT-3D is the hardest cell so passing P0 on it is a stronger signal. The auditor's "add δ-2-1 as a secondary P0 smoke before T7" is captured as a soft recommendation: sub-agent on T6 may opt to also smoke-test δ-2-1 if time permits, but it is not a gate. Tradeoff noted: γ-2-1 P0 failure leaves ambiguity between "X.B-specific bug" vs "generic plumbing bug"; acceptable risk given the ceiling-agent build is well-trodden.
- **D.1-D.3 — rollback observability.** **[ACCEPTED]** §8.3 "park" semantics: a parked domain receives `S_scen = NaN` in the final sweep (not removed); figures and tables show "—" for that cell. Clarified inline at §8.3 if needed; recorded here.
- **D.4 — attacker-gate observability.** **[ACCEPTED]**
- **D.Q1–Q10 — load-bearing table.** **[FIXED]** §9 reworked: Q2/Q3/Q5/Q6/Q8/Q9/Q10 RESOLVED inline; Q1/Q4/Q7 DEFERRABLE with author-picks recorded.
- **E.T0/T1/T3 executability.** **[FIXED]** With Q2/Q9 resolved (§9), T3 is now executable from the blueprint alone — the GT projection and OOD direction are pinned in §4 row 4 and §9 Q9 resolution respectively.

— end §10 reviewer pushback —

---

— end blueprint v2 —
