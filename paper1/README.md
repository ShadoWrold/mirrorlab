# Paper 1 — MirrorLab manuscript source

LaTeX source for the Paper 1 draft. Target venue: NeurIPS / ICLR
Datasets-and-Benchmarks track, 8-page main + appendix.

## Files

| File | Purpose |
|---|---|
| `main.tex` | 8-page main manuscript |
| `appendix.tex` | Supplementary material; `\input{}`-ed from `main.tex` |
| `refs.bib` | Bibliography (BibTeX) |
| `Makefile` | `make pdf` builds the manuscript |
| `figures/` | Symlinks to `../figures/fig{1..6}_*.pdf` rendered by `mirrorlab.reports.figures` |

## Build

```bash
make pdf      # → main.pdf
make clean    # remove aux files
make view     # build + open
```

Requires a working TeX Live install (`pdflatex`, `bibtex`).

## Source-of-truth pointers

- Headline cliff numbers: `docs/sprint4-figure-captions.md` and
  `docs/sprint4-sweep-data-final.json` (rescored after Sprint 4 #7).
- Ceiling: `docs/sprint4-ceiling-report.md` and `docs/ceiling-data.json`.
- Lookup attacker: `docs/sprint35-report.md`.
- Shift catalog: `docs/d6-shift-catalog.md`.
- Calibration registry: `docs/paper1-spec.md` §10.

## Title status

Locked: **MirrorLab: A Symmetry-Organized Counterfactual Benchmark
Reveals a Discovery Cliff in Frontier LLM Agents.**
Two alternatives kept as comments at the top of `main.tex`.

## Honest-limitation block

Limitations section (§8) is load-bearing. It must state:
single seed, 4/12 domains, 5 models, gpt-4o → gpt-4.1 mid-sweep proxy
swap, self-reported symmetry-bonus label. Do not soften it without
re-reading `docs/sprint4-sweep-summary.md` first.
