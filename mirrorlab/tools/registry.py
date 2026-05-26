"""Central tool registry. Spec §4.

Exposes the 32 MVS callables under their canonical dotted names
(``measure.position``, ``manipulate.set_initial``, etc.) along with a
small metadata shell — category, ``needs_sim``, ``mutates``. Downstream
agent harnesses iterate this registry to build the JSON-schema tool
manifest given to the LLM.

Wiring:

    from mirrorlab.tools.registry import REGISTRY, call
    call(ctx, "measure.position", body_id=0, t=1.0)

``ctx`` is a ``SandboxContext``; latency / call counts are recorded
through ``ctx.record_call``. ``measure`` / ``manipulate`` tools take
``ctx.sim``; ``analyze`` / ``knowledge`` tools ignore it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from mirrorlab.tools import analyze, knowledge, manipulate, measure
from mirrorlab.tools.sandbox import SandboxContext


@dataclass(frozen=True)
class ToolSpec:
    name: str
    category: str           # measure / manipulate / analyze / knowledge
    fn: Callable[..., Any]
    needs_sim: bool
    mutates: bool           # whether the tool may mutate sim state


def _spec(name: str, category: str, fn: Callable[..., Any],
          *, needs_sim: bool, mutates: bool) -> ToolSpec:
    return ToolSpec(name=name, category=category, fn=fn,
                    needs_sim=needs_sim, mutates=mutates)


_MEASURE = [
    ("position", measure.position),
    ("velocity", measure.velocity),
    ("field", measure.field),
    ("energy", measure.energy),
    ("spectrum", measure.spectrum),
    ("trajectory", measure.trajectory),
    ("scattering", measure.scattering),
    ("observable", measure.observable),
]

_MANIPULATE = [
    ("set_initial", manipulate.set_initial),
    ("apply_impulse", manipulate.apply_impulse),
    ("set_external_field", manipulate.set_external_field),
    ("set_boundary", manipulate.set_boundary),
    ("set_parameter", manipulate.set_parameter),
    ("reset", manipulate.reset),
    ("swap_bodies", manipulate.swap_bodies),
    ("time_reverse_probe", manipulate.time_reverse_probe),
]

_ANALYZE = [
    ("fit", analyze.fit),
    ("regress", analyze.regress),
    ("invariant_check", analyze.invariant_check),
    ("dimensional_analysis", analyze.dimensional_analysis),
    ("symbolic_simplify", analyze.symbolic_simplify),
    ("numerical_solve", analyze.numerical_solve),
    ("spectrum_fit", analyze.spectrum_fit),
    ("statistical_test", analyze.statistical_test),
]

_KNOWLEDGE = [
    ("lookup_constant", knowledge.lookup_constant),
    ("lookup_formula", knowledge.lookup_formula),
    ("unit_convert", knowledge.unit_convert),
    ("list_observables", knowledge.list_observables),
    ("suggest_probe", knowledge.suggest_probe),
    ("symmetry_glossary", knowledge.symmetry_glossary),
    ("dim_table", knowledge.dim_table),
    ("related_phenomena", knowledge.related_phenomena),
]


def _build_registry() -> Dict[str, ToolSpec]:
    reg: Dict[str, ToolSpec] = {}
    for short, fn in _MEASURE:
        reg[f"measure.{short}"] = _spec(f"measure.{short}", "measure", fn,
                                        needs_sim=True, mutates=False)
    for short, fn in _MANIPULATE:
        reg[f"manipulate.{short}"] = _spec(f"manipulate.{short}", "manipulate", fn,
                                           needs_sim=True, mutates=True)
    for short, fn in _ANALYZE:
        reg[f"analyze.{short}"] = _spec(f"analyze.{short}", "analyze", fn,
                                        needs_sim=False, mutates=False)
    for short, fn in _KNOWLEDGE:
        reg[f"knowledge.{short}"] = _spec(f"knowledge.{short}", "knowledge", fn,
                                          needs_sim=False, mutates=False)
    return reg


REGISTRY: Dict[str, ToolSpec] = _build_registry()
assert len(REGISTRY) == 32, f"MVS must be exactly 32 tools, got {len(REGISTRY)}"


def call(__ctx: SandboxContext, __name: str, /, **kwargs: Any) -> Any:
    """Invoke a registered tool through ``__ctx`` (records monitoring data).

    Positional-only ctx/name avoids kwarg collision with tools that take a
    ``name`` parameter (e.g. ``measure.observable``).
    """
    if __name not in REGISTRY:
        raise KeyError(f"unknown tool {__name!r}")
    spec = REGISTRY[__name]
    if spec.needs_sim:
        if __ctx.sim is None:
            raise RuntimeError(f"tool {__name!r} requires ctx.sim but none is bound")
        fn = spec.fn
        sim = __ctx.sim
        return __ctx.record_call(__name, (), kwargs, lambda **kw: fn(sim, **kw))
    return __ctx.record_call(__name, (), kwargs, spec.fn)


def categories() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for spec in REGISTRY.values():
        out[spec.category] = out.get(spec.category, 0) + 1
    return out


__all__ = ["REGISTRY", "ToolSpec", "call", "categories"]
