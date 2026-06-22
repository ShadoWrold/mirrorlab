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

# Neutral, by-category description of the toolbox. The full set of tools (with
# their exact names, parameters, and per-tool descriptions) is delivered to the
# agent through the function-calling schema built from ``mirrorlab.tools.
# registry`` — NOT enumerated here. We deliberately avoid a hand-picked
# shortlist of tool names: an earlier shortlist foregrounded the curve-fitting
# tools (the path the benchmark exists to penalize) while omitting the
# invariant / symmetry probes that operationalize the intended solution, which
# biased agents toward the failure mode. A category-level summary is steering-
# neutral and stays in sync with the registry automatically.
TOOLBOX_DESCRIPTION: str = (
    "You have a toolbox, delivered via the function-calling interface, in "
    "four categories:\n"
    "  - measure: read the live system's instantaneous state and trajectories.\n"
    "  - manipulate: set initial conditions, perturb the system, reset it, or "
    "probe it under transformations (e.g. time reversal, body exchange).\n"
    "  - analyze: operate on data you collect — fit models, regress, check "
    "invariants/conservation, dimensional analysis, spectra, symbolic work.\n"
    "  - knowledge: reference constants, dimensional signatures, symmetry "
    "glossary, and related phenomena.\n"
    "Inspect the full tool list and each tool's signature in your function-"
    "calling interface; choose whichever tools fit your investigation."
)


# ---- Observables per domain --------------------------------------------

HOOKE_OBSERVABLES: tuple[str, ...] = ("t", "x", "v", "F")
DAMPED_HO_OBSERVABLES: tuple[str, ...] = ("t", "x", "v", "F")
GRAVITY_OBSERVABLES: tuple[str, ...] = ("t", "r", "v", "F")
COULOMB_OBSERVABLES: tuple[str, ...] = ("t", "r", "v", "F")
PENDULUM_OBSERVABLES: tuple[str, ...] = ("theta", "omega", "theta_ddot")
RLC_OBSERVABLES: tuple[str, ...] = ("q", "i", "didt")
THERMAL_OBSERVABLES: tuple[str, ...] = ("T_hot", "T_cold", "L", "q")
WAVE_OBSERVABLES: tuple[str, ...] = ("t", "u")
OPTICS_OBSERVABLES: tuple[str, ...] = ("theta1", "theta2", "nu", "T")
FLUID_OBSERVABLES: tuple[str, ...] = ("p1", "v1", "v2", "h1", "h2", "p2")
KINETICS_OBSERVABLES: tuple[str, ...] = ("t", "C", "rate")
DECAY_OBSERVABLES: tuple[str, ...] = ("t", "N", "rate")


# ---- Generic prompt assembler ------------------------------------------

def _compose(
    narrative: str,
    observables: Sequence[str],
    output_name: str,
) -> str:
    obs_line = ", ".join(observables)
    return (
        f"{narrative}\n"
        "\n"
        f"Observable variables: {obs_line}.\n"
        "\n"
        f"{TOOLBOX_DESCRIPTION}\n"
        "\n"
        "Your task is to propose one or more candidate laws relating the "
        "agent-declared inputs to the agent-declared outputs, together with "
        "the SI dimensional signature of every quantity in the law. The "
        f"benchmark scores each candidate law by predicting {output_name}: "
        f"every law you submit must compute {output_name} from its declared "
        f"inputs, and its declared output dimension must be that of "
        f"{output_name}. If you discover that an intermediate quantity (for "
        "example a rate, a frequency, or a coefficient) depends on a setting "
        f"you can vary, fold that dependence back into your predictor for "
        f"{output_name} rather than submitting the intermediate relation on "
        "its own. Submit your answer in the format specified by the "
        "benchmark protocol."
    )


# ---- Per-domain prompt builders ----------------------------------------

def hooke_prompt(
    observables: Sequence[str] = HOOKE_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating a 1-D mechanical system. A single body of "
        "mass m moves along one axis under a state-dependent restoring "
        "influence directed toward an equilibrium point. You may interrogate "
        "the system by issuing tool calls; each call returns a measurement "
        "of the system's instantaneous state."
    )
    return _compose(narrative, observables, "F")


def damped_ho_prompt(
    observables: Sequence[str] = DAMPED_HO_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating a 1-D mechanical body of mass m. Its state "
        "evolves under a combined position-dependent restoring influence "
        "and a motion-opposing influence, both directed back toward an "
        "equilibrium configuration."
    )
    return _compose(narrative, observables, "F")


def gravity_prompt(
    observables: Sequence[str] = GRAVITY_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating a two-body radial configuration: a test "
        "body of mass m at separation r from a central source. The source "
        "exerts an attractive influence on the test body whose magnitude "
        "depends on their separation."
    )
    return _compose(narrative, observables, "F")


def coulomb_prompt(
    observables: Sequence[str] = COULOMB_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating two static-charge bodies separated by a "
        "distance r in an otherwise empty medium. The bodies exert a "
        "mutual influence whose magnitude depends on their separation "
        "and the magnitude of the charges they carry."
    )
    return _compose(narrative, observables, "F")


def pendulum_prompt(
    observables: Sequence[str] = PENDULUM_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating a rigid body pivoting about a fixed axis "
        "under a uniform vertical influence. At any chosen instant you may "
        "set the body to an angle theta and read its angular acceleration; "
        "your goal is the instantaneous law giving the angular acceleration "
        "as a function of the angle."
    )
    return _compose(narrative, observables, "theta_ddot")


def rlc_prompt(
    observables: Sequence[str] = RLC_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating a single-loop electrical configuration with "
        "three passive elements arranged in series. At any chosen instant you "
        "may set the stored charge q and loop current i and read the rate of "
        "change of the current; your goal is the instantaneous law giving "
        "that current rate as a function of (q, i)."
    )
    return _compose(narrative, observables, "didt")


def thermal_prompt(
    observables: Sequence[str] = THERMAL_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating a planar slab of thickness L bounded by "
        "two reservoirs held at temperatures T_hot and T_cold. In steady "
        "state a thermal current q flows from the hotter to the cooler "
        "face; you may interrogate that current along with the boundary "
        "temperatures and the slab thickness."
    )
    return _compose(narrative, observables, "q")


def wave_prompt(
    observables: Sequence[str] = WAVE_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating a scalar disturbance that propagates "
        "through a 1-D medium. At a fixed probe location you may sample "
        "the instantaneous field amplitude."
    )
    return _compose(narrative, observables, "u")


def optics_prompt(
    observables: Sequence[str] = OPTICS_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating the planar interface between two "
        "transparent media. A ray strikes the interface at an angle "
        "theta1 and emerges into the second medium at an angle theta2 "
        "measured from the same surface normal."
    )
    return _compose(narrative, observables, "theta2")


def fluid_prompt(
    observables: Sequence[str] = FLUID_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating a steady flow of a constant-density medium "
        "between two cross-sections of a duct, an upstream station 1 and a "
        "downstream station 2. You may sample the elevation h, speed v, and "
        "pressure p at each station (h1/v1/p1 upstream, h2/v2 downstream) and "
        "you wish to predict the downstream pressure p2 from that state."
    )
    return _compose(narrative, observables, "p2")


def kinetics_prompt(
    observables: Sequence[str] = KINETICS_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating an isolated, well-mixed reactor. A single "
        "reactive species is present at concentration C; at any chosen "
        "instant you may sample C and the instantaneous time-rate at "
        "which it changes."
    )
    return _compose(narrative, observables, "C")


def decay_prompt(
    observables: Sequence[str] = DECAY_OBSERVABLES,
) -> str:
    narrative = (
        "You are investigating an isolated population of identical "
        "entities, each independently subject to a transition that "
        "removes it from the population. You may sample the population "
        "count N and its instantaneous time-rate."
    )
    return _compose(narrative, observables, "N")


__all__ = [
    "TOOLBOX_DESCRIPTION",
    "HOOKE_OBSERVABLES",
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
