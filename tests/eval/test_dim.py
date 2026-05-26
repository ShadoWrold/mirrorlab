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
