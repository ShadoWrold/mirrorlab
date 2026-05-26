# Sprint 4 — Paper trail (reproducibility chain)

**Date frozen:** 2026-05-26
**Repo head at PDF build:** `0de1b92bea4de14282bd708fe8cb2afd1ac4f01e`
(`Sprint 3.5 TRUE PASS: budget contract fixed, lookup-attacker actually defeated`)

The Sprint-4 sweep, ceiling oracle, figure pipeline, paper draft, and
verdict report are all **uncommitted working-tree artifacts** at the moment
of this snapshot — they will be folded into a single "Sprint 4 TRUE PASS"
commit once the integrator hands back to team-lead. The SHA-256 hashes
below pin every input to `paper1/main.pdf` so that commit can be verified
bit-for-bit on re-build.

## Upstream commit chain

| Sprint | Commit | Subject |
|--------|--------|---------|
| Sprint 1 | `0301a85` | Sprint 1 PASS: end-to-end demo with Hooke + γ-1-1 |
| Sprint 2 | `0e57b11` | Sprint 2 PASS: full 36-shift catalog wired + 32-tool MVS + true counterfactual |
| Sprint 3 | `b349392` | Sprint 3 CONDITIONAL PASS: plumbing certified, behavioral data deferred |
| Sprint 3.5 | `0de1b92` | Sprint 3.5 TRUE PASS: budget contract fixed, lookup-attacker actually defeated |
| Sprint 4 | *pending* | (will land after team-lead merges this integration commit) |

## Sprint-4 artifact hashes (SHA-256)

### Sweep + oracle data

```
09436ebf68e958a32b50fe268742788fc5caeb9a035682771880d7b501501335  docs/sprint4-sweep-data-final.json
211c984b026d789e56f9fb23ba3d62e33218229507144f6f6a5f8875238f2a38  docs/ceiling-data.json
edf9c840ea0394567a581efe951aa4929afbe60ec7ee1fd3594501f7d4204549  docs/sprint35-pilot-data.json
```

`sprint4-sweep-data-final.json` is the **merged** dataset
(claude/gemini/gpt-5.4 from the original sweep + gpt-4.1 from the
gpt-4o-swap rerun, all rescored under the fixed scoring binding) — 60 runs,
5 models × 4 domains × 3 tiers × 1 seed. Provenance is recorded inside the
file's `meta.merged_from` field.

`ceiling-data.json` is the 48-pair oracle ceiling (12 domains × 4 shift
classes × 1 seed). Summary: median 1.083, mean 1.053, min 0.549, 47/48
above 0.7.

### Figures

```
40370089864768eced603366c79a5baf2b4ad770800c60cc1df9b11034758f06  figures/fig1_cliff.pdf
e9e203b9370bf38f58b1a1df18513f4e41586b2c0cdd6f265e5d84ed6c386d31  figures/fig2_heatmap_gamma.pdf
24ab6837cfa0e62f19d1554925c5f4be5dcc6f0c98e42c297207de75483cbebe  figures/fig3_radars.pdf
cc1b18127ac8060da48ea201ca4bbbddf136d1ea7801a3c19a1776d5cf229ab4  figures/fig4_attacker.pdf
e2f994d05d3946dafa956b6e809d1fbe398f4dd69a0ace44d3c9d7bef5695889  figures/fig5_ceiling_scatter.pdf
7abb512c01d6449c7dd9a572b838256ecb8cfebe3a754664e30a0309a43f9956  figures/fig6_efficiency.pdf
```

All six rendered by `mirrorlab/reports/figures.py` from the data files
above. 300-dpi PNGs co-exist next to the PDFs for README use.

### Paper sources + compiled PDF

```
4dc858c2d9f72972ac7f4905acdd74285efb6013305d0ee19c0f2039e6d079f4  paper1/main.tex
552ed19dac2b41cbddb8f1e2c4d4013aceb1aaf4bda4729c8c53def6f0d00bd8  paper1/appendix.tex
11e74129088fdca796216a83b70ec4c44c59a376b9de5a2ce6749765c3ef0280  paper1/refs.bib
5b5022c3d5ec406913776dffe173c0b83d981bea1fff160bf587b1173f8e68aa  paper1/main.pdf
```

### Test suite

```
pytest tests/ -q  →  854 passed in 128.08s (at the snapshot head)
```

## How to reproduce `paper1/main.pdf` from scratch

```bash
# 1. Repo at the snapshot head
git checkout 0de1b92  # plus the uncommitted Sprint-4 working tree

# 2. Verify sweep + oracle data hashes
sha256sum -c <<'EOF'
09436ebf68e958a32b50fe268742788fc5caeb9a035682771880d7b501501335  docs/sprint4-sweep-data-final.json
211c984b026d789e56f9fb23ba3d62e33218229507144f6f6a5f8875238f2a38  docs/ceiling-data.json
EOF

# 3. (Optional) Re-render figures from data
python -m mirrorlab.reports.figures  # writes figures/fig{1..6}.{png,pdf}

# 4. Build the PDF
cd paper1 && make distclean && make pdf
# → main.pdf, 9 pages, 388 965 bytes
#   SHA-256: 5b5022c3d5ec406913776dffe173c0b83d981bea1fff160bf587b1173f8e68aa
```

The PDF hash is **not** byte-stable across TinyTeX rebuilds (pdfTeX writes
a build timestamp), but the page count, figure-list, and bbl contents are
stable. For a byte-stable rebuild, set `SOURCE_DATE_EPOCH` before invoking
`pdflatex`.

## Provider / model identifiers used in the sweep

| Model alias                 | Provider     | Notes |
|-----------------------------|--------------|-------|
| `claude-opus-4.6`           | Anthropic    | task #1 adapter |
| `claude-sonnet-4.5`         | Anthropic    | task #1 adapter |
| `gemini-3.1-pro-preview`    | Google       | task #1 adapter |
| `gpt-4.1-20250414`          | OpenAI-compat| task #8 swap from `gpt-4o` |
| `gpt-5.4-20260305`          | OpenAI-compat| Sprint 3.5 default |

All five hit the same local OpenAI-compatible proxy / Anthropic SDK / Gemini
SDK chain wired in task #1. Scores were re-computed by
`mirrorlab.runners.rescore` after the task-#7 binding fix; the rescored mean
matches the values reported in `docs/sprint4-figure-captions.md` and
`docs/sprint4-report.md`.
