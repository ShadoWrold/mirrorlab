"""D5 v1 persistence semantics.

Within-scenario state on the agent scratchpad must survive across tool calls
*and* across consecutive operations on the same ``SandboxContext`` /
``SimInstance``. Cross-scenario state must NOT leak — each fresh load gives
a fresh sandbox with empty scratchpad and zero call counts.
"""

from __future__ import annotations

from mirrorlab.scenarios.loader import load
from mirrorlab.tools.registry import call
from mirrorlab.tools.sandbox import SandboxContext


def _new_ctx(shift: str = "baseline", seed: int = 0) -> SandboxContext:
    scen = load("hooke", shift, seed=seed)
    return SandboxContext(sim=scen.sim, scenario_id=f"hooke:{shift}:{seed}")


def test_scratchpad_survives_within_scenario():
    ctx = _new_ctx()
    ctx.scratchpad["fitted_k"] = 4.2
    call(ctx, "measure.position", body_id=0, t=0.1)
    assert ctx.scratchpad["fitted_k"] == 4.2
    call(ctx, "manipulate.set_parameter", param_name="k", value=10.0)
    assert ctx.scratchpad["fitted_k"] == 4.2


def test_call_log_accumulates_within_scenario():
    ctx = _new_ctx()
    for t in [0.0, 0.1, 0.2, 0.3]:
        call(ctx, "measure.position", body_id=0, t=t)
    assert ctx.call_counts["measure.position"] == 4
    assert len(ctx.call_log) == 4


def test_sim_mutations_persist_within_scenario():
    ctx = _new_ctx()
    call(ctx, "manipulate.set_parameter", param_name="k", value=77.0)
    assert ctx.sim._params.k == 77.0
    # subsequent measurement should reflect the mutated state
    r = call(ctx, "measure.field", probe_point=[0.0], field_type="force")
    # at x=x0, F = -k*x0
    expected = -77.0 * ctx.sim._params.x0
    assert abs(r["value"] - expected) < 1e-9


def test_no_leak_across_scenarios():
    ctx_a = _new_ctx(seed=1)
    ctx_a.scratchpad["secret"] = "alpha"
    call(ctx_a, "measure.position", body_id=0, t=0.0)
    call(ctx_a, "manipulate.set_parameter", param_name="k", value=12345.0)

    ctx_b = _new_ctx(seed=2)
    assert ctx_b.scratchpad == {}
    assert ctx_b.call_log == []
    assert ctx_b.call_counts == {}
    assert ctx_b.sim is not ctx_a.sim
    assert ctx_b.sim._params.k != 12345.0


def test_fresh_load_does_not_share_sim_instance():
    s1 = load("hooke", "baseline", seed=7).sim
    s2 = load("hooke", "baseline", seed=7).sim
    assert s1 is not s2
    s1._params  # noqa: F841 — accessed to ensure independent instance
    # mutating one must not touch the other
    import dataclasses
    s1._params = dataclasses.replace(s1._params, k=999.0)
    assert s2._params.k != 999.0


def test_import_log_isolated_per_context():
    ctx_a = _new_ctx(seed=10)
    ctx_b = _new_ctx(seed=11)
    ctx_a.record_import("sklearn")
    ctx_a.record_import("pysr")
    assert len(ctx_a.import_log) == 2
    assert ctx_b.import_log == []
