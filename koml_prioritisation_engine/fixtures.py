"""Labelled synthetic fixtures. No randomness; seed is not applicable."""
import json
from pathlib import Path

def generate(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    # Four hand-calculated cases repeated 50 times: scores 0, 10, 100, 400.
    cases = [(0, 0, 0, 1, "0.000000"), (10, 0, 0, 1, "10.000000"),
             (50, 1, 0, 1, "100.000000"), (100, 1, 1, 1, "400.000000")]
    tasks, scores, high = [], {}, []
    for i in range(200):
        value, urgency, reversible, effort, expected = cases[i % 4]
        ident = f"task-{i:03d}"
        tasks.append(dict(id=ident, title=f"Synthetic task {i}", expected_value=str(value),
                          urgency=str(urgency), reversibility=str(reversible), effort=str(effort), synthetic=True))
        scores[ident] = expected
        if i % 4 in (2, 3):
            high.append(ident)
    data = {"_comment": "SYNTHETIC fixture: four planted cases repeated 50 times", "synthetic": True, "tasks": tasks}
    expectations = {"_comment": "SYNTHETIC hand-computed oracle, never consumed by run",
        "synthetic": True, "count": 200, "synthetic_count": 200, "real_count": 0,
        "total_expected_value": "8000", "high_priority_ids": high, "scores": scores,
        "calculation": "50 * (0 + 10 + 50 + 100) = 8000; 100 scores >= 100"}
    for name, content in (("tasks.json", data), ("expectations.json", expectations)):
        (out / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "README.md").write_text("<!-- SYNTHETIC fixture -->\nAll 200 tasks are synthetic. No measured savings.\n", encoding="utf-8")
