"""Offline rescore: s0 gpt + claude full sweep under unified scoring
(rad fix + Phase 2 structural bonus + cf clamp). Builds the gpt-vs-claude table.

Run with: python3 -S docs/_rescore_gpt_vs_claude.py
The -S flag skips automatic .pth processing — a sibling editable install
(_editable_impl_long_horizon_bench.pth) points at a dead /ssd-disk mount whose
I/O error crashes normal startup. We re-add site-packages by hand below.
"""
import sys
sys.path.insert(0, "/home/lih/.local/lib/python3.12/site-packages")
sys.path.insert(0, "/usr/lib/python3/dist-packages")
sys.path.insert(0, ".")

import json
import statistics as st

import mirrorlab.scenarios.loader  # noqa: F401
from mirrorlab.scenarios.loader import load
from mirrorlab.spec import get_cell, has_cell
from mirrorlab.runners.sprint3_pilot import score_against_scenario_detail


def rescore(entries):
    out = {}
    for x in entries:
        key = (x["domain_id"], x["shift_id"])
        rec = {"stored": x.get("s_scen"), "term": x["terminated_by"],
               "sat": x.get("saturated")}
        if x.get("submission") and has_cell(*key):
            spec = get_cell(*key)
            sc = load(*key, seed=0)
            try:
                det = score_against_scenario_detail(
                    sc, x["submission"], gt_symmetry=spec.break_type,
                    structural=True)
                rec["rescored"] = round(det.best_of_k, 4)
                rec["single"] = round(det.single_submission, 4)
            except Exception as e:
                # A malformed predictor (e.g. IndentationError in the submitted
                # code) scores 0 — same as the live grader would have done.
                rec["rescored"] = 0.0
                rec["single"] = 0.0
                rec["score_error"] = type(e).__name__
            rec["break_type"] = spec.break_type
        else:
            rec["rescored"] = 0.0
            rec["single"] = 0.0
        out[key] = rec
    return out


s0 = json.load(open("docs/measurement-sweep-s0.json"))
gpt = [x for x in s0["entries"] if x["model"].startswith("gpt")]
cl = json.load(open("docs/claude-full-sweep.json"))["entries"]

g = rescore(gpt)
c = rescore(cl)

gv = [v["rescored"] for v in g.values()]
cv = [v["rescored"] for v in c.values()]
gs = [v.get("stored", 0) or 0 for v in g.values()]
cs = [v.get("stored", 0) or 0 for v in c.values()]

print("=== gpt vs claude unified scoring (rad fix + Phase2 + clamp) ===")
print(f"gpt:    stored={st.mean(gs):.3f} -> rescored={st.mean(gv):.3f}  "
      f"(nonzero {sum(1 for x in gv if x > 0.01)}/48)")
print(f"claude: stored={st.mean(cs):.3f} -> rescored={st.mean(cv):.3f}  "
      f"(nonzero {sum(1 for x in cv if x > 0.01)}/48)")

rows = []
for key in sorted(set(g) | set(c)):
    gg = g.get(key, {})
    cc = c.get(key, {})
    rows.append({"domain": key[0], "shift": key[1],
                 "gpt": gg.get("rescored"), "claude": cc.get("rescored"),
                 "gpt_term": gg.get("term"), "claude_term": cc.get("term")})
json.dump({"meta": {"scoring": "radfix+phase2+clamp",
                    "source": "s0-gpt + claude-full"}, "rows": rows},
          open("docs/gpt-vs-claude-rescored.json", "w"), indent=1)
print("wrote docs/gpt-vs-claude-rescored.json")
