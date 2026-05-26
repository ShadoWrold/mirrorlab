"""Smoke render test for the Sprint-4 paper figures.

Renders all 6 figures into a tmp dir and checks that each (.png, .pdf) pair
exists and has non-trivial size. Headline numbers from the cliff plot are
verified against the team-lead's rescored mean S_scen table.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


HEADLINE_EXPECTED = {
    "claude-opus-4.6":         (0.258, 0.000, 0.249),
    "claude-sonnet-4.5":       (0.250, 0.000, 0.499),
    "gemini-3.1-pro-preview":  (0.483, 0.110, 0.583),
    "gpt-4.1-20250414":        (0.033, 0.000, 0.000),
    "gpt-5.4-20260305":        (0.571, 0.698, 0.474),
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
