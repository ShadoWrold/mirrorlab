# Paper 1 Spec — MirrorLab Benchmark v1

> Implementation blueprint for Paper 1 of the MirrorLab program.
> v0.1 draft, 2026-05-25. Source inputs: `d6-shift-catalog.md` (post-audit, 36/36 approved),
> `story.md`, `team-briefing.md` (D1–D7), `r1-physics-consistency.md`, `r5-elegant-defense.md`.
>
> Style: technical spec, executable, no marketing. Each section ≤ 1 screen. Placeholders that require empirical calibration are tagged **[CAL]** and re-collected in §10.

---

## 1. Scope & Non-goals

### In scope (v1, this paper)

- A physics-discovery benchmark targeting frontier LLM agents, organized around **one-symmetry-at-a-time** counterfactual shifts.
- 12 simulator domains × {baseline, γ-tier, δ-tier} scenarios, drawn from the **36-shift audited catalog** (`d6-shift-catalog.md`).
- One operating mode only: **Agent mode** — LLM-callable `measure` / `manipulate` / `analyze` / `knowledge` tools, JSON-schema interface, optional Python sandbox (D4).
- Tool-pool design (D3) with **within-scenario** persistence (D5 v1 restriction).
- Two-stage evaluator (dimensional pre-filter + numerical predictor test) with three test-point types (in-domain, OOD, counterfactual).
- Adversarial self-test: a lookup-style attacker agent that must score < 50 % before release (D6 R-1 mitigation).
- A first SOTA sweep over 5 frontier models (calibration of the headline "cliff" figure of `story.md`).

### Out of scope (Paper 2 / Paper 3 — hooks only)

- **Auto mode** procedural rollout API for world-model training. The simulator backend will be designed with a parallel `step(state, action) → state'` surface, but the rollout harness, dataset pipeline, and WM trainer ship in Paper 2.
- **Cross-scenario** skill library / persistence (full D5). v1 freezes the library at scenario boundaries; the on-disk format will be forward-compatible but cross-scenario reuse is *disabled*.
- **Conservation-law representation probing** (Paper 3). v1 only emits a binary "did the agent name the broken symmetry?" bonus signal — no internal-representation analysis.
- Closed-form symbolic equality oracle. v1 scores predictors numerically; symbolic equivalence checking (à la EGG-SR, R5 §1.3) is left to a future revision.

### Non-goals (will not ship in this program at all)

- Multi-modal physics (vision / video). MirrorLab is text+JSON only.
- Real-world experimental data. Everything is simulated; experimental ablations are limited to numerical perturbations of the simulator.

---

## 2. Architecture Overview

```mermaid
flowchart LR
    subgraph Bench[MirrorLab v1]
        SCEN[Scenario Loader<br/>= baseline + shift]
        SIM[Simulator Backend<br/>12 domains · NewtonBench-reuse]
        TOOL[Tool Pool<br/>measure/manipulate/analyze/knowledge]
        SBX[Python Sandbox<br/>optional, monitored]
        AG((Agent / LLM))
        SUB[Submission<br/>(formula, SI-dim, vars)]
        EVAL[Evaluator<br/>stage-1: dim · stage-2: numeric]
        SCORE[Scorer<br/>main + bonus]
    end

    SCEN --> SIM
    AG -- tool calls --> TOOL
    TOOL --> SIM
    AG -- python --> SBX
    SBX --> SIM
    AG -- final --> SUB
    SUB --> EVAL
    SIM -- ground-truth predictor --> EVAL
    EVAL --> SCORE
```

**Data flow** (one scenario):

1. `Scenario Loader` picks a `(domain, shift_id ∈ catalog ∪ {baseline})` pair, samples concrete parameters under the shift's documented preconditions, and produces a fresh sandboxed `SimInstance`.
2. The agent is given a **scenario prompt** (domain narrative, observable variables, available tool names) — *not* the shift label and *not* the formula family.
3. Agent issues tool calls; `SimInstance` returns measurements; the agent may use the Python sandbox for offline analysis with a token / wall-clock budget.
4. At `submit`, agent produces a **submission set** (§5).
5. Evaluator runs stage-1 (dimensional) then stage-2 (numerical) over a held-out test grid (§6).
6. Scorer aggregates per-scenario, then benchmark-level (§7).

---

## 3. Simulator Backend

### 3.1 Reuse of NewtonBench

We **fork** the 12 named domains from NewtonBench (HKUST-KnowComp/NewtonBench, arxiv 2510.07172) as the baseline-law layer, and add a thin **shift-injection layer** on top. The 12 domains line up 1-to-1 with the catalog:

| # | Domain | Baseline source | Shifts available (catalog) |
|---|---|---|---|
| 1 | Hooke spring | NewtonBench hooke | γ-1-1, γ-1-2, δ-1-1 |
| 2 | Newtonian gravity | NewtonBench gravity | γ-2-1, γ-2-2, δ-2-1 |
| 3 | Damped HO | NewtonBench damped | γ-3-1, γ-3-2, δ-3-1 |
| 4 | Pendulum | NewtonBench pendulum | γ-4-1, γ-4-2, δ-4-1 |
| 5 | Coulomb | NewtonBench coulomb | γ-5-1, γ-5-2, δ-5-1 |
| 6 | RLC | NewtonBench rlc | γ-6-1, γ-6-2, δ-6-1 |
| 7 | Thermal (Fourier) | NewtonBench fourier | γ-7-1, γ-7-2, δ-7-1 |
| 8 | Scalar wave | NewtonBench wave | γ-8-1, γ-8-2, δ-8-1 |
| 9 | Geometric optics (Snell) | NewtonBench snell | γ-9-1, γ-9-2, δ-9-1 |
| 10 | Inviscid fluid (Bernoulli) | NewtonBench bernoulli | γ-10-1, γ-10-2, δ-10-1 |
| 11 | Reaction kinetics | NewtonBench kinetics | γ-11-1, γ-11-2, δ-11-1 |
| 12 | Radioactive decay | NewtonBench decay | γ-12-1, γ-12-2, δ-12-1 |

### 3.2 Shift injection

Each shift is implemented as a **function-level replacement** that takes the baseline's force / EOM / rate routine and substitutes the catalog-specified expression, parameterized by samples drawn at `Scenario Loader` time under the shift's documented sampling and safety preconditions. All shifts go through a single registry:

```
mirrorlab/shifts/<domain>/<shift_id>.py  →  ShiftImpl(law, sampler, validator)
```

`validator` re-runs the catalog's safety preconditions at scenario emit and rejects bad samples (e.g. γ-10-2 must satisfy `|λ|·(h_max/h₀)^q < 0.5`). Invariant labels are kept in a *separate* file (`labels.json`) that the agent prompt never reads.

### 3.3 Dual-API design (Paper 2 hook, not exposed in v1)

The `SimInstance` exposes two surfaces internally:

- `agent_api`: the only surface the LLM agent can reach. Tool-mediated, monitored, rate-limited.
- `auto_api`: bare `reset()`, `step(action) → obs`, `close()`. **Disabled** in v1 — guarded by a feature flag that ships *off*. Documented in the codebase as the entry point for Paper 2's WM-training rollouts.

This keeps the API contract frozen now so Paper 2 doesn't have to rewrite the backend later.

---

## 4. Tool Pool Design

Four categories (D3). Each tool has a stated **token cost** (counts toward the per-scenario budget) and is **stateless across scenarios** in v1.

### 4.1 Minimum viable set (≥ 8 per category — adjust during Sprint 2 calibration)

**Measure** (read-only, observes simulator state)

1. `measure.position(body_id, t)` — returns position observation + noise.
2. `measure.velocity(body_id, t)` — first-difference / direct, depending on domain.
3. `measure.field(probe_point, field_type)` — for EM / thermal / fluid domains.
4. `measure.energy(system)` — total mechanical / electrical energy estimator.
5. `measure.spectrum(signal, window)` — FFT on a tool-collected signal.
6. `measure.trajectory(body_id, t_window, sample_rate)` — bulk trajectory pull.
7. `measure.scattering(beam, target)` — domain-specific (optics, gravity probe).
8. `measure.observable(name)` — domain-listed extra observables (e.g. charge density).

**Manipulate** (issues controlled interventions)

1. `manipulate.set_initial(body_id, state)`
2. `manipulate.apply_impulse(body_id, Δp, t)`
3. `manipulate.set_external_field(field_spec)` — within domain-allowed envelope
4. `manipulate.set_boundary(boundary_spec)` — for PDE domains
5. `manipulate.set_parameter(param_name, value)` — only on a domain-whitelisted subset
6. `manipulate.reset()` — reset to scenario default
7. `manipulate.swap_bodies(i, j)` — interchange test (useful against γ-9-2 reciprocity)
8. `manipulate.time_reverse_probe(t_window)` — symmetry probe (T-rev test)

**Analyze** (compute-only, no sim access)

1. `analyze.fit(model, data, init)` — least-squares / nonlinear fit
2. `analyze.dim_check(expr, units)` — SI dimensional consistency
3. `analyze.symmetry_probe(data, kind)` — checks PAR/ROT/T-rev/SCALE invariance up to tolerance
4. `analyze.conserved_search(trajectory, ansatz_list)` — fits constants of motion
5. `analyze.spectral(signal)` — peak detection, harmonic content
6. `analyze.residual(model, data)` — RMS residual + structured residual visualization stub
7. `analyze.regress(features, target)` — generic OLS / LASSO front-end
8. `analyze.compare(model_a, model_b, data)` — likelihood-ratio surrogate

**Knowledge** (cost-bearing reads from a frozen knowledge cache)

1. `knowledge.lookup(law_name)` — returns a canonical formulation of a named law (Hooke, Coulomb, ...). High cost.
2. `knowledge.search_symmetries(domain)` — returns a *generic* list of symmetries available in the baseline domain. Medium cost.
3. `knowledge.list_units(quantity)` — SI unit reference. Low cost.
4. `knowledge.solve_ode(spec)` — symbolic ODE-solver façade. High cost.
5. `knowledge.simplify(expr)` — CAS simplification. Low cost.
6. `knowledge.taxonomy(domain)` — list of named effects (e.g. "Yukawa", "Duffing") to deliberately seed lookup-style attempts (audited for catalog overlap, see §8). Medium cost.
7. `knowledge.constants(name)` — fundamental constants (G, k_e, etc.). Low cost.
8. `knowledge.cite(query)` — opaque "literature snippet" hook (returns a generic textbook excerpt, never catalog shifts). Medium cost.

### 4.2 Persistence (D5, v1 form)

- **Within scenario**: agent-authored Python snippets / fitted models persist for the duration of one scenario via a scratchpad.
- **Across scenarios**: scratchpad **wiped**. The on-disk schema is forward-compatible (`scratchpad/{scenario_id}.json` with a versioned envelope), but the cross-scenario loader is hard-disabled by a flag.

### 4.3 Library-call monitoring

We do **not** forbid `numpy`, `scipy`, `sympy`, `sklearn`, or even `pysr` / `gplearn`. Sandbox monitors record (per scenario):

- Tool calls (name, args hash, latency, cost).
- Python imports list + per-import cumulative wall-clock and token-equivalent compute.
- Whether the submission's formula was produced by a `pysr` / `gplearn` / `polyfit` call (best-effort static + dynamic detection — flagged into a reportable axis, not penalized).

The benchmark relies on the **elegant defense** of R5 §1 (extrapolation + cross-scenario consistency + counterfactual probes) rather than tool bans — measured god-tool usage is a *reported axis*, not an enforced rule.

---

## 5. Submission Format

Each scenario closes with the agent emitting a **submission set** = list of one or more candidate laws. Each entry:

```json
{
  "law_id": "L1",
  "formula": "F = -k*x - alpha*x**3",
  "predictor": { "lang": "python", "code": "def f(x, k, alpha): return -k*x - alpha*x**3" },
  "inputs":  [ {"name": "x",     "units": "m"} ],
  "outputs": [ {"name": "F",     "units": "kg*m/s**2"} ],
  "params":  [ {"name": "k",     "units": "kg/s**2", "value": 4.21},
               {"name": "alpha", "units": "kg/(m**2 s**2)", "value": 0.13} ],
  "claim_broken_symmetry": "LIN"     // optional, scored as bonus (§7)
}
```

### 5.1 Rules

- **Formula** (string, human-readable) and **predictor** (callable) must agree (checked by random-input parity test before scoring).
- **SI dimensional signature** is mandatory. Missing or malformed units ⇒ **auto-0** for that entry (stage-1 dim filter fails closed).
- **Variable names** must reference the scenario's declared observables. Unknown vars ⇒ auto-0.
- **Internal consistency across the set is NOT required** (catalog "Option A", per D6 R-1 discussion). Each entry is scored independently; the *best-scoring* entry contributes the main score, subject to a small penalty for set size (§7) to discourage shotgun submissions.

### 5.2 Set size cap

`|submission_set| ≤ 5` per scenario. Larger sets are truncated to the agent's first 5 in declaration order.

---

## 6. Evaluation Protocol

### 6.1 Stage 1 — dimensional pre-filter

For each submission entry: compute the SI dim signature of `formula` from the declared input / output / parameter units; verify the output matches the scenario's declared output dim. Failure ⇒ entry score = 0, do not proceed to stage 2.

### 6.2 Stage 2 — numerical matching

For each surviving entry, evaluate the predictor on a **held-out test grid** of $N_{test}$ points sampled from three sub-grids:

| Sub-grid | Symbol | Purpose | Default share (v1, **[CAL]**) |
|---|---|---|---|
| (a) in-domain | $\mathcal{T}_a$ | sample range overlaps agent's measurement window | 0.40 |
| (b) OOD | $\mathcal{T}_b$ | sample range outside measurement window; R5 §1 motif | 0.40 |
| (c) counterfactual | $\mathcal{T}_c$ | latent scenario parameter perturbed at evaluation time (R5 §3) | 0.20 |

Per-point error metric: **RMSLE** of predictor vs ground truth on each output channel (RMSLE chosen for scale-spanning robustness, consistent with NewtonBench).

Per-entry score: $s_{entry} = \exp(-\bar{R} / \tau)$, where $\bar{R}$ is the weighted-mean RMSLE across the three sub-grids using the share weights above and $\tau$ is a **[CAL]** scale (Sprint-3 calibration; target placeholder $\tau = 0.5$).

### 6.3 Bonus probe (symmetry / conservation recognition)

If `claim_broken_symmetry` is present and matches the ground-truth shift label (e.g. `"ROT"` for γ-2-1), award `b = 0.10` bonus (**[CAL]**). Wrong claim ⇒ no penalty. Baseline scenarios accept `"none"` as the correct claim.

This is the only signal the agent gets about the *invariant-label* layer; it does *not* leak the formula.

---

## 7. Scoring Formula

Per scenario:

$$
S_{scen} = \max_{e \in \text{submission}} s_{entry}(e) \cdot \big(1 - \rho \cdot (|\text{submission}|-1)\big) + b \cdot \mathbb{1}[\text{symmetry claim correct}]
$$

with `ρ = 0.05` (**[CAL]**) shotgun-penalty per extra entry beyond the first. $S_{scen} \in [0, 1+b]$.

Benchmark-level aggregate: macro-mean per (domain, tier) cell, then equal-weight average across cells:

$$
S_{bench} = \frac{1}{|\text{cells}|} \sum_{(d, t) \in \text{cells}} \frac{1}{|\text{scen}(d,t)|} \sum_{s} S_{scen}(s)
$$

where `tier ∈ {baseline, γ, δ}` and `domain ∈ {1..12}` ⇒ 36 cells.

### 7.1 Reporting axes (Paper 1 headline figures)

1. **Cliff plot**: $S_{bench}$ per tier (baseline / γ / δ), per model. Expected pattern (per `story.md` hypothesis): tall on baseline, mid on γ, near-random on δ.
2. **Per-domain heatmap**: 12 × 3 cell, one model per panel.
3. **OOD vs in-domain gap**: $\langle s_a \rangle - \langle s_b \rangle$ per tier — the R5 §1 "extrapolation kills god-tool" axis.
4. **Counterfactual-robustness**: $\langle s_c \rangle$ alone, per tier — the R5 §3 axis.
5. **Symmetry-naming accuracy**: $\mathbb{1}[\text{claim correct}]$ rate per tier, per model — independent of formula accuracy.
6. **Tool-pool usage profile**: stacked bar of tool-category call counts per model — descriptive only, not scored.

---

## 8. Adversarial Self-Test (Lookup Attacker)

### 8.1 Goal

Before release, demonstrate that a **lookup-style attacker** — an agent whose strategy is "match observed law to a textbook taxonomy and re-emit it" — scores **below 50 %** of $S_{bench}$ on the γ ∪ δ slice. Threshold: $S_{bench}^{lookup}(\gamma \cup \delta) < 0.50$ (**[CAL]**).

### 8.2 Implementation

- **Attacker prompt** (locked-in template): *"You are an expert physicist. You will observe a physical system through tool calls. After at most $K$ tool calls, submit the closest matching known law from your training data. Prefer canonical textbook forms. Do not propose novel modifications."* Plus the standard scenario observables.
- **Attacker model**: same frontier LLM family as the strongest evaluation target (worst-case attacker assumption). One attacker run per scenario, $K = 20$ (**[CAL]**).
- **Pass criterion**: full benchmark run; aggregate $S_{bench}^{lookup}$ on the 24 γ + 12 δ scenarios.
- **Gate**: if $S_{bench}^{lookup} ≥ 0.50$ on any cell, the offending shift goes back to the catalog round-3 (re-randomize parameter ranges, swap to alternate motif, or escalate to physicist-A/B).

### 8.3 Catalog interaction

Per the round-2 audit (`d6-shift-catalog.md` line 800), all 36 shifts already pass an attack-resistance heuristic. §8.2 is the **closed-loop verification** before public release.

---

## 9. Engineering Plan

### 9.1 Directory layout (target)

```
mirrorlab/
├── mirrorlab/
│   ├── domains/         # 12 baseline domain implementations (forked from NewtonBench)
│   ├── shifts/          # 36 catalog shifts, registry + impls
│   ├── scenarios/       # Scenario Loader, prompt templates, labels.json
│   ├── tools/           # measure / manipulate / analyze / knowledge
│   ├── sandbox/         # Python sandbox + monitor
│   ├── eval/            # stage-1 dim + stage-2 numeric + scoring
│   ├── attacker/        # lookup-attacker harness (§8)
│   ├── runners/         # per-model run drivers (Claude / GPT / Gemini / DeepSeek / o-series)
│   └── reports/         # plot + table generators for Paper 1 figures
├── tests/
│   ├── catalog/         # one test per shift: dim, single-break, safety preconditions
│   ├── tools/           # contract tests per tool
│   └── eval/            # golden-submission round-trips
├── docs/                # this spec + design notes
└── pyproject.toml
```

### 9.2 Sprints (4 × 2-week, assuming small team, no GPU)

| Sprint | Deliverable | Exit criterion | ETA (assuming start 2026-06-01) |
|---|---|---|---|
| 1 | Sim backend skeleton + 1 demo shift end-to-end | A single γ-1-1 scenario runs from loader → agent stub → eval → score | 2026-06-14 |
| 2 | Full 36-shift catalog wired + tool pool MVS (§4) | All 36 catalog shifts emit valid scenarios; tool contract tests green | 2026-06-28 |
| 3 | Evaluator (§6) + scoring (§7) + lookup-attacker (§8) | Pilot run on 5 scenarios × 1 model passes; attacker scores < 50 % on a sampled γ+δ slice | 2026-07-12 |
| 4 | 5 frontier-model sweep + Paper 1 figures + writing | Cliff plot reproduces, all six reporting axes produced; draft submitted | 2026-07-26 |

Assumptions: 2 engineers full-time, API budget allocated, no model-side scaffolding bugs. Slip risk concentrated in Sprint 2 (tool design iteration) and Sprint 4 (model-side reproducibility).

---

## 10. Open Calibration Items

Single registry of all **[CAL]** placeholders. Each is a value the v1 framework cannot fix from first principles; Sprint-3 ablations will pin them.

| ID | Item | Default placeholder | Decision rule |
|---|---|---|---|
| CAL-1 | Test-point shares $(\pi_a, \pi_b, \pi_c)$ | (0.40, 0.40, 0.20) | tune until the OOD-vs-in-domain gap is statistically detectable on baseline tier without saturating |
| CAL-2 | OOD ratio (extrapolation distance) | 5× sampling range | NewtonBench-comparable; revisit if SR baselines collapse instantly |
| CAL-3 | Counterfactual perturbation magnitude | ±30 % on shift's free parameters | small enough that the *correct* law transports, large enough that fitted constants don't |
| CAL-4 | Score temperature $\tau$ | 0.5 | calibrate so a trivial-constant predictor scores ~0 and the GT law scores > 0.9 |
| CAL-5 | Symmetry-bonus weight $b$ | 0.10 | small enough that it can't substitute for a wrong formula |
| CAL-6 | Shotgun penalty $\rho$ | 0.05 / extra entry | tune against attacker submitting 5× textbook laws |
| CAL-7 | Per-scenario tool budget | 30 tool calls + 60 s sandbox wall-clock | revisit if frontier models hit ceiling on baseline tier |
| CAL-8 | Attacker tool-call budget $K$ | 20 | set so the attacker can identify a *named* law but can't fit a non-textbook one |
| CAL-9 | Lookup-attacker pass threshold | < 0.50 $S_{bench}$ on γ ∪ δ | gate value — if loose, harder; if tight, may force catalog round-3 |
| CAL-10 | Per-cell scenarios | 3 random seeds per cell ⇒ 108 scenarios total | enough for cell-level mean ± std; expand if variance dominates |
| CAL-11 | Frontier-model panel | Claude Opus, GPT-5, Gemini 2.5 Pro, DeepSeek-R2, o-series | confirm versions at Sprint 4 launch (API drift risk) |
| CAL-12 | Knowledge-tool cost ratio | 5× a measure call | discourage but don't ban; tune against the attacker baseline |
| CAL-13 | RMSLE clamp on degenerate predictors | clamp at $10^6$ before RMSLE | avoid `inf` from divergent fits |

— end Paper 1 spec —
