"""Smoke render test for the Paper-1 figures (X+Y rebuild).

Renders all 6 figures into a tmp dir and checks that each (.png, .pdf) pair
exists and has non-trivial size. Headline numbers from the cliff plot are
verified against the X+Y 4-model sweep (docs/sprint4-sweep-data-final.json).
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


# X+Y mean S_scen per (model, tier) — from docs/sprint4-sweep-data-final.json,
# rescored under the contract-fixed scoring core (CAL-4 τ=0.20, relative-floor
# metric, alias-bridge + coeff synonyms). The γ-tier cliff holds for all four
# models against the near-flat oracle ceiling (~0.99 across tiers).
HEADLINE_EXPECTED = {
    "gpt-5.5":                 (0.980, 0.003, 0.118),
    "gpt-5.4-20260305":        (0.924, 0.121, 0.167),
    "gemini-3.1-pro-preview":  (0.825, 0.068, 0.088),
    "claude-opus-4.8":         (0.881, 0.007, 0.102),
}

FIG_NAMES = [
    "fig1_cliff",
    "fig2_heatmap_gamma",
    "fig3_radars",
    "fig4_attacker",
    "fig5_ceiling_scatter",
    "fig6_efficiency",
]


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("figs")
    figs_mod = importlib.import_module("mirrorlab.reports.figures")
    # Re-point FIG_DIR to the tmp dir so the test does not stomp on the
    # committed figures/ outputs.
    figs_mod.FIG_DIR = Path(tmp)
    headline = figs_mod.render_all()
    return Path(tmp), headline


def test_all_figures_emit_png_and_pdf(rendered):
    out_dir, _ = rendered
    for name in FIG_NAMES:
        png = out_dir / f"{name}.png"
        pdf = out_dir / f"{name}.pdf"
        assert png.exists(), f"missing {png}"
        assert pdf.exists(), f"missing {pdf}"
        assert png.stat().st_size > 5_000, f"{png} too small ({png.stat().st_size} bytes)"
        assert pdf.stat().st_size > 3_000, f"{pdf} too small ({pdf.stat().st_size} bytes)"


@pytest.mark.parametrize("model,expected", list(HEADLINE_EXPECTED.items()))
def test_cliff_headline_numbers(rendered, model, expected):
    _, headline = rendered
    base_e, gamma_e, delta_e = expected
    assert headline[f"{model}/baseline"] == pytest.approx(base_e, abs=0.005)
    assert headline[f"{model}/gamma"] == pytest.approx(gamma_e, abs=0.005)
    assert headline[f"{model}/delta"] == pytest.approx(delta_e, abs=0.005)
