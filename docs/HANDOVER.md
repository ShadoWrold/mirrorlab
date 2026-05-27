# MirrorLab Handover Document

> **Purpose**: Bring a new AI assistant up to speed on the MirrorLab research program. Read this before doing anything.
>
> **Reading order**: §1 → §2 → §3 → §4 → §5 → §6 → skim others.
>
> **Last update**: 2026-05-27 (post-T23) by Claude Opus 4.7

---

## 1. What MirrorLab Is (60 seconds)

A research program with **3 planned papers**, organized under GitHub org [ShadoWrold](https://github.com/ShadoWrold) (typo intentional — "shifted spelling" mirrors the project's shifted physics).

**Paper 1 (current focus)** — **MirrorLab**: a physics-discovery benchmark for LLM agents. We construct physics worlds where exactly one symmetry has been broken (γ-shifts) or one conservation law violated (δ-shifts). Frontier LLMs are scored on whether they can:
1. Discover the modified law from experiments
2. Submit predictions that survive **out-of-distribution** and **counterfactual** probe points

**Why this matters**: existing benchmarks (NewtonBench, PhysGym) only test β-type mutations (changed constants/exponents). γ/δ shifts are organized by **Noether's theorem** — each shift breaks exactly one symmetry, and the broken Noether charge is the smoking gun. We test whether LLMs can think *structurally* about physics, not just curve-fit.

**Paper 2** — Counterfactual diversity hypothesis (train physical world models on MirrorLab).
**Paper 3** — Symmetry recovery via physics-inductive world models.

**Bench status (2026-05-27, post-X+Y rebuild)**: the original Sprint-4 "TRUE PASS" was found to be a *plumbing pass*, not a *physics pass* — `loader.py` scored agent predictors against the **baseline-form law** (not the shifted law) for all 36 shifts, so a 1-D Newtonian closure could score 0.95+ on a 3-D anisotropic γ shift. The blocker is documented in `docs/blocker-{consensus,trace,physics,fix-options}.md`; the full rewrite plan lives in `docs/blueprint-xy.md` v2. The X+Y rebuild has **shipped through T23**: all 48 (domain, shift) cells × 3 seeds now score against truth-form GT with cf_params reaching the predictor on sub-grid (c). Headline numbers: ceiling overall median **0.992**, stub mean **0.617**, spread mean **+0.357**, **0 cells** below 0.70 floor.

---

## 2. Repository Map

```
mirrorlab/                            # ROOT
├── README.md                         # public-facing repo description (Sprint-4-era language)
├── paper1/                           # Paper 1 LaTeX manuscript (9-page draft, PRE-X+Y data)
│   ├── main.tex, appendix.tex, refs.bib, Makefile
│   └── main.pdf                      # builds clean but numbers are stale; T26 will regen
├── mirrorlab/                        # PYTHON PACKAGE
│   ├── domains/                      # 12 baseline physics simulators
│   ├── shifts/                       # 36 γ/δ shift implementations (= 12 × 3)
│   ├── scenarios/
│   │   ├── loader.py                 # entry point (now dispatches to loader_shifts/)
│   │   ├── loader_shifts/            # ★ X+Y per-(domain,shift) builders, 12 files
│   │   │   ├── _common.py            # _pack (3-tuple grid_c), _linspace_signed, ...
│   │   │   ├── {gravity,hooke,coulomb,thermal,decay}.py        # P1 domains
│   │   │   ├── {damped_ho,pendulum,rlc,wave,optics,fluid,kinetics}.py   # P2 domains
│   │   │   └── __init__.py           # 48-entry _GRID_BUILDERS dispatch table
│   │   ├── prompts.py                # 12 domain prompt templates (updated for new vocab)
│   │   ├── agent_stub.py             # rule-based baseline agent (T13 channel-harmonized)
│   │   ├── counterfactual.py         # ±30% latent-param perturbation
│   │   │                             # + _LAW_PARAM_FIELDS, _PREDICTOR_NAME_MAP,
│   │   │                             #   params_to_predictor_kwargs (X+Y additions)
│   │   └── registry.py               # (domain, shift) → SimInstance factory
│   ├── tools/                        # 32-tool MVS (measure/manipulate/analyze/knowledge)
│   │   ├── measure.py, manipulate.py, analyze.py, knowledge.py
│   │   ├── registry.py, sandbox.py   # multi-D bugs fixed in Sprint 4.5
│   ├── eval/                         # 2-stage evaluator (dim + numeric)
│   │   ├── dimensional.py
│   │   ├── numeric.py                # ★ subgrid-c branch: _eval_subgrid_c overrides
│   │   │                             #   declared params with per-point cf_params kwargs
│   │   └── scoring.py
│   ├── runners/
│   │   ├── openai_client.py          # OpenAI-format proxy (gpt-*) @ 127.0.0.1:4142
│   │   ├── anthropic_client.py       # Anthropic-format proxy (claude/gemini) @ 127.0.0.1:4141
│   │   ├── provider.py               # auto-dispatch by model name prefix
│   │   ├── llm_agent.py              # tool-calling loop w/ budgets
│   │   ├── ceiling_agent.py          # oracle ceiling — 12 _<domain>_pred dispatchers
│   │   │                             #   rewritten for X+Y (T4, T12, T16-T22)
│   │   ├── t23_ceiling_sweep.py      # ★ NEW: 48 cells × 3 seeds, writes docs/ceiling-data.json
│   │   ├── sprint{1,2,3,3_5,4}_*.py  # legacy sprint runners (sprint4_sweep still used for T25)
│   │   ├── rescore.py                # version-guards on "xy_version: 1"
│   ├── attacker/                     # lookup-attacker (spec §8) — locked prompt v1.1
│   │   ├── lookup.py, runner.py, cli.py
│   ├── calibration/sweep.py          # CAL-N knob sweeps
│   └── reports/figures.py            # paper figures generator (will be re-run at T26)
├── vendor/newtonbench/               # git submodule (HKUST-KnowComp/NewtonBench)
├── tests/                            # pytest suite (~853 tests pre-X+Y; ~+8 P1/P2 gates)
│   ├── catalog/                      # 36 per-shift tests
│   ├── scenarios/, tools/, eval/, attacker/, calibration/
│   ├── runners/
│   │   ├── test_p0_gravity_g_2_1_smoke.py        # X+Y T5/T6 P0 gate
│   │   ├── test_p1_{coulomb,decay,gravity_rest,hooke,thermal}_smoke.py
│   │   ├── test_p1_sweep_acceptance.py            # 20 cells × 3 seeds = 60 (P1 §8.2 gate)
│   │   └── test_p2_sweep_acceptance.py            # 28 cells × 3 seeds = 84 (P2 §8.3 gate)
│   ├── reports/, integration/
├── figures/                          # paper-grade PDFs + PNGs (pre-X+Y data; T26 regen pending)
├── docs/
│   ├── HANDOVER.md                   # ← this file
│   ├── blueprint-xy.md               # ★ X+Y master plan v2 (SHIP-approved); SOURCE OF TRUTH
│   ├── blueprint-xy-review-round{1,2}.md   # audit trail
│   ├── blocker-{consensus,trace,physics,fix-options}.md  # why X+Y exists
│   ├── ceiling-data.json             # ★ T23 output (xy_version: 1, 144 rows / 48 cells)
│   ├── archive/pre-xy/               # all pre-X+Y JSONs (sprint3/3.5/4 + old ceiling)
│   ├── program-overview.md           # 3-paper program (PI / collaborator view)
│   ├── story.md                      # plain-English 500-word story
│   ├── paper1-spec.md                # Paper 1 implementation spec
│   ├── d6-shift-catalog.md           # 36 shifts, post-audit Round-2 final
│   ├── audits/                       # 36 per-shift human-review markdowns
│   ├── sprint{1,2,3,3_5,4}-report.md # per-sprint verdicts (Sprint-4 superseded by X+Y)
│   └── v2-todo.md                    # carry-over fixes deferred to v2
└── pyproject.toml
```

---

## 3. Sprint History (timeline, what was achieved)

| Sprint | Goal | Outcome |
|---|---|---|
| **1** | sim + agent loop + scoring (Hooke + γ-1-1 only) | PASS |
| **2** | 12 domains + 36 shifts + 32 tools | PASS, 331/331 tests |
| **3** | LLM runner + lookup-attacker + first pilot | CONDITIONAL PASS — pipeline OK, 0/5 honest cells submitted (budget-prompt mismatch) |
| **3.5** | Fix budget contract + retry pilot | TRUE PASS — 4/5 honest cells submit, attacker `S_bench^lookup = 0.0` non-vacuous |
| **4** | 5-model × 4-domain × 3-tier sweep + ceiling + figures + paper draft | TRUE PASS (later **invalidated** — see X+Y blocker) |
| **4.5** | Audit findings: step() leaks, sampler/validator hardening, multi-D tool bugs | DONE in commit `675e7b7`, `34ea738` |
| **X+Y** | Full bench rebuild after blocker (`loader.py` scored against baseline-form GT) | **In progress, T0 → T23 shipped**; T24 / T25 / T26 pending |

### X+Y task-by-task (commits)

| Task | Commit | What |
|---|---|---|
| BLOCKER consensus + blueprint v2 | `04fe986` | Spec frozen |
| T0  | `fbcdab7` | Archived 7 pre-XY JSONs to `docs/archive/pre-xy/` |
| T1  | `b41e0a0` | Y plumbing — `numeric._eval_subgrid_c` overrides declared params with cf_params |
| T2  | `36ac395` | `loader_shifts/` scaffold + 48-entry dispatch |
| T3  | `c79d94c` | gravity γ-2-1 truth-form builder (P0) |
| T4  | `9785721` | ceiling γ-2-1 truth predictor |
| T5/T6 | `35b2645` | End-to-end ceiling > baseline-stub smoke (P0 gate) |
| T7  | `79c6d14` | hooke loader_shifts (4 cells) |
| T8  | `b43214e` | coulomb loader_shifts (4 cells) |
| T9  | `821ea4d` | thermal loader_shifts (4 cells) |
| T10 | `8a8734a` | decay loader_shifts (4 cells) |
| T11 | `01abb34` | gravity rest (baseline + γ-2-2 + δ-2-1) |
| T12-mini + T15 | `193bf76` | decay stub fix + P1 sweep acceptance gate |
| T16-T18 (P2 A) | `7a64fb6` | damped_ho + pendulum + optics truth-form |
| T19-T22 (P2 B) | `3cb0449` | fluid + rlc + wave + kinetics truth-form + P2 sweep gate |
| T13 | `35d5924` | Stub channel harmonization (pendulum/rlc/wave/kinetics) |
| **T23** | **`c3ebbb9`** | **Full 48-cell × 3-seed ceiling + stub sweep → new `docs/ceiling-data.json`** |

---

## 4. T23 Result Summary (2026-05-27)

**Runner**: `python3 -m mirrorlab.runners.t23_ceiling_sweep --out docs/ceiling-data.json --quiet`
**Wall-clock**: 165.5 s, zero LLM calls.

| Metric | Value | Gate (§8.2 / §8.3) |
|---|---|---|
| Rows / cells / seeds | 144 / 48 / 3 | — |
| Errors | **0** | — |
| Ceiling overall median | **0.992** | ≥ 0.90 ✓ |
| Ceiling mean | 0.974 | — |
| Stub mean | 0.617 | — |
| Spread mean | **+0.357** | — |
| Spread median | +0.116 | — |
| Cells with min ceiling < 0.70 | **0** | ≥ 0.70 ✓ |
| Truth ≥ baseline on every (cell,seed) | True | ✓ |

**Top spread cliffs (X+Y working as intended)**:
- `optics/δ-9-1`, `coulomb/δ-5-1`, `optics/γ-9-2`, `coulomb/γ-5-2` → all ≈ **+1.00**
- `gravity/γ-2-1` +0.9998, `rlc/γ-6-2` +0.9998, `thermal/δ-7-1` +0.9985
- `pendulum/δ-4-1` +0.9907, `fluid/γ-10-1` +0.9788

The cliff cells confirm X.B input-vocabulary expansion (3-D coords for ROT, `t` for T_TRANS) is now exposing what stub canonical-law fits cannot.

**Soft cells (small spread by physics, not by bug)**: enumerated in `tests/runners/test_p{1,2}_sweep_acceptance.py::_P{1,2}_SOFT_CELLS`. Baselines all 0 by construction (stub IS the canonical law).

---

## 5. Conventions & Codified Rules

### 5.1 step() leak severity rule (codified 2026-05-27 during δ-1-1 audit)

> A `step()` output key is a 🔴 leak iff: **(a) the key is a derived quantity that the shift's broken-symmetry directly manifests in, AND (b) the baseline domain's `step()` does not include that key**.

Fixed in Sprint 4.5 (commit `34ea738`); cross-checked again during X+Y per-cell builder authoring.

### 5.2 X+Y data-format contract

All post-X+Y sweep JSONs MUST have top-level key `"xy_version": 1`. `mirrorlab/runners/rescore.py` refuses files lacking it. Pre-XY JSONs are quarantined under `docs/archive/pre-xy/`.

`docs/ceiling-data.json` schema (T23 output):
```
{
  "xy_version": 1,
  "schema": "ceiling+stub per (domain,shift,seed)",
  "elapsed_s": <float>,
  "summary": { n_rows, n_errors, n_cells,
               ceiling_overall_median, ceiling_mean,
               stub_mean, spread_mean, spread_median,
               worst_cells_below_0_7 },
  "rows": [ { domain_id, shift_id, seed,
              s_scen_ceiling, s_scen_stub, spread, error }, ... ]
}
```

`mirrorlab/reports/figures.py` consumes the **legacy `rows[i].s_scen`** shape (pre-X+Y `docs/ceiling-data.json`). For T26 it needs a tiny adapter: read `s_scen_ceiling` instead. Either patch figures.py or write `s_scen` as an alias in T23 output — defer to T26 implementer.

### 5.3 Disjointness invariant (blueprint §2.4)

For every shift Params dataclass:
- **Law-coefficient fields**: exactly `counterfactual._LAW_PARAM_FIELDS[type(params)]`. Mutated ONLY by `cf_params` on sub-grid (c). Forbidden for builders to mutate per grid point.
- **Input-encoding fields**: complement. Mutated freely by builders per grid point. Forbidden for `cf_params` to touch.

Enforced by `tests/scenarios/test_param_field_disjointness.py` (parametrized over all 36 shifts).

### 5.4 Predictor name-map (blueprint §2.5)

Shift-internal Params field names → predictor-facing kwarg names via `counterfactual._PREDICTOR_NAME_MAP`. Rules: lowercase + strip trailing `0` only for canonical singletons (`G0→G`, `lam0→lam`) + preserve numeric pairs (`L1→L_1`, `M01→M_01`) + sequential numeric for role modifiers (`q_src/q_test→q_1/q_2`).

Round-trip bijection enforced per type.

### 5.5 [CAL] placeholder convention

[CAL]-tagged values in spec are deliberately un-fixed placeholders.
- **Locked** (pre-X+Y): CAL-4 τ=0.35, CAL-7=30 (honest budget), CAL-8 K=20 (attacker), CAL-9 < 0.50 (attacker threshold)
- **CAL-5 (bonus)**: blueprint Q1 author-pick reduces to 0.05 post-X+Y; deferred until T25 numbers land
- **Deferred to camera-ready**: CAL-1 (sub-grid shares), CAL-3 (±30% counterfactual), CAL-10 (seeds per cell)

### 5.6 Provider routing

- `gpt-*`, `o3*`, `o4*` → OpenAI-format proxy at `127.0.0.1:4142/v1`, env `MIRRORLAB_LLM_API_KEY` (sk-cloudgpt-...)
- `claude-*`, `gemini-*` → Anthropic-format proxy at `127.0.0.1:4141`, key literal `"dummy"`
- Default model: `gpt-5.4-20260305` (bare `gpt-5.4` not on proxy)
- Known quirks: gpt-5.x rejects `tool_choice` + `max_tokens` (shim in `openai_client.OpenAIClient.chat` drops them only for gpt-5*); gpt-5.4 is 3× slower than gpt-4.1

### 5.7 Memory references

- `~/.claude/projects/-Data-tanh-phyLLM/memory/llm_api_endpoint.md` — proxy keys + model defaults
- `~/.claude/projects/-Data-tanh-phyLLM/memory/MEMORY.md` — index

These survive across Claude sessions. New AI may not have access — check the GitHub repo's docs/ as authoritative.

---

## 6. Active Work Queue (Next Steps)

In strict execution order. The next stop is **T24**.

### 6.1 T24 — lookup-attacker sweep (next up, requires LLM key)

**Goal**: regenerate `S_bench^lookup` on the γ∪δ slice under X+Y bench. Verify §8.4 gate `< 0.50`.

**Plan**:
- Cells: 24 (γ + δ across 12 domains, excluding baselines)
- Seeds: 3
- Turn cap: ~20 per run (locked-prompt attacker is one-shot in practice)
- Budget: ~72 runs × ~20 calls ≈ 1.5 k LLM calls, ~1.5 h wall-clock (blueprint §7.1 R2 estimate)
- **Model choice (user-approved 2026-05-27)**: `gpt-4.1` — attacker prompt is locked to "submit the textbook canonical law", so model strength is irrelevant; cheap model preserves budget.
- Runner: `mirrorlab/attacker/runner.py` exists; needs verification it writes `"xy_version": 1` header. If not, add adapter or new wrapper `t24_attacker_sweep.py` analogous to `t23_ceiling_sweep.py`.

**Gate predictions (blueprint §6.3)**:
- A: attacker score on baselines stays high (~0.95+) — gate excludes baselines, attacker passes anyway
- B: attacker score on γ/δ slice drops sharply (≤ 0.1) → §8.4 PASS
- C: if any γ/δ slice ≥ 0.50 → catalog Round-3 escalation, do NOT proceed to T25

**Output**: new `docs/sprint35-attacker-data.json` (or rename to `attacker-xy-data.json`) with `xy_version: 1`. Archive any old in-place file first via `git mv`.

### 6.2 T25 — Sprint-4 model sweep rerun (after T24, big LLM bill)

**Goal**: rebuild the cliff plot under X+Y bench so paper §6 numbers reflect truth-form scoring.

**Plan (user-approved 2026-05-27)**:
- **Cells: 12** (Sprint-4 subset for direct comparability with old `figures/fig1_cliff.png`)
- Domains: hooke / coulomb / thermal / decay (same 4 as Sprint-4)
- Models: 5 frontier (gpt-4.1, gpt-5.4, claude-*, gemini-*, plus one o-series — confirm with user before launching)
- Budget: 5 models × ~36 runs × ~30 turn ≈ tens-of-thousands of calls, 4-6 h wall-clock
- Runner: `mirrorlab/runners/sprint4_sweep.py` exists; `--out` default now writes to `docs/sprint4-sweep-data.json`. Verify it writes `"xy_version": 1`; if not, patch or wrap.

**Decision points to flag before launch**:
- Confirm 12-cell subset (vs full 48-cell R5)
- Confirm 5-model list (gpt-5.4 is 3× slower; sequence runs cheap→expensive so cliff signal lands early)
- Confirm CAL-5 bonus value (0.05 per blueprint Q1, or hold 0.10 until ablation)

### 6.3 T26 — Figures + paper data refresh (after T25, zero LLM)

**Goal**: regenerate `figures/fig1_cliff.png` + tables; update Paper 1 LaTeX.

**Plan**:
- Adapt `mirrorlab/reports/figures.py` to new T23 schema (`s_scen_ceiling` vs old `s_scen`)
- Regenerate all 6 paper figures
- Update `docs/sprint4-figure-captions.md` — remove "convention recognition" hedge, replace with X+Y framing
- Update Paper 1 §6 numbers from new sweep
- Update `docs/sprint4-report.md` → write `docs/x_y-sweep-report.md` superseder
- Footnote in paper §8 Limitations: T0-archived original sweep, X+Y rebuild summarized in HANDOVER §3-4

### 6.4 v2 backlog (camera-ready, weeks of work, none block T24-T26)

See [`docs/v2-todo.md`](v2-todo.md). Key items:
- **TODO-1**: IC randomization across 36 shifts
- **TODO-4**: timescale normalization (gravity M spans 4 orders → orbital period not visible)
- **TODO-5**: γ-2-2 1D→2D promotion to expose Bertrand precession
- Full 48-cell × 3-seed sweep (R5; T25 is 12-cell only)
- Multi-seed honest data for CAL-4 τ direction-lock confirmation

### 6.5 Paper 2 program (deferred)

Counterfactual diversity hypothesis. Train physical world models on MirrorLab. Auto-mode generator scaffolded but not wired.

---

## 7. Quick Verification Checklist (run before doing anything)

```bash
cd /Data/tanh/phyLLM
git log --oneline -10
# Should see c3ebbb9 (T23) at top.

git status                                        # should be clean
pytest -q tests/runners/test_p1_sweep_acceptance.py tests/runners/test_p2_sweep_acceptance.py
# 8 passed in ~155s. If any fail, the X+Y bench has regressed since T23.

python3 -c "import json; d=json.load(open('docs/ceiling-data.json')); \
            print('xy_version=', d.get('xy_version'), 'n_rows=', d['summary']['n_rows'], \
                  'median=', round(d['summary']['ceiling_overall_median'], 4))"
# Expect: xy_version=1 n_rows=144 median=0.9917
```

Sanity: if `docs/ceiling-data.json` has shape `{"summary": {...legacy...}, "rows": [{"s_scen": ...}]}` without `xy_version`, someone clobbered T23 — `git checkout c3ebbb9 -- docs/ceiling-data.json` to restore.

---

## 8. Team / Agent Conventions

This project uses delegation to agent teams when work is parallel. Each sprint had a team of 4-8 named agents (`physicist-A`, `sim-engineer`, `figure-maker`, etc.) coordinated via:

- `TeamCreate` / `TeamDelete` — one team per sprint
- `TaskCreate` / `TaskUpdate` — task list with `blockedBy` dependencies
- `SendMessage` — inter-agent comms (always by name, never UUID)
- `CronCreate(durable=true)` — 10-min polling for long-running sprints

When teams finish, **always shut down all teammates and `TeamDelete`** before starting a new sprint team. Lead can only manage one team at a time.

For non-sprint work (single-shot audits / fixes / linear sweeps like T23), `Agent(run_in_background=true)` or direct execution from the main session is fine without a formal team. T23 was done in main session because builders were already validated by P1/P2 acceptance tests.

T24 / T25 will run for hours under LLM load — use `Bash(run_in_background=true)` and check back, or set a `CronCreate` poll.

---

## 9. Conversational Style

User prefers:
- **Terse, declarative responses** in Chinese (with English technical terms inline)
- **Numbers, tables, severity badges** (🔴 / 🟡 / ✅) over prose
- **Honest negative findings flagged loudly** — never sugar-coat
- **Direct decision questions** when blocked, not open-ended brainstorming
- ≤25 words between tool calls during execution; final summaries can be longer
- **Always cite file:line when referencing code**

User is technically sophisticated — physics + ML background. Don't over-explain basics. Do explain non-obvious reasoning chains.

When code/spec violations are found, **upgrade severity by codified rule, not by gut feeling**.

---

## 10. Git / GitHub Discipline

- Remote: `origin → https://github.com/ShadoWrold/mirrorlab` (current org)
- Also: `personal → https://github.com/Tanhhhhtjy/phyLLM` (archived backup)
- Main branch: `main`
- Co-author tag on AI-generated commits: `Co-Authored-By: Claude Opus 4 (1M context) <noreply@anthropic.com>`
- **Never** commit secrets (API keys live only in env vars / memory files)
- Every X+Y task commits to `main` directly (no PR workflow)
- Commit message format: `Tn (tier): one-line subject` + body with what / why / test or data delta

---

## 11. Contact Points

- Repository: https://github.com/ShadoWrold/mirrorlab
- Org: https://github.com/ShadoWrold
- User GitHub: Tanhhhhtjy (er-huo)
- Email: tianjinyu@buaa.edu.cn (from org billing settings)

---

## Appendix A: Codified Acronyms

| Term | Meaning |
|---|---|
| γ-shift | structural symmetry break (e.g. ROT, PAR, SCALE) |
| δ-shift | conservation-law violation (e.g. E, L, Q) |
| Noether-paired | the conserved quantity uniquely associated with a continuous symmetry |
| god-tool | any closed-form symbolic-regression library (PySR, gplearn) that could "win" the bench by sheer fitting |
| ceiling oracle | agent that reads ground-truth law directly; used to prove bench is fair |
| lookup-attacker | LLM with locked prompt "submit the textbook canonical law"; used to prove bench resists textbook recall |
| OOD | out-of-distribution test point (training range × 5) |
| counterfactual | test point with shift's free parameters perturbed ±30% |
| CAL-N | [CAL]-tagged placeholder in spec §10, tuned during Sprint 3 |
| step() leak | derived quantity in `_Sim.step()` output that reveals the broken symmetry (forbidden post-Sprint 4.5) |
| X+Y | the full bench rebuild documented in `docs/blueprint-xy.md`: X.A = truth-form GT, X.B = expanded input vocab, Y = cf_params reach predictor on sub-grid (c) |
| P0 / P1 / P2 | X+Y rollout tiers: P0 = gravity γ-2-1 only; P1 = 5 domains (gravity/hooke/coulomb/thermal/decay); P2 = remaining 7 domains |
| Tn | X+Y task number from blueprint §5 DAG (T0 archive → T26 figures) |

---

## Appendix B: Pre-X+Y context (for archaeology)

The original Sprint-4 report and figures are intact for forensic comparison:
- `docs/sprint4-report.md` — TRUE PASS verdict on pre-X+Y bench (now superseded)
- `figures/fig1_cliff.png` — pre-X+Y cliff plot; T26 will overwrite with X+Y rebuild
- `docs/archive/pre-xy/*.json` — 7 invalidated sweep JSONs + 1 invalidated ceiling JSON

Do NOT trust pre-X+Y numbers in the README or paper draft until T26 lands. The README/paper still describe Sprint-4 results as headline; this is a known stale-language hazard.

— end of handover —
