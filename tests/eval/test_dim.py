"""Tests for ``mirrorlab.eval.dimensional`` — SI 7-tuple parsing + matching."""

from __future__ import annotations

import pytest

from mirrorlab.eval.dimensional import ZERO, match_dim, parse_dim


def test_parse_force_unit_lowercase_si():
    assert parse_dim("kg*m*s**-2") == (1, 1, -2, 0, 0, 0, 0)


def test_parse_force_unit_symbolic_bracketed():
    assert parse_dim("[M·L/T²]") == (1, 1, -2, 0, 0, 0, 0)


def test_parse_dimensionless():
    assert parse_dim("1") == ZERO
    assert parse_dim("") == ZERO


def test_parse_length():
    assert parse_dim("m") == (0, 1, 0, 0, 0, 0, 0)


def test_parse_spring_constant():
    assert parse_dim("kg*s**-2") == (1, 0, -2, 0, 0, 0, 0)


def test_parse_division_chain():
    # kg/m/s**2 → kg · m⁻¹ · s⁻²  (note: this is *not* force; just exercising parser)
    assert parse_dim("kg/m/s**2") == (1, -1, -2, 0, 0, 0, 0)


def test_parse_unicode_superscript_negative():
    assert parse_dim("s⁻²") == (0, 0, -2, 0, 0, 0, 0)


def test_parse_unknown_unit_raises():
    with pytest.raises(ValueError):
        parse_dim("foo*bar")


# ---- Dimensionless derived units (rad, sr): SI angle is length/length -------

def test_parse_radian_is_dimensionless():
    # A radian is m/m — dimensionless. An LLM writing "rad" for an angle must
    # not be rejected as an unknown unit.
    assert parse_dim("rad") == ZERO
    assert parse_dim("sr") == ZERO


def test_parse_angular_acceleration_equals_inverse_s_squared():
    # rad/s^2 is physically s^-2 (angular acceleration). A pendulum predictor
    # that outputs "rad/s^2" must match a target written as "s**-2".
    assert parse_dim("rad/s^2") == (0, 0, -2, 0, 0, 0, 0)
    assert parse_dim("rad/s**2") == (0, 0, -2, 0, 0, 0, 0)


def test_match_dim_radian_units_against_si_target():
    # The exact false-reject from the claude sweep: correct physics, units
    # written in non-canonical (angular) form.
    assert match_dim({"outputs": [{"name": "a", "units": "rad/s^2"}]},
                     "s**-2") is True
    assert match_dim({"outputs": [{"name": "th", "units": "rad"}]},
                     "1") is True


def test_match_dim_correct():
    entry = {"outputs": [{"name": "F", "units": "kg*m*s**-2"}]}
    assert match_dim(entry, "kg*m*s**-2") is True
    assert match_dim(entry, (1, 1, -2, 0, 0, 0, 0)) is True


def test_match_dim_mismatch():
    entry = {"outputs": [{"name": "F", "units": "kg*m*s**-1"}]}
    assert match_dim(entry, "kg*m*s**-2") is False


def test_match_dim_missing_units_fails_closed():
    assert match_dim({"outputs": [{"name": "F"}]}, "kg*m*s**-2") is False
    assert match_dim({"outputs": []}, "kg*m*s**-2") is False
    assert match_dim({}, "kg*m*s**-2") is False


def test_match_dim_garbage_units_fails_closed():
    entry = {"outputs": [{"name": "F", "units": "foo"}]}
    assert match_dim(entry, "kg*m*s**-2") is False


# ---- "name = expansion" equivalence declarations (T25 parser bug) -------
# LLMs frequently write a unit as "<named> = <base-SI expansion>", e.g.
# gpt-5.5 submitted "N = kg m s^-2" for force. The two sides are the SAME
# dimension written two ways; the parser must NOT multiply them together.

def test_parse_named_equals_expansion_force():
    # Was the bug: parsed N(1,1,-2) * kg*m*s^-2(1,1,-2) = (2,2,-4).
    assert parse_dim("N = kg m s^-2") == (1, 1, -2, 0, 0, 0, 0)


def test_parse_named_equals_expansion_spring_constant():
    assert parse_dim("N m^-1 = kg s^-2") == (1, 0, -2, 0, 0, 0, 0)


def test_parse_expansion_equals_named_either_side():
    # Equivalence is symmetric: expansion on the left must also work.
    assert parse_dim("kg m s^-2 = N") == (1, 1, -2, 0, 0, 0, 0)


def test_parse_space_separated_base_si():
    # "kg m s^-2" (space-separated, ^ exponent) must equal the canonical form.
    assert parse_dim("kg m s^-2") == (1, 1, -2, 0, 0, 0, 0)


def test_match_dim_accepts_named_equals_expansion():
    entry = {"outputs": [{"name": "F", "units": "N = kg m s^-2"}]}
    assert match_dim(entry, "kg*m*s**-2") is True
