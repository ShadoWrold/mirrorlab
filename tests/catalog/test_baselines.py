"""Smoke tests: every registered baseline can step(0.0) and exposes a dim signature."""

from __future__ import annotations

import importlib

import pytest

from mirrorlab.scenarios.registry import make

BASELINES = [
    "hooke", "gravity", "damped_ho", "pendulum", "coulomb", "rlc",
    "thermal", "wave", "optics", "fluid", "kinetics", "decay",
]


@pytest.mark.parametrize("domain", BASELINES)
def test_baseline_step_zero(domain: str) -> None:
    sim = make(domain, "baseline", seed=0)
    obs = sim.step(0.0)
    assert "t" in obs and obs["t"] == 0.0
    assert sim.params is not None


@pytest.mark.parametrize("domain", BASELINES)
def test_baseline_dim_signature_well_formed(domain: str) -> None:
    mod = importlib.import_module(f"mirrorlab.domains.{domain}")
    sig = getattr(mod, "DIM_SIGNATURE")
    assert set(sig) >= {"inputs", "outputs", "params"}
    for section in ("inputs", "outputs", "params"):
        assert isinstance(sig[section], dict)
        for k, v in sig[section].items():
            assert isinstance(k, str) and isinstance(v, str) and v


@pytest.mark.parametrize("domain", BASELINES)
def test_baseline_step_small_positive(domain: str) -> None:
    sim = make(domain, "baseline", seed=1)
    obs = sim.step(0.01)
    assert obs["t"] == 0.01
    for k, v in obs.items():
        assert v == v, f"{domain}.{k} is NaN"
