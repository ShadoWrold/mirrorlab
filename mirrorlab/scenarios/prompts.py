"""Agent-visible scenario prompts.

Per spec §3 / §3.2: each prompt exposes the domain narrative, observable
variables, and available tool names. It does NOT include the shift label
(e.g. ``gamma_1_1``, ``PAR``) nor any hint of the formula family
(no ``Hooke``, ``linear``, ``tanh``, ``F = -k x``, no domain proper
nouns like ``Coulomb``/``Newton``/``Bernoulli``/``Snell`` …). Per-domain
leak tests live under ``tests/scenarios/``.

Sprint 3: 12 templates — one per domain registered in the scenario
registry. Tool list is identical across domains (the agent harness
discovers tools through ``mirrorlab.tools.registry``; the prompt only
needs to advertise the canonical names).
"""

from __future__ import annotations

from typing import Sequence

# A shared shortlist of tool names visible to the agent. Kept small so the
# prompt stays human-readable; the full registry is exposed through the
# harness, not the prompt. See ``mirrorlab/tools/registry.py``.
DEFAULT_TOOL_NAMES: tuple[str, ...] = (
    "measure.observable",
    "measure.trajectory",
    "manipulate.set_initial",
    "analyze.fit",
    "analyze.regress",
    "analyze.dimensional_analysis",
    "analyze.residual",
)


# ---- Observables per domain --------------------------------------------

HOOKE_OBSERVABLES: tuple[str, ...] = ("t", "x", "v", "F")
DAMPED_HO_OBSERVABLES: tuple[str, ...] = ("t", "x", "v", "F")
GRAVITY_OBSERVABLES: tuple[str, ...] = ("t", "r", "v", "F")
COULOMB_OBSERVABLES: tuple[str, ...] = ("t", "r", "v", "F")
PENDULUM_OBSERVABLES: tuple[str, ...] = ("t", "theta", "omega")
RLC_OBSERVABLES: tuple[str, ...] = ("t", "q", "i", "V")
THERMAL_OBSERVABLES: tuple[str, ...] = ("T_hot", "T_cold", "L", "q")
WAVE_OBSERVABLES: tuple[str, ...] = ("t", "u", "du_dt")
OPTICS_OBSERVABLES: tuple[str, ...] = ("theta1", "theta2")
FLUID_OBSERVABLES: tuple[str, ...] = ("v", "h", "p", "p2")
KINETICS_OBSERVABLES: tuple[str, ...] = ("t", "C", "rate")
DECAY_OBSERVABLES: tuple[str, ...] = ("t", "N", "rate")

# Back-compat alias retained for Sprint 1 tests.
HOOKE_TOOL_NAMES: tuple[str, ...] = DEFAULT_TOOL_NAMES


# ---- Generic prompt assembler ------------------------------------------

def _compose(
    narrative: str,
    observables: Sequence[str],
    tool_names: Sequence[str],
) -> str:
    obs_line = ", ".join(observables)
    tool_lines = "\n".join(f"  - {name}" for name in tool_names)
    return (
        f"{narrative}\n"
        "\n"
        f"Observable variables: {obs_line}.\n"
        "\n"
        "Available tools:\n"
        f"{tool_lines}\n"
        "\n"
        "Your task is to propose one or more candidate laws relating the "
        "agent-declared inputs to the agent-declared outputs, together with "
        "the SI dimensional signature of every quantity in the law. Submit "
        "your answer in the format specified by the benchmark protocol."
    )


# ---- Per-domain prompt builders ----------------------------------------

def hooke_prompt(
    observables: Sequence[str] = HOOKE_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating a 1-D mechanical system. A single body of "
        "mass m moves along one axis under a state-dependent restoring "
        "influence directed toward an equilibrium point. You may interrogate "
        "the system by issuing tool calls; each call returns a measurement "
        "of the system's instantaneous state."
    )
    return _compose(narrative, observables, tool_names)


def damped_ho_prompt(
    observables: Sequence[str] = DAMPED_HO_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating a 1-D mechanical body of mass m. Its state "
        "evolves under a combined position-dependent restoring influence "
        "and a motion-opposing influence, both directed back toward an "
        "equilibrium configuration."
    )
    return _compose(narrative, observables, tool_names)


def gravity_prompt(
    observables: Sequence[str] = GRAVITY_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating a two-body radial configuration: a test "
        "body of mass m at separation r from a central source. The source "
        "exerts an attractive influence on the test body whose magnitude "
        "depends on their separation."
    )
    return _compose(narrative, observables, tool_names)


def coulomb_prompt(
    observables: Sequence[str] = COULOMB_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating two static-charge bodies separated by a "
        "distance r in an otherwise empty medium. The bodies exert a "
        "mutual influence whose magnitude depends on their separation "
        "and the magnitude of the charges they carry."
    )
    return _compose(narrative, observables, tool_names)


def pendulum_prompt(
    observables: Sequence[str] = PENDULUM_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating a rigid body pivoting about a fixed axis "
        "under a uniform vertical influence. The body's angular "
        "configuration evolves in time; you may probe the angle and "
        "angular rate at any chosen instant."
    )
    return _compose(narrative, observables, tool_names)


def rlc_prompt(
    observables: Sequence[str] = RLC_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating a single-loop electrical configuration with "
        "three passive elements arranged in series. Probing yields the "
        "instantaneous stored charge, loop current, and driving potential."
    )
    return _compose(narrative, observables, tool_names)


def thermal_prompt(
    observables: Sequence[str] = THERMAL_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating a planar slab of thickness L bounded by "
        "two reservoirs held at temperatures T_hot and T_cold. In steady "
        "state a thermal current q flows from the hotter to the cooler "
        "face; you may interrogate that current along with the boundary "
        "temperatures and the slab thickness."
    )
    return _compose(narrative, observables, tool_names)


def wave_prompt(
    observables: Sequence[str] = WAVE_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating a scalar disturbance that propagates "
        "through a 1-D medium. At a fixed probe location you may sample "
        "the instantaneous field amplitude and its time-derivative."
    )
    return _compose(narrative, observables, tool_names)


def optics_prompt(
    observables: Sequence[str] = OPTICS_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating the planar interface between two "
        "transparent media. A ray strikes the interface at an angle "
        "theta1 and emerges into the second medium at an angle theta2 "
        "measured from the same surface normal."
    )
    return _compose(narrative, observables, tool_names)


def fluid_prompt(
    observables: Sequence[str] = FLUID_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating a steady flow of a constant-density "
        "medium between two cross-sections of a duct. At each section "
        "you may sample the local elevation, speed, and pressure, and "
        "you wish to predict the downstream pressure given the upstream "
        "state."
    )
    return _compose(narrative, observables, tool_names)


def kinetics_prompt(
    observables: Sequence[str] = KINETICS_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating an isolated, well-mixed reactor. A single "
        "reactive species is present at concentration C; at any chosen "
        "instant you may sample C and the instantaneous time-rate at "
        "which it changes."
    )
    return _compose(narrative, observables, tool_names)


def decay_prompt(
    observables: Sequence[str] = DECAY_OBSERVABLES,
    tool_names: Sequence[str] = DEFAULT_TOOL_NAMES,
) -> str:
    narrative = (
        "You are investigating an isolated population of identical "
        "entities, each independently subject to a transition that "
        "removes it from the population. You may sample the population "
        "count N and its instantaneous time-rate."
    )
    return _compose(narrative, observables, tool_names)


__all__ = [
    "DEFAULT_TOOL_NAMES",
    "HOOKE_OBSERVABLES",
    "HOOKE_TOOL_NAMES",
    "DAMPED_HO_OBSERVABLES",
    "GRAVITY_OBSERVABLES",
    "COULOMB_OBSERVABLES",
    "PENDULUM_OBSERVABLES",
    "RLC_OBSERVABLES",
    "THERMAL_OBSERVABLES",
    "WAVE_OBSERVABLES",
    "OPTICS_OBSERVABLES",
    "FLUID_OBSERVABLES",
    "KINETICS_OBSERVABLES",
    "DECAY_OBSERVABLES",
    "hooke_prompt",
    "damped_ho_prompt",
    "gravity_prompt",
    "coulomb_prompt",
    "pendulum_prompt",
    "rlc_prompt",
    "thermal_prompt",
    "wave_prompt",
    "optics_prompt",
    "fluid_prompt",
    "kinetics_prompt",
    "decay_prompt",
]
