# MirrorLab Handover Document

> **Purpose**: Bring a new AI assistant up to speed on the MirrorLab research program. Read this before doing anything.
>
> **Reading order**: §1 → §2 → §3 → §4 → §5 → §6 → skim others.
>
> **Last update**: 2026-05-27 by Claude Opus 4.7

---

## 1. What MirrorLab Is (60 seconds)

A research program with **3 planned papers**, organized under GitHub org [ShadoWrold](https://github.com/ShadoWrold) (typo intentional — "shifted spelling" mirrors the project's shifted physics).

**Paper 1 (current focus)** — **MirrorLab**: a physics-discovery benchmark for LLM agents. We construct physics worlds where exactly one symmetry has been broken (γ-shifts) or one conservation law violated (δ-shifts). Frontier LLMs are scored on whether they can:
1. Discover the modified law from experiments
2. Submit predictions that survive **out-of-distribution** and **counterfactual** probe points

**Why this matters**: existing benchmarks (NewtonBench, PhysGym) only test β-type mutations (changed constants/exponents). γ/δ shifts are organized by **Noether's theorem** — each shift breaks exactly one symmetry, and the broken Noether charge is the smoking gun. We test whether LLMs can think *structurally* about physics, not just curve-fit.

**Paper 2** — Counterfactual diversity hypothesis (train physical world models on MirrorLab).
**Paper 3** — Symmetry recovery via physics-inductive world models.

**Sprint 4 result (preliminary, single-seed, 4 representative domains)**: 4/5 frontier LLMs cliff-drop on γ-tier; only GPT-5.4 holds (0.698 vs 1.10 ceiling). cliff plot in [`figures/fig1_cliff.png`](../figures/fig1_cliff.png).

---

## 2. Repository Map

```
mirrorlab/                            # ROOT
├── README.md                         # public-facing repo description
├── paper1/                           # Paper 1 LaTeX manuscript (9-page draft)
│   ├── main.tex, appendix.tex, refs.bib, Makefile
│   └── main.pdf                      # builds clean
├── mirrorlab/                        # PYTHON PACKAGE
│   ├── domains/                      # 12 baseline physics simulators
│   ├── shifts/                       # 36 γ/δ shift implementations (= 12 × 3)
│   ├── scenarios/
│   │   ├── loader.py                 # scenario builder w/ test grids
│   │   ├── prompts.py                # 12 domain prompt templates
│   │   ├── agent_stub.py             # rule-based baseline agent
│   │   ├── counterfactual.py         # ±30% latent-param perturbation
│   │   └── registry.py               # (domain, shift) → SimInstance
│   ├── tools/                        # 32-tool MVS (measure/manipulate/analyze/knowledge)
│   │   ├── measure.py, manipulate.py, analyze.py, knowledge.py
│   │   ├── registry.py, sandbox.py
│   ├── eval/                         # 2-stage evaluator (dim + numeric)
│   │   ├── dimensional.py, numeric.py, scoring.py
│   ├── runners/
│   │   ├── openai_client.py          # OpenAI-format proxy (gpt-*) @ 127.0.0.1:4142
│   │   ├── anthropic_client.py       # Anthropic-format proxy (claude/gemini) @ 127.0.0.1:4141
│   │   ├── provider.py               # auto-dispatch by model name prefix
│   │   ├── llm_agent.py              # tool-calling loop w/ budgets
│   │   ├── ceiling_agent.py          # oracle ceiling experiment
│   │   ├── sprint{1,2,3,3_5,4}_*.py  # sprint demo / pilot runners
│   │   ├── rescore.py                # re-score saved sweep data
│   ├── attacker/                     # lookup-attacker (spec §8)
│   │   ├── lookup.py, runner.py, cli.py
│   ├── calibration/sweep.py          # CAL-N knob sweeps
│   └── reports/figures.py            # paper figures generator
├── vendor/newtonbench/               # git submodule (HKUST-KnowComp/NewtonBench)
├── tests/                            # pytest suite (~850 tests)
│   ├── catalog/                      # 36 per-shift tests
│   ├── scenarios/, tools/, eval/, attacker/, calibration/
│   ├── runners/, reports/, integration/
├── figures/                          # paper-grade PDFs + PNGs (300 dpi)
├── docs/
│   ├── program-overview.md           # 3-paper program (PI / collaborator view)
│   ├── story.md                      # plain-English 500-word story
│   ├── paper1-spec.md                # Paper 1 implementation spec
│   ├── d6-shift-catalog.md           # 36 shifts, post-audit Round-2 final
│   ├── audits/                       # 36 per-shift human-review markdowns
│   ├── sprint{1,2,3,3_5,4}-report.md # per-sprint verdicts
│   ├── sprint4-{sweep-data,ceiling-data,...}.json   # raw experimental data
│   ├── v2-todo.md                    # carry-over fixes deferred to v2
│   └── HANDOVER.md                   # ← this file
└── pyproject.toml
```

---

## 3. Sprint History (timeline, what was achieved)

| Sprint | Goal | Outcome |
|---|---|---|
| **1** | sim + agent loop + scoring (Hooke + γ-1-1 only) | PASS, end-to-end demo green |
| **2** | All 12 domains + 36 shifts + 32 tools + true counterfactual sub-grid | PASS, 331/331 tests; multi-seed mean discrimination Δ jumped 0.22 → 0.40 |
| **3** | LLM runner + lookup-attacker + first pilot | CONDITIONAL PASS — pipeline worked but 0/5 honest cells submitted due to **budget-prompt mismatch** (prompt advertised CAL-7=30 calls but runner clamped to 20; model paced wrong) |
| **3.5** | Fix budget contract + retry pilot | TRUE PASS — 4/5 honest cells submitted, attacker `S_bench^lookup = 0.0` (non-vacuous) |
| **4** | 5-model × 4-domain × 3-tier sweep + ceiling + figures + paper draft | TRUE PASS — cliff plot reproduces; ceiling median 1.08 (bench fair); 9-page paper PDF builds clean |
| **4.5** (in progress at handover) | Fix audit findings: step() leaks + sampler/validator hardening | Done at handover write-time — 853/854 tests, see commit `34ea738` |

---

## 4. Conventions & Codified Rules

These rules emerged from human review and override any earlier informal conventions.

### 4.1 step() leak severity rule (codified 2026-05-27 during δ-1-1 audit)

> A `step()` output key is a 🔴 leak iff: **(a) the key is a derived quantity that the shift's broken-symmetry directly manifests in, AND (b) the baseline domain's `step()` does not include that key**.

Examples:
- γ-1-2 outputting `Lz` → 🔴 (ROT-break Noether charge; baseline Hooke is 1D, no Lz)
- δ-1-1 outputting `E` → 🔴 (E-break charge; baseline doesn't output E)
- δ-2-1 outputting `G_eff` → 🔴 (modified parameter directly)

This was applied during the 36-shift human audit; 14 shifts had 🔴 leaks (now removed in Sprint 4.5).

### 4.2 D6 design rules (shift construction)

When designing or modifying shifts:
1. **Borrow but don't copy**: take ideas from named physics effects (MOND / Cattaneo-Vernotte / SME / Stokes drag / ...) but write a novel functional form. Avoid lookup-attacker recognition.
2. **Cross-domain re-skin preferred**: transplanting a math structure from domain A to domain B is the strongest defense.
3. **One symmetry break per shift**: γ-X-Y breaks exactly one γ-type symmetry; δ-X-Y breaks exactly one conservation law. Dissipative bundle convention: T-rev loss is bundled with E-break, counted as single shift.
4. **Wide parameter randomization**: every free parameter from a LogUniform or Uniform distribution covering ≥1 decade or ≥0.5 range.
5. **Numerical safety**: validator must enforce parameter regions where sim is stable.

### 4.3 [CAL] placeholder convention

[CAL]-tagged values in spec are deliberately un-fixed placeholders. They are tuned in Sprint 3 calibration. Status at handover:
- **Locked**: CAL-4 τ=0.35, CAL-7=30 (honest budget), CAL-8 K=20 (attacker), CAL-9 < 0.50 (attacker threshold)
- **Deferred to camera-ready**: CAL-1 (sub-grid shares), CAL-3 (±30% counterfactual), CAL-10 (seeds per cell)

### 4.4 Provider routing

- `gpt-*`, `o3*`, `o4*` → OpenAI-format proxy at `127.0.0.1:4142/v1`, env `MIRRORLAB_LLM_API_KEY` (sk-cloudgpt-...)
- `claude-*`, `gemini-*` → Anthropic-format proxy at `127.0.0.1:4141`, key literal `"dummy"`
- Default model: `gpt-5.4-20260305` (bare `gpt-5.4` not on proxy)
- Known quirks: gpt-5.x rejects `tool_choice` + `max_tokens` (shim in `openai_client.OpenAIClient.chat` drops them only for gpt-5*); gpt-5.4 is 3× slower than gpt-4.1

### 4.5 Memory references

- `~/.claude/projects/-Data-tanh-phyLLM/memory/llm_api_endpoint.md` — proxy keys + model defaults
- `~/.claude/projects/-Data-tanh-phyLLM/memory/MEMORY.md` — index

These survive across Claude sessions. New AI may not have access — check the GitHub repo's docs/ as authoritative.

---

## 5. Open Decisions Awaiting User Input

### 5.1 Tool pool multi-D bug (just discovered, blocks reliable Sprint 4 reinterpretation)

Audit found: `measure.position / velocity / energy / trajectory / spectrum` and `manipulate.set_initial / apply_impulse / set_parameter / time_reverse_probe` assume **1-D Hooke**. They KeyError or stub-fail on 11/12 multi-D domains.

**Effective tools per scenario**:
- 1D scenarios (hooke baseline, hooke γ-1-1, hooke δ-1-1, decay, kinetics, fluid): **~30 / 32 work**
- Multi-D scenarios (gravity, coulomb, hooke γ-1-2, rlc, thermal, wave, optics, pendulum): **~18 / 32 work**

This means Sprint 4 sweep results conflate "LLM weakness" with "tool unavailability".

**Decision pending**: spawn agent team to fix (next planned action) vs. document as known limitation.

### 5.2 v2-todo backlog (7 items deferred to camera-ready)

See [`docs/v2-todo.md`](v2-todo.md). Summary:
- **TODO-1**: IC randomization (36-shift refactor; sampler currently hardcodes initial conditions)
- **TODO-2**: ~~step() leak removal (DONE in Sprint 4.5)~~
- **TODO-3**: gravity γ-2-1 v_circ uses G_DEFAULT (intentional but undocumented — now commented)
- **TODO-4**: timescale normalization (gravity M spans 4 orders → orbital period not visible to agent)
- **TODO-5**: γ-2-2 is 1D radial sim, can't show Bertrand precession (claim-vs-impl mismatch)
- **TODO-6**: ~~γ-3-2 sampler silent γ-mutation (FIXED via rejection sampling)~~
- **TODO-7**: ~~Coulomb min-distance check (FIXED)~~

### 5.3 v1 paper data caveat (must footnote)

Sprint 4 sweep (60 cells × 5 models = 300 LLM calls) was run with:
- (a) step() leaks present for 5 of the 12 swept cells (Hooke δ-1-1, Coulomb γ-5-1, Coulomb δ-5-1, Thermal γ-7-1, Thermal δ-7-1) — now removed in Sprint 4.5
- (b) multi-D tool bugs (just discovered, not yet fixed)

The cliff finding **still holds qualitatively** (Claude got 0 on γ even with leaks; bench-fairness ceiling experiment is unaffected). But the paper §8 Limitations should:
1. Footnote the step() leak issue
2. Footnote the tool availability issue
3. Promise camera-ready re-run after fixes

---

## 6. Active Work Queue (Recommended Next Steps)

In order of priority:

1. **🔴 Tool pool multi-D fix** (Sprint 4.5 continuation, ~1-2 hours)
   - measure.position/velocity etc. → reflect-from-step()
   - manipulate.set_parameter → use sim.params dataclass fields automatically
   - knowledge.list_observables → align with step() reality

2. **🟡 Re-run Sprint 4 sweep with fixed tools** (~1-2 hours LLM time)
   - 60 cells × 5 models with new tools; compare to pre-fix data
   - If cliff still visible, paper claims solidify
   - Update figures, regenerate `paper1/main.pdf`

3. **🟡 Audit remaining components** (Hour each, deferable)
   - `scenarios/loader.py` (test grid generation per domain)
   - `eval/dimensional.py` + `eval/numeric.py` (post-Sprint-4 binding fixes)
   - `attacker/lookup.py` (locked prompt v1.1)
   - `calibration/sweep.py` (knob sweep math)
   - `paper1/main.tex` (manuscript polish)

4. **v2 backlog** (camera-ready, weeks of work)
   - TODO-1 IC randomization
   - TODO-4 timescale normalization
   - TODO-5 γ-2-2 2D upgrade
   - Multi-seed sweep (current is single-seed)
   - Full 48-pair sweep (current is 12-pair subset)

5. **Paper 2 program** (deferred until Paper 1 ships)
   - Counterfactual diversity hypothesis
   - Train physical world models on MirrorLab trajectories
   - Auto-mode procedural data generator (already designed in `domains/*` with feature flag, not wired)

---

## 7. Team / Agent Conventions

This project has used heavy delegation to agent teams. Each Sprint had a team of 4-8 named agents (`physicist-A`, `sim-engineer`, `figure-maker`, etc.) coordinated via:

- `TeamCreate` / `TeamDelete` — one team per sprint
- `TaskCreate` / `TaskUpdate` — task list with `blockedBy` dependencies
- `SendMessage` — inter-agent comms (always by name, never UUID)
- `CronCreate(durable=true)` — 10-min polling for long-running sprints

When teams finish, **always shut down all teammates and `TeamDelete`** before starting a new sprint team. Lead can only manage one team at a time.

For non-sprint work (single-shot audits / fixes), `Agent(run_in_background=true)` is fine without a formal team.

---

## 8. Conversational Style

User prefers:
- **Terse, declarative responses** in Chinese (with English technical terms inline)
- **Numbers, tables, severity badges** (🔴 / 🟡 / ✅) over prose
- **Honest negative findings flagged loudly** — never sugar-coat
- **Direct decision questions** when blocked, not open-ended brainstorming
- ≤25 words between tool calls during execution; final summaries can be longer
- **Always cite file:line when referencing code**

User is technically sophisticated — physics + ML background. Don't over-explain basics. Do explain non-obvious reasoning chains.

When code/spec violations are found, **upgrade severity by codified rule, not by gut feeling** — see §4.1 for example precedent.

---

## 9. Git / GitHub Discipline

- Remote: `origin → https://github.com/ShadoWrold/mirrorlab` (current org)
- Also: `personal → https://github.com/Tanhhhhtjy/phyLLM` (archived backup)
- Main branch: `main`
- Co-author tag on AI-generated commits: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- **Never** commit secrets (API keys live only in env vars / memory files)
- Every sprint commits to `main` directly (no PR workflow)
- Commit messages include: what changed + why + test count diff

---

## 10. Quick Verification Checklist (New AI runs this first)

```bash
cd /Data/tanh/phyLLM
git log --oneline -10              # see recent commits
pytest -q                           # should report 853/853 (or close)
ls docs/audits/ | wc -l             # should be ≥37 (36 + README)
cat docs/v2-todo.md                 # see open backlog
ls vendor/newtonbench/              # submodule should be populated
cat paper1/main.pdf | head -c 4     # should start with %PDF
```

If any of these fail, surface to user immediately rather than guessing.

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

— end of handover —
