"""Measure tools should reflect step() keys for every domain (not just Hooke 1-D)."""

from __future__ import annotations

import pytest

from mirrorlab.scenarios.loader import load
from mirrorlab.tools import measure


def _sim(domain: str):
    return load(domain, "baseline", seed=0).sim


def test_position_gravity_uses_r():
    r = measure.position(_sim("gravity"), body_id=0, t=0.0)
    assert "t" in r and "r" in r and "x" not in r


def test_position_coulomb_uses_r():
    r = measure.position(_sim("coulomb"), body_id=0, t=0.0)
    assert "r" in r


def test_position_pendulum_uses_theta():
    r = measure.position(_sim("pendulum"), body_id=0, t=0.0)
    assert "theta" in r


def test_position_optics_returns_thetas():
    r = measure.position(_sim("optics"), body_id=0, t=0.0)
    assert "theta1" in r and "theta2" in r


def test_position_hooke_still_returns_x():
    r = measure.position(_sim("hooke"), body_id=0, t=0.0)
    assert "x" in r


def test_position_raises_for_no_pos_observable():
    with pytest.raises(KeyError):
        measure.position(_sim("thermal"), body_id=0, t=0.0)


def test_velocity_pendulum_uses_omega():
    r = measure.velocity(_sim("pendulum"), body_id=0, t=0.0)
    assert "omega" in r


def test_velocity_wave_uses_du_dt():
    r = measure.velocity(_sim("wave"), body_id=0, t=0.0)
    assert "du_dt" in r


def test_velocity_rlc_uses_i():
    r = measure.velocity(_sim("rlc"), body_id=0, t=0.0)
    assert "i" in r


def test_velocity_decay_uses_rate():
    r = measure.velocity(_sim("decay"), body_id=0, t=0.0)
    assert "rate" in r


def test_trajectory_coulomb_returns_all_step_keys():
    r = measure.trajectory(_sim("coulomb"), body_id=0,
                           t_window=[0.0, 0.5], sample_rate=10)
    for k in ("t", "r", "v", "F"):
        assert k in r
        assert len(r[k]) == len(r["t"])


def test_trajectory_pendulum_returns_theta_and_omega():
    r = measure.trajectory(_sim("pendulum"), body_id=0,
                           t_window=[0.0, 1.0], sample_rate=20)
    assert "theta" in r and "omega" in r
    assert len(r["theta"]) == len(r["omega"]) == len(r["t"])


def test_spectrum_accepts_pendulum_theta():
    r = measure.spectrum(_sim("pendulum"), signal="theta",
                         window=[0.0, 2.0], n_samples=64)
    assert len(r["freqs"]) == len(r["magnitude"])


def test_spectrum_accepts_kinetics_C():
    r = measure.spectrum(_sim("kinetics"), signal="C",
                         window=[0.0, 2.0], n_samples=64)
    assert len(r["freqs"]) == len(r["magnitude"])


def test_spectrum_rejects_unknown_signal_with_available_list():
    with pytest.raises(ValueError, match="available"):
        measure.spectrum(_sim("pendulum"), signal="x",
                         window=[0.0, 1.0], n_samples=32)


def test_field_force_raises_when_not_exposed():
    with pytest.raises(KeyError, match="force"):
        measure.field(_sim("thermal"), probe_point=[0.0], field_type="force")


def test_energy_falls_back_when_no_v():
    r = measure.energy(_sim("thermal"), system="total", t=0.0)
    assert r["kinetic"] is None
    assert "note" in r


def test_energy_hooke_still_computes_kinetic():
    r = measure.energy(_sim("hooke"), system="total", t=0.0)
    assert r["kinetic"] is not None
